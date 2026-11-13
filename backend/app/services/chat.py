"""Conversation admission, generation, HITL approval resumption, and durable usage settlement."""
import asyncio
import logging
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

import anyio
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from starlette.concurrency import run_in_threadpool

from app.ai.graph.agent import agent
from app.ai.llm import CRAFT_MODES, resolve_model
from app.ai.tools import get_tool_tier, truncate_tool_output
from app.core.config import get_settings
from app.db.crud_chat import ChatCRUD
from app.db.crud_token import AssistantReply, TokenUsageCRUD
from app.db.session import SessionLocal
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedChat:
    conversation_id: int
    reservation_id: str
    user_id: int
    user_message: str
    messages: list
    user_instructions: str
    relevant_memories: list[str]
    model: str
    mode: str
    tier: str
    cancel: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass(frozen=True)
class PreparedApproval:
    conversation_id: int
    reservation_id: str
    user_id: int
    action_id: str
    tool_name: str
    decision: str
    resume_payload: dict
    model: str
    tier: str
    cancel: asyncio.Event = field(default_factory=asyncio.Event)


def prompt_bound(messages, mode, user_instructions="", relevant_memories=None):
    # Byte-level upper bound with generous per-message framing overhead. Reserve
    # all history + system instructions + personalization + maximum output.
    extra = len((user_instructions or "").encode("utf-8")) + sum(
        len(str(m).encode("utf-8")) for m in (relevant_memories or [])
    )
    return (
        len(CRAFT_MODES[mode].encode("utf-8"))
        + extra
        + 64
        + sum(len(str(m.content).encode("utf-8")) + 64 for m in messages)
        + get_settings().max_output_tokens
    )


def _extract_interrupt(config: dict) -> Optional[dict]:
    state = agent.get_state(config)
    for task in getattr(state, "tasks", []):
        for intr in getattr(task, "interrupts", []):
            if getattr(intr, "value", None):
                return intr.value
    return None


def _persist_approval(
    conversation_id: int,
    user_id: int,
    interrupt_item: dict,
) -> dict:
    action_id = interrupt_item.get("actionId") or f"act_{uuid4().hex[:8]}"
    tool_name = interrupt_item.get("tool") or "edit_workspace_file"
    tier = interrupt_item.get("tier", 2)
    parameters = interrupt_item.get("parameters", {})
    rationale = interrupt_item.get("rationale", "")
    diff = interrupt_item.get("diff", "")

    with SessionLocal() as db:
        ChatCRUD.create_or_update_approval(
            db=db,
            action_id=action_id,
            conversation_id=conversation_id,
            user_id=user_id,
            tool_name=tool_name,
            tier=tier,
            parameters=parameters,
            rationale=rationale,
            diff=diff,
        )

    return {
        "actionId": action_id,
        "tool": tool_name,
        "toolName": tool_name,
        "tier": tier,
        "parameters": parameters,
        "rationale": rationale,
        "diff": diff,
    }


def _persist_memories(user_id: int, message: str, conversation_id: int) -> None:
    if not message:
        return
    with SessionLocal() as db:
        MemoryService.persist_extracted_memories(
            db=db,
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
        )


