from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import List
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
    ModelInfoResponse,
    QuotaResponse,
)
from app.services.chat import ChatService
from app.services.auth import AuthService
from app.db.models import User
from app.db.crud_token import TokenUsageCRUD
from app.db.crud_chat import ChatCRUD
from app.ai.llm import MODEL_CATALOG, PLAN_QUOTAS

router = APIRouter(prefix="/chat", tags=["chat"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.get_user_by_token(token, db)


limiter = Limiter(key_func=get_remote_address)


@router.get("/models", response_model=List[ModelInfoResponse])
def list_models():
    """Return available AI models and their required subscription tier"""
    return [
        ModelInfoResponse(
            id=m["id"],
            name=m["name"],
            description=m["description"],
            requiredPlan=m["requiredPlan"],
        )
        for m in MODEL_CATALOG
    ]


@router.get("/quota", response_model=QuotaResponse)
def get_quota(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the current user's token and request quota"""
    from datetime import date, datetime
    from app.db.models import Conversation, Message

    tier = getattr(current_user, "plan", "free").lower()
    tier_quota = PLAN_QUOTAS.get(tier, PLAN_QUOTAS["free"])
    total_tokens = tier_quota["tokens"]
    total_requests = tier_quota["requests"]

    user_limit = TokenUsageCRUD.get_user_limit(db, current_user.id)
    if not user_limit:
        user_limit = TokenUsageCRUD.create_user_limit(db, current_user.id, initial_limit=total_tokens)

    today_start = datetime.combine(date.today(), datetime.min.time())
    requests_used = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Message.role == "user",
            Message.created_at >= today_start,
        )
        .count()
    )

    return {
        "requestsRemaining": max(0, total_requests - requests_used),
        "tokensRemaining": user_limit.daily_limit,
        "totalRequests": total_requests,
        "totalTokens": total_tokens,
    }


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all previous conversations for the user"""
    return ChatCRUD.get_conversations_for_user(db, current_user.id)


@router.get("/{conversation_id}/history", response_model=List[MessageResponse])
def get_history(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the full message history for a conversation"""
    conversation = ChatCRUD.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ChatCRUD.get_messages_for_conversation(db, conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete an owned conversation and its messages"""
    deleted = ChatCRUD.delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(status_code=204)


@router.post("/stream")
def chat_stream_endpoint(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream AI chat response via Server-Sent Events (SSE)"""
    tier = getattr(current_user, "plan", "free").lower()
    generator = ChatService.stream_chat(
        message=body.message,
        conversation_id=body.conversation_id,
        user_id=current_user.id,
        user_tier=tier,
        db=db,
        model_id=body.model,
        mode=body.mode,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("", response_model=ChatResponse)
def chat_endpoint(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the AI under token policy enforcement and tier-based model routing"""
    tier = getattr(current_user, "plan", "free").lower()
    return ChatService.process_chat(
        body.message,
        body.conversation_id,
        current_user.id,
        tier,
        db,
        model_id=body.model,
        mode=body.mode,
    )
