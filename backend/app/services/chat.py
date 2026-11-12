import json
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from typing import Optional, Generator
from langgraph.types import Command
from app.db.crud_token import TokenUsageCRUD
from app.db.crud_chat import ChatCRUD
from app.schemas.chat import ChatResponse
from app.ai.graph.agent import agent
from app.ai.llm import ALLOWED_MODELS, PLAN_QUOTAS, is_tier_allowed
from app.ai.tools import TOOL_CAPABILITY_TIERS, truncate_tool_output, get_tool_tier
from app.services.memory import MemoryService


class ChatService:
    @staticmethod
    def _validate_policy_and_prepare(
        message: str,
        conversation_id: Optional[int],
        user_id: int,
        user_tier: str,
        db: Session,
        model_id: Optional[str] = None,
    ):
        tier_lower = (user_tier or "free").lower()
        default_tokens = PLAN_QUOTAS.get(tier_lower, PLAN_QUOTAS["free"])["tokens"]

        user_limit = TokenUsageCRUD.get_user_limit(db, user_id)
        if not user_limit:
            user_limit = TokenUsageCRUD.create_user_limit(db, user_id, initial_limit=default_tokens)

        if user_limit.daily_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Daily token limit exceeded",
            )

        # Enforce model tier lock if a known model_id is requested
        if model_id and model_id in ALLOWED_MODELS:
            required_plan = ALLOWED_MODELS[model_id]["requiredPlan"]
            if not is_tier_allowed(tier_lower, required_plan):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Model '{model_id}' requires the '{required_plan}' plan.",
                )

        if not conversation_id:
            title = message[:30] + "..." if len(message) > 30 else message
            conversation = ChatCRUD.create_conversation(db, user_id, title)
            conversation_id = conversation.id
        else:
            conversation = ChatCRUD.get_conversation(db, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise HTTPException(status_code=404, detail="Conversation not found")

        ChatCRUD.add_message(db, conversation_id, "user", message)

        # Retrieve active user preferences and relevant memories for AgentState
        prefs = MemoryService.get_preferences(db, user_id)
        user_instructions = MemoryService.format_user_instructions(prefs)
        relevant_memories = (
            MemoryService.get_relevant_memories(db, user_id, message, limit=5)
            if prefs.memory_enabled
            else []
        )

        history = ChatCRUD.get_messages_for_conversation(db, conversation_id)
        formatted_history = []
        for msg in history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            else:
                formatted_history.append(AIMessage(content=msg.content))

        return conversation_id, formatted_history, user_instructions, relevant_memories

    @staticmethod
    def _build_agent_invocation(
        formatted_history: list,
        user_instructions: str,
        relevant_memories: list[str],
        user_id: int,
        user_tier: str,
        model_id: Optional[str],
        effective_mode: str,
        conversation_id: Optional[int] = None,
    ) -> tuple[dict, dict]:
        input_state = {
            "messages": formatted_history,
            "user_instructions": user_instructions,
            "relevant_memories": relevant_memories,
        }
        config = {
            "configurable": {
                "user_id": user_id,
                "user_tier": user_tier,
                "model_id": model_id,
                "mode": effective_mode,
            }
        }
        if conversation_id is not None:
            config["configurable"]["thread_id"] = str(conversation_id)
        return input_state, config

    @staticmethod
    def _finalize_turn(
        db: Session,
        user_id: int,
        conversation_id: int,
        user_message: str,
        response_content: str,
        tokens_used: int,
    ) -> int:
        ChatCRUD.add_message(db, conversation_id, "assistant", response_content)
        updated_limit = TokenUsageCRUD.deduct_tokens(db, user_id, tokens_used)
        MemoryService.persist_extracted_memories(
            db=db,
            user_id=user_id,
            message=user_message,
            conversation_id=conversation_id,
        )
        return updated_limit.daily_limit

    @staticmethod
    def process_chat(
        message: str,
        conversation_id: Optional[int],
        user_id: int,
        user_tier: str,
        db: Session,
        model_id: Optional[str] = None,
        mode: Optional[str] = "standard",
    ) -> ChatResponse:
        conv_id, formatted_history, user_instructions, relevant_memories = ChatService._validate_policy_and_prepare(
            message, conversation_id, user_id, user_tier, db, model_id=model_id
        )

        effective_mode = (mode or "standard").lower()
        input_state, config = ChatService._build_agent_invocation(
            formatted_history,
            user_instructions,
            relevant_memories,
            user_id,
            user_tier,
            model_id,
            effective_mode,
            conversation_id=conv_id,
        )

        try:
            result = agent.invoke(input_state, config=config)
            final_message = result["messages"][-1]
            response_content = final_message.content

            tokens_used = 0
            if hasattr(final_message, "response_metadata") and final_message.response_metadata:
                token_usage = final_message.response_metadata.get("token_usage", {})
                tokens_used = token_usage.get("total_tokens", 0)

            if tokens_used <= 0 and hasattr(final_message, "usage_metadata") and final_message.usage_metadata:
                tokens_used = final_message.usage_metadata.get("total_tokens", 0)

            if tokens_used <= 0:
                tokens_used = len(message.split()) + len(response_content.split())

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating AI response: {str(e)}",
            )

        tokens_remaining = ChatService._finalize_turn(
            db=db,
            user_id=user_id,
            conversation_id=conv_id,
            user_message=message,
            response_content=response_content,
            tokens_used=tokens_used,
        )

        return ChatResponse(
            response=response_content,
            tokens_used=tokens_used,
            tokens_remaining=tokens_remaining,
            conversation_id=conv_id,
            model_used=model_id or "llama3-8b-8192",
            mode_used=effective_mode,
        )

    @staticmethod
    def _format_sse_event(event_type: Optional[str], payload: dict) -> str:
        if event_type:
            return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        return f"data: {json.dumps(payload)}\n\n"

    @staticmethod
    def _format_sse_error(is_agent_mode: bool, detail: str) -> str:
        if is_agent_mode:
            return ChatService._format_sse_event("error", {"error": detail})
        return ChatService._format_sse_event(None, {"type": "error", "error": detail})

    @staticmethod
    def _format_token_chunk(is_agent_mode: bool, chunk_text: str) -> str:
        if is_agent_mode:
            return ChatService._format_sse_event("token", {"token": chunk_text})
        return ChatService._format_sse_event(None, {"type": "chunk", "content": chunk_text})

    @staticmethod
    def stream_chat(
        message: str,
        conversation_id: Optional[int],
        user_id: int,
        user_tier: str,
        db: Session,
        model_id: Optional[str] = None,
        mode: Optional[str] = "standard",
    ) -> Generator[str, None, None]:
        """
        True Server-Sent Events (SSE) token generator routed through the LangGraph agent.
        Emits typed SSE event envelopes (thought, token, done) in Agent Studio mode while
        preserving legacy chunk/done/error frames for conversational modes.
        """
        effective_mode = (mode or "standard").lower()
        is_agent_mode = effective_mode == "agent"

        try:
            conv_id, formatted_history, user_instructions, relevant_memories = ChatService._validate_policy_and_prepare(
                message=message,
                conversation_id=conversation_id,
                user_id=user_id,
                user_tier=user_tier,
                db=db,
                model_id=model_id,
            )
        except HTTPException as he:
            yield ChatService._format_sse_error(is_agent_mode, he.detail)
            return
        except Exception as exc:
            yield ChatService._format_sse_error(is_agent_mode, f"Error generating AI response: {str(exc)}")
            return

        input_state, config = ChatService._build_agent_invocation(
            formatted_history,
            user_instructions,
            relevant_memories,
            user_id,
            user_tier,
            model_id,
            effective_mode,
            conversation_id=conv_id,
        )

        if is_agent_mode:
            active_model = model_id or "llama3-8b-8192"
            yield ChatService._format_sse_event(
                "thought",
                {"thought": f"Analyzing goal in Agent Studio mode ({active_model})..."},
            )

        emitted_tool_call_ids: set[str] = set()
        step_count = 0
        accumulated_chunks = []
        try:
            for item in agent.stream(input_state, config=config, stream_mode="messages"):
                msg_obj = item[0] if isinstance(item, tuple) else item

                tool_calls = getattr(msg_obj, "tool_calls", None)
                if is_agent_mode and tool_calls:
                    if msg_obj.content and isinstance(msg_obj, AIMessage):
                        yield ChatService._format_sse_event(
                            "thought",
                            {"thought": str(msg_obj.content)},
                        )
                    for tc in tool_calls:
                        tc_id = tc.get("id") or f"act_{step_count + 1}"
                        tc_name = tc.get("name") or ""
                        if tc_name and tc_id not in emitted_tool_call_ids:
                            emitted_tool_call_ids.add(tc_id)
                            step_count += 1
                            tier = get_tool_tier(tc_name)
                            yield ChatService._format_sse_event(
                                "action_call",
                                {
                                    "actionId": tc_id,
                                    "tool": tc_name,
                                    "args": tc.get("args", {}),
                                    "tier": tier,
                                },
                            )
                    continue

                if isinstance(msg_obj, ToolMessage):
                    if is_agent_mode:
                        tc_id = getattr(msg_obj, "tool_call_id", "") or f"act_{step_count}"
                        tc_name = getattr(msg_obj, "name", "") or "workspace_tool"
                        yield ChatService._format_sse_event(
                            "action_result",
                            {
                                "actionId": tc_id,
                                "tool": tc_name,
                                "output": truncate_tool_output(str(msg_obj.content)),
                            },
                        )
                    continue

                content = getattr(msg_obj, "content", "")
                if not content:
                    continue

                if isinstance(msg_obj, AIMessageChunk):
                    accumulated_chunks.append(content)
                    yield ChatService._format_token_chunk(is_agent_mode, content)
                elif isinstance(msg_obj, AIMessage):
                    words = content.split(" ")
                    for idx, word in enumerate(words):
                        chunk_str = (" " if idx > 0 else "") + word
                        accumulated_chunks.append(chunk_str)
                        yield ChatService._format_token_chunk(is_agent_mode, chunk_str)
        except Exception as exc:
            yield ChatService._format_sse_error(is_agent_mode, f"Error generating AI response: {str(exc)}")
            return

        # Check for LangGraph checkpoint interrupt (HITL for Tier 2/3 tools)
        if is_agent_mode:
            try:
                state = agent.get_state(config)
                interrupt_item = None
                for task in getattr(state, "tasks", []):
                    for intr in getattr(task, "interrupts", []):
                        interrupt_item = intr.value
                        break
                    if interrupt_item:
                        break

                if interrupt_item:
                    action_id = interrupt_item.get("actionId") or f"act_{uuid.uuid4().hex[:8]}"
                    tool_name = interrupt_item.get("tool") or "edit_workspace_file"
                    tier = interrupt_item.get("tier", 2)
                    parameters = interrupt_item.get("parameters", {})
                    rationale = interrupt_item.get("rationale", "")
                    diff = interrupt_item.get("diff", "")

                    ChatCRUD.create_or_update_approval(
                        db=db,
                        action_id=action_id,
                        conversation_id=conv_id,
                        user_id=user_id,
                        tool_name=tool_name,
                        tier=tier,
                        parameters=parameters,
                        rationale=rationale,
                        diff=diff,
                    )

                    yield ChatService._format_sse_event(
                        "approval_required",
                        {
                            "actionId": action_id,
                            "tool": tool_name,
                            "toolName": tool_name,
                            "tier": tier,
                            "parameters": parameters,
                            "rationale": rationale,
                            "diff": diff,
                        },
                    )

                    resolved_model = model_id or "llama3-8b-8192"
                    user_limit = TokenUsageCRUD.get_user_limit(db, user_id)
                    remaining = user_limit.daily_limit if user_limit else 0
                    done_envelope = {
                        "status": "interrupted",
                        "actionId": action_id,
                        "totalSteps": max(1, step_count),
                        "conversationId": conv_id,
                        "tokensUsed": len(message.split()),
                        "tokensRemaining": remaining,
                        "modelUsed": resolved_model,
                        "modeUsed": effective_mode,
                    }
                    yield ChatService._format_sse_event("done", done_envelope)
                    return
            except Exception:
                pass

        response_content = "".join(accumulated_chunks)
        tokens_used = len(message.split()) + len(response_content.split())

        tokens_remaining = ChatService._finalize_turn(
            db=db,
            user_id=user_id,
            conversation_id=conv_id,
            user_message=message,
            response_content=response_content,
            tokens_used=tokens_used,
        )

        resolved_model = model_id or "llama3-8b-8192"
        if is_agent_mode:
            done_envelope = {
                "status": "completed",
                "totalSteps": max(1, step_count + 1),
                "conversationId": conv_id,
                "tokensUsed": tokens_used,
                "tokensRemaining": tokens_remaining,
                "modelUsed": resolved_model,
                "modeUsed": effective_mode,
            }
            yield ChatService._format_sse_event("done", done_envelope)
            return

        done_payload = {
            "type": "done",
            "conversation_id": conv_id,
            "tokens_used": tokens_used,
            "tokens_remaining": tokens_remaining,
            "model_used": resolved_model,
            "mode_used": effective_mode,
        }
        yield ChatService._format_sse_event(None, done_payload)

    @staticmethod
    def resume_approval(
        db: Session,
        user_id: int,
        action_id: str,
        decision: str,
        modified_params: Optional[dict] = None,
        feedback: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Resumes an interrupted LangGraph checkpoint after user approves,
        modifies, or rejects a Tier 2 action.
        """
        approval = ChatCRUD.get_approval_by_id(db, action_id, user_id=user_id)
        if not approval:
            yield ChatService._format_sse_error(True, "Approval request not found or unauthorized.")
            return

        if approval.status != "pending":
            yield ChatService._format_sse_error(True, f"Approval request is already {approval.status}.")
            return

        # Update approval in DB
        ChatCRUD.resolve_approval(db, action_id, decision=decision, feedback=feedback)

        conversation_id = approval.conversation_id
        user_limit = TokenUsageCRUD.get_user_limit(db, user_id)
        if user_limit and user_limit.daily_limit <= 0:
            yield ChatService._format_sse_error(True, "Daily token limit exceeded.")
            return

        resume_payload = {
            "decision": decision,
            "modifiedParams": modified_params or {},
            "feedback": feedback or "",
        }

        config = {
            "configurable": {
                "thread_id": str(conversation_id),
                "user_id": user_id,
                "mode": "agent",
            }
        }

        step_count = 0
        accumulated_chunks = []
        last_tool_output = ""

        try:
            for item in agent.stream(Command(resume=resume_payload), config=config, stream_mode="messages"):
                msg_obj = item[0] if isinstance(item, tuple) else item

                tool_calls = getattr(msg_obj, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        tc_id = tc.get("id") or f"act_{step_count + 1}"
                        tc_name = tc.get("name") or ""
                        tier = get_tool_tier(tc_name)
                        yield ChatService._format_sse_event(
                            "action_call",
                            {
                                "actionId": tc_id,
                                "tool": tc_name,
                                "args": tc.get("args", {}),
                                "tier": tier,
                            },
                        )
                    continue

                if isinstance(msg_obj, ToolMessage):
                    step_count += 1
                    out_str = truncate_tool_output(str(msg_obj.content))
                    last_tool_output = out_str
                    yield ChatService._format_sse_event(
                        "action_result",
                        {
                            "actionId": action_id,
                            "tool": approval.tool_name,
                            "output": out_str,
                        },
                    )
                    continue

                content = getattr(msg_obj, "content", "")
                if not content:
                    continue

                if isinstance(msg_obj, AIMessageChunk):
                    accumulated_chunks.append(content)
                    yield ChatService._format_token_chunk(True, content)
                elif isinstance(msg_obj, AIMessage):
                    words = content.split(" ")
                    for idx, word in enumerate(words):
                        chunk_str = (" " if idx > 0 else "") + word
                        accumulated_chunks.append(chunk_str)
                        yield ChatService._format_token_chunk(True, chunk_str)
        except Exception as exc:
            yield ChatService._format_sse_error(True, f"Error resuming agent: {str(exc)}")
            return

        # Check if there is another interrupt
        state = agent.get_state(config)
        next_interrupt = None
        for task in getattr(state, "tasks", []):
            for intr in getattr(task, "interrupts", []):
                next_interrupt = intr.value
                break
            if next_interrupt:
                break

        if next_interrupt:
            next_action_id = next_interrupt.get("actionId") or f"act_{uuid.uuid4().hex[:8]}"
            next_tool = next_interrupt.get("tool") or "edit_workspace_file"
            next_tier = next_interrupt.get("tier", 2)
            next_params = next_interrupt.get("parameters", {})
            next_rationale = next_interrupt.get("rationale", "")
            next_diff = next_interrupt.get("diff", "")

            ChatCRUD.create_or_update_approval(
                db=db,
                action_id=next_action_id,
                conversation_id=conversation_id,
                user_id=user_id,
                tool_name=next_tool,
                tier=next_tier,
                parameters=next_params,
                rationale=next_rationale,
                diff=next_diff,
            )

            yield ChatService._format_sse_event(
                "approval_required",
                {
                    "actionId": next_action_id,
                    "tool": next_tool,
                    "toolName": next_tool,
                    "tier": next_tier,
                    "parameters": next_params,
                    "rationale": next_rationale,
                    "diff": next_diff,
                },
            )
            done_envelope = {
                "status": "interrupted",
                "actionId": next_action_id,
                "totalSteps": max(1, step_count),
                "conversationId": conversation_id,
                "tokensUsed": 10,
                "tokensRemaining": user_limit.daily_limit if user_limit else 0,
                "modelUsed": "llama3-8b-8192",
                "modeUsed": "agent",
            }
            yield ChatService._format_sse_event("done", done_envelope)
            return

        response_content = "".join(accumulated_chunks)
        if not response_content.strip():
            response_content = f"Action '{approval.tool_name}' {decision}ed: {last_tool_output}"

        tokens_used = max(10, len(response_content.split()))
        tokens_remaining = ChatService._finalize_turn(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=f"[{decision.upper()}] {approval.tool_name}",
            response_content=response_content,
            tokens_used=tokens_used,
        )

        done_envelope = {
            "status": "completed",
            "totalSteps": max(1, step_count + 1),
            "conversationId": conversation_id,
            "tokensUsed": tokens_used,
            "tokensRemaining": tokens_remaining,
            "modelUsed": "llama3-8b-8192",
            "modeUsed": "agent",
        }
        yield ChatService._format_sse_event("done", done_envelope)