class ChatService:
    @staticmethod
    def prepare(
        message,
        conversation_id,
        user_id,
        user_tier,
        db,
        model_id=None,
        mode="standard",
        request_id=None,
    ):
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

        prefs = MemoryService.get_preferences(db, user_id)
        user_instructions = MemoryService.format_user_instructions(prefs)
        relevant_memories = (
            MemoryService.get_relevant_memories(db, user_id, message, limit=5)
            if prefs.memory_enabled
            else []
        )

        messages = [
            HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
            for m in history
        ]
        messages.append(HumanMessage(content=message))
        reservation = TokenUsageCRUD.reserve(
            db,
            user_id,
            user_tier,
            prompt_bound(messages, mode, user_instructions, relevant_memories),
            request_id or str(uuid4()),
        )
        try:
            if conversation_id is None:
                conversation = ChatCRUD.create_conversation(
                    db,
                    user_id,
                    message[:30] + ("..." if len(message) > 30 else ""),
                )
                conversation_id = conversation.id
            ChatCRUD.add_message(db, conversation_id, "user", message)
            db.commit()
        except Exception:
            db.rollback()
            TokenUsageCRUD.finish(db, reservation, outcome="failed", tokens_used=0)
            raise
        return PreparedChat(
            conversation_id=conversation_id,
            reservation_id=reservation,
            user_id=user_id,
            user_message=message,
            messages=messages,
            user_instructions=user_instructions,
            relevant_memories=relevant_memories,
            model=model,
            mode=mode,
            tier=user_tier,
        )

    @staticmethod
    def prepare_approval(
        db,
        user_id: int,
        user_tier: str,
        action_id: str,
        decision: str,
        modified_params: Optional[dict] = None,
        feedback: Optional[str] = None,
    ) -> PreparedApproval:
        approval = ChatCRUD.get_approval_by_id(db, action_id, user_id=user_id)
        if not approval:
            raise HTTPException(404, "Approval request not found or unauthorized.")
        if approval.status != "pending":
            raise HTTPException(409, f"Approval request is already {approval.status}.")

        model = resolve_model(user_tier, None)
        reservation = TokenUsageCRUD.reserve(
            db,
            user_id,
            user_tier,
            get_settings().max_output_tokens + 256,
            str(uuid4()),
        )
        try:
            ChatCRUD.resolve_approval(db, action_id, decision=decision, feedback=feedback)
            db.commit()
        except Exception:
            db.rollback()
            TokenUsageCRUD.finish(db, reservation, outcome="failed", tokens_used=0)
            raise

        resume_payload = {
            "decision": decision,
            "modifiedParams": modified_params or {},
            "feedback": feedback or "",
        }
        return PreparedApproval(
            conversation_id=approval.conversation_id,
            reservation_id=reservation,
            user_id=user_id,
            action_id=action_id,
            tool_name=approval.tool_name,
            decision=decision,
            resume_payload=resume_payload,
            model=model,
            tier=user_tier,
        )

    @staticmethod
    def _settle(prepared, outcome, tokens_used=None, text=None):
        with SessionLocal() as db:
            return TokenUsageCRUD.finish(
                db,
                prepared.reservation_id,
                outcome=outcome,
                tokens_used=tokens_used,
                assistant=AssistantReply(
                    prepared.conversation_id,
                    text,
                    prepared.model,
                    getattr(prepared, "mode", "agent"),
                )
                if outcome == "succeeded" and text is not None
                else None,
            )

    @staticmethod
    async def _run_graph_stream(
        *,
        prepared,
        graph_input,
        config: dict,
        is_agent_mode: bool,
        approval_fallback: Optional[dict] = None,
    ):
        text = ""
        total_usage = None
        settled = False
        emitted_tool_call_ids: set[str] = set()
        step_count = 0
        last_tool_output = ""
        approval_result_emitted = False
        mode = getattr(prepared, "mode", "agent")

        try:
            if is_agent_mode and approval_fallback is None:
                yield {
                    "_sse_event": "thought",
                    "thought": f"Analyzing goal in Agent Studio mode ({prepared.model})...",
                }
            elif not is_agent_mode:
                yield {
                    "type": "start",
                    "conversation_id": prepared.conversation_id,
                    "request_id": prepared.reservation_id,
                    "model_used": prepared.model,
                    "mode_used": mode,
                }

            async with asyncio.timeout(get_settings().generation_timeout_seconds):
                async with aclosing(
                    agent.astream(graph_input, config=config, stream_mode="messages")
                ) as chunks:
                    async for item in chunks:
                        msg_obj = item[0] if isinstance(item, tuple) else item

                        usage = getattr(msg_obj, "usage_metadata", None) or {}
                        metadata = getattr(msg_obj, "response_metadata", None) or {}
                        reported = usage.get("total_tokens") or metadata.get("token_usage", {}).get("total_tokens")
                        if reported:
                            total_usage = int(reported)

                        tool_calls = getattr(msg_obj, "tool_calls", None)
                        if is_agent_mode and tool_calls:
                            if getattr(msg_obj, "content", None) and isinstance(msg_obj, AIMessage):
                                yield {"_sse_event": "thought", "thought": str(msg_obj.content)}
                            for tc in tool_calls:
                                tc_id = tc.get("id") or f"act_{step_count + 1}"
                                tc_name = tc.get("name") or ""
                                if tc_name and tc_id not in emitted_tool_call_ids:
                                    emitted_tool_call_ids.add(tc_id)
                                    step_count += 1
                                    yield {
                                        "_sse_event": "action_call",
                                        "actionId": tc_id,
                                        "tool": tc_name,
                                        "args": tc.get("args", {}),
                                        "tier": get_tool_tier(tc_name),
                                    }
                            continue

                        if isinstance(msg_obj, ToolMessage):
                            if is_agent_mode:
                                out_str = truncate_tool_output(str(msg_obj.content))
                                last_tool_output = out_str
                                tc_id = getattr(msg_obj, "tool_call_id", "") or f"act_{step_count}"
                                tc_name = getattr(msg_obj, "name", "") or "workspace_tool"
                                if (
                                    approval_fallback
                                    and not approval_result_emitted
                                    and tc_id not in emitted_tool_call_ids
                                ):
                                    tc_id = approval_fallback["actionId"]
                                    tc_name = approval_fallback["toolName"]
                                    approval_result_emitted = True
                                yield {
                                    "_sse_event": "action_result",
                                    "actionId": tc_id,
                                    "tool": tc_name,
                                    "output": out_str,
                                }
                            continue

                        content = getattr(msg_obj, "content", "")
                        if isinstance(content, str) and content:
                            text += content
                            if is_agent_mode:
                                yield {"_sse_event": "token", "token": content}
                            else:
                                yield {"type": "chunk", "content": content}

            if is_agent_mode:
                interrupt_item = await run_in_threadpool(_extract_interrupt, config)
                if interrupt_item:
                    approval_payload = await run_in_threadpool(
                        _persist_approval,
                        prepared.conversation_id,
                        prepared.user_id,
                        interrupt_item,
                    )
                    result = await run_in_threadpool(
                        ChatService._settle,
                        prepared,
                        "succeeded",
                        total_usage if total_usage is not None else len(getattr(prepared, "user_message", "").split()) or 10,
                        None,
                    )
                    settled = True
                    charged, remaining = result or (0, 0)
                    yield {"_sse_event": "approval_required", **approval_payload}
                    yield {
                        "_sse_event": "done",
                        "status": "interrupted",
                        "actionId": approval_payload["actionId"],
                        "totalSteps": max(1, step_count),
                        "conversationId": prepared.conversation_id,
                        "tokensUsed": charged,
                        "tokensRemaining": remaining,
                        "modelUsed": prepared.model,
                        "modeUsed": mode,
                    }
                    return

                if not text.strip() and approval_fallback:
                    text = f"Action '{approval_fallback['toolName']}' {approval_fallback['decision']}ed: {last_tool_output}"
                    yield {"_sse_event": "token", "token": text}

            if not text:
                raise RuntimeError("Provider returned no assistant text")

            result = await run_in_threadpool(
                ChatService._settle, prepared, "succeeded", total_usage, text
            )
            if result is None:
                raise RuntimeError("Reservation already settled or expired")
            settled = True
            charged, remaining = result

            user_message = getattr(prepared, "user_message", "")
            if user_message:
                await run_in_threadpool(
                    _persist_memories, prepared.user_id, user_message, prepared.conversation_id
                )

            if is_agent_mode:
                yield {
                    "_sse_event": "done",
                    "status": "completed",
                    "totalSteps": max(1, step_count + 1),
                    "conversationId": prepared.conversation_id,
                    "tokensUsed": charged,
                    "tokensRemaining": remaining,
                    "modelUsed": prepared.model,
                    "modeUsed": mode,
                    "usage_estimated": total_usage is None,
                }
            else:
                yield {
                    "type": "done",
                    "conversation_id": prepared.conversation_id,
                    "tokens_used": charged,
                    "tokens_remaining": remaining,
                    "model_used": prepared.model,
                    "mode_used": mode,
                    "usage_estimated": total_usage is None,
                }
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except Exception as exc:
            # Never expose provider exceptions, request headers, keys, or stack traces.
            logger.warning("Generation failed (%s)", type(exc).__name__)
            configured_error = isinstance(exc, HTTPException) and exc.status_code == 503
            error_msg = (
                "AI provider is not configured. Please try again later."
                if configured_error
                else "AI generation failed. Please try again."
            )
            error_status = 503 if configured_error else 502
            if is_agent_mode:
                yield {
                    "_sse_event": "error",
                    "status": error_status,
                    "error": error_msg,
                    "conversationId": prepared.conversation_id,
                }
            else:
                yield {
                    "type": "error",
                    "status": error_status,
                    "error": error_msg,
                    "conversation_id": prepared.conversation_id,
                }
        finally:
            prepared.cancel.set()
            if not settled:
                # ASGI disconnects cancel the surrounding task group. Shield only
                # bounded durable settlement; never shield the upstream generation.
                with anyio.CancelScope(shield=True):
                    await run_in_threadpool(
                        ChatService._settle,
                        prepared,
                        "cancelled" if text else "failed",
                        total_usage if total_usage is not None else (None if text else 0),
                    )

    @staticmethod
    async def events(prepared: PreparedChat):
        config = {
            "configurable": {
                "user_id": prepared.user_id,
                "user_tier": prepared.tier,
                "model_id": prepared.model,
                "mode": prepared.mode,
                "thread_id": str(prepared.conversation_id),
                "cancel_event": prepared.cancel,
            }
        }
        input_state = {
            "messages": prepared.messages,
            "user_instructions": prepared.user_instructions,
            "relevant_memories": prepared.relevant_memories,
        }
        async with aclosing(
            ChatService._run_graph_stream(
                prepared=prepared,
                graph_input=input_state,
                config=config,
                is_agent_mode=(prepared.mode == "agent"),
            )
        ) as stream:
            async for event in stream:
                yield event

    @staticmethod
    async def approval_events(prepared: PreparedApproval):
        config = {
            "configurable": {
                "thread_id": str(prepared.conversation_id),
                "user_id": prepared.user_id,
                "user_tier": prepared.tier,
                "model_id": prepared.model,
                "mode": "agent",
                "cancel_event": prepared.cancel,
            }
        }
        async with aclosing(
            ChatService._run_graph_stream(
                prepared=prepared,
                graph_input=Command(resume=prepared.resume_payload),
                config=config,
                is_agent_mode=True,
                approval_fallback={
                    "actionId": prepared.action_id,
                    "toolName": prepared.tool_name,
                    "decision": prepared.decision,
                },
            )
        ) as stream:
            async for event in stream:
                yield event