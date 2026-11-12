"""Conversation admission, generation, and durable usage settlement."""
import asyncio
import logging
from contextlib import aclosing
from dataclasses import dataclass, field
from uuid import uuid4

import anyio
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from starlette.concurrency import run_in_threadpool

from app.ai.graph.agent import agent
from app.ai.llm import CRAFT_MODES, resolve_model
from app.core.config import get_settings
from app.db.crud_chat import ChatCRUD
from app.db.crud_token import TokenUsageCRUD, AssistantReply
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedChat:
    conversation_id: int
    reservation_id: str
    messages: list
    model: str
    mode: str
    tier: str
    cancel: asyncio.Event = field(default_factory=asyncio.Event)


def prompt_bound(messages, mode):
    # Byte-level upper bound with generous per-message framing overhead. Reserve
    # all history + system instructions + maximum output, not just the new text.
    return (len(CRAFT_MODES[mode].encode("utf-8")) + 64
            + sum(len(str(m.content).encode("utf-8")) + 64 for m in messages)
            + get_settings().max_output_tokens)


class ChatService:
    @staticmethod
    def prepare(message, conversation_id, user_id, user_tier, db, model_id=None,
                mode="standard", request_id=None):
        model = resolve_model(user_tier, model_id)
        mode = (mode or "standard").lower()
        if mode not in CRAFT_MODES:
            raise HTTPException(422, "Unknown Craft Mode")
        history = []
        if conversation_id is not None:
            conversation = ChatCRUD.get_conversation(db, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise HTTPException(404, "Conversation not found")
            history = ChatCRUD.get_messages_for_conversation(db, conversation_id)
        messages = [HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
                    for m in history]
        messages.append(HumanMessage(content=message))
        reservation = TokenUsageCRUD.reserve(db, user_id, user_tier,
                                             prompt_bound(messages, mode), request_id or str(uuid4()))
        try:
            if conversation_id is None:
                conversation = ChatCRUD.create_conversation(db, user_id,
                                  message[:30] + ("..." if len(message) > 30 else ""))
                conversation_id = conversation.id
            ChatCRUD.add_message(db, conversation_id, "user", message)
            db.commit()
        except Exception:
            db.rollback()
            TokenUsageCRUD.finish(db, reservation, outcome="failed", tokens_used=0)
            raise
        return PreparedChat(conversation_id, reservation, messages, model, mode, user_tier)

    @staticmethod
    def _settle(prepared, outcome, tokens_used=None, text=None):
        with SessionLocal() as db:
            return TokenUsageCRUD.finish(
                db, prepared.reservation_id, outcome=outcome, tokens_used=tokens_used,
                assistant=AssistantReply(prepared.conversation_id, text, prepared.model, prepared.mode)
                if outcome == "succeeded" else None,
            )

    @staticmethod
    async def events(prepared):
        text = ""
        total_usage = None
        settled = False
        config = {"configurable": {"user_tier": prepared.tier,
                                   "model_id": prepared.model, "mode": prepared.mode,
                                   "cancel_event": prepared.cancel}}
        try:
            yield {"type": "start", "conversation_id": prepared.conversation_id,
                   "request_id": prepared.reservation_id, "model_used": prepared.model,
                   "mode_used": prepared.mode}
            async with asyncio.timeout(get_settings().generation_timeout_seconds):
                async with aclosing(agent.astream({"messages": prepared.messages}, config=config,
                                                   stream_mode="messages")) as chunks:
                    async for chunk, _metadata in chunks:
                        if isinstance(chunk.content, str) and chunk.content:
                            text += chunk.content
                            yield {"type": "chunk", "content": chunk.content}
                        usage = getattr(chunk, "usage_metadata", None) or {}
                        metadata = getattr(chunk, "response_metadata", None) or {}
                        reported = usage.get("total_tokens") or metadata.get("token_usage", {}).get("total_tokens")
                        if reported:
                            total_usage = int(reported)
            if not text:
                raise RuntimeError("Provider returned no assistant text")
            result = await run_in_threadpool(ChatService._settle, prepared, "succeeded", total_usage, text)
            if result is None:
                raise RuntimeError("Reservation already settled or expired")
            settled = True
            charged, remaining = result
            yield {"type": "done", "conversation_id": prepared.conversation_id,
                   "tokens_used": charged, "tokens_remaining": remaining,
                   "model_used": prepared.model, "mode_used": prepared.mode,
                   "usage_estimated": total_usage is None}
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except Exception as exc:
            # Never expose provider exceptions, request headers, keys, or stack traces.
            logger.warning("Generation failed (%s)", type(exc).__name__)
            configured_error = isinstance(exc, HTTPException) and exc.status_code == 503
            yield {"type": "error", "status": 503 if configured_error else 502,
                   "error": "AI provider is not configured. Please try again later." if configured_error
                   else "AI generation failed. Please try again.",
                   "conversation_id": prepared.conversation_id}
        finally:
            prepared.cancel.set()
            if not settled:
                # ASGI disconnects cancel the surrounding task group. Shield only
                # bounded durable settlement; never shield the upstream generation.
                with anyio.CancelScope(shield=True):
                    await run_in_threadpool(ChatService._settle, prepared,
                                            "cancelled" if text else "failed",
                                            total_usage if total_usage is not None else (None if text else 0))
