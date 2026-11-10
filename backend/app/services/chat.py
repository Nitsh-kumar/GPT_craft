import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage
from typing import Optional, Generator
from app.db.crud_token import TokenUsageCRUD
from app.db.crud_chat import ChatCRUD
from app.schemas.chat import ChatResponse
from app.ai.graph.agent import agent
from app.ai.llm import ALLOWED_MODELS, PLAN_QUOTAS, is_tier_allowed


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

        history = ChatCRUD.get_messages_for_conversation(db, conversation_id)
        formatted_history = []
        for msg in history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            else:
                formatted_history.append(AIMessage(content=msg.content))

        return conversation_id, formatted_history

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
        conv_id, formatted_history = ChatService._validate_policy_and_prepare(
            message, conversation_id, user_id, user_tier, db, model_id=model_id
        )

        effective_mode = (mode or "standard").lower()
        input_state = {"messages": formatted_history}
        config = {
            "configurable": {
                "user_id": user_id,
                "user_tier": user_tier,
                "model_id": model_id,
                "mode": effective_mode,
            }
        }

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

        ChatCRUD.add_message(db, conv_id, "assistant", response_content)
        updated_limit = TokenUsageCRUD.deduct_tokens(db, user_id, tokens_used)

        return ChatResponse(
            response=response_content,
            tokens_used=tokens_used,
            tokens_remaining=updated_limit.daily_limit,
            conversation_id=conv_id,
            model_used=model_id or "llama3-8b-8192",
            mode_used=effective_mode,
        )

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
        Server-Sent Events (SSE) generator for token-by-token streaming over HTTP.
        Catches any runtime or upstream LLM errors and streams a structured error event
        to prevent HTTP stream aborts / network connection resets.
        """
        try:
            result = ChatService.process_chat(
                message=message,
                conversation_id=conversation_id,
                user_id=user_id,
                user_tier=user_tier,
                db=db,
                model_id=model_id,
                mode=mode,
            )
        except HTTPException as he:
            yield f"data: {json.dumps({'type': 'error', 'error': he.detail})}\n\n"
            return
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': f'Error generating AI response: {str(exc)}'})}\n\n"
            return

        words = result.response.split(" ")
        for idx, word in enumerate(words):
            chunk = (" " if idx > 0 else "") + word
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        done_payload = {
            "type": "done",
            "conversation_id": result.conversation_id,
            "tokens_used": result.tokens_used,
            "tokens_remaining": result.tokens_remaining,
            "model_used": result.model_used,
            "mode_used": result.mode_used,
        }
        yield f"data: {json.dumps(done_payload)}\n\n"
