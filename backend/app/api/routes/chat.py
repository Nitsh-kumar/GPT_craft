from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse, QuotaResponse
from app.services.chat import ChatService
from app.services.auth import AuthService
from app.db.models import User
from app.db.crud_token import TokenUsageCRUD
from app.db.crud_chat import ChatCRUD

router = APIRouter(prefix="/chat", tags=["chat"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.get_user_by_token(token, db)

limiter = Limiter(key_func=get_remote_address)

def get_rate_limit_based_on_tier(request: Request):
    try:
        current_user = request.state.user
        if current_user and current_user.plan and current_user.plan.name.lower() == "pro":
            return "50/minute"
        return "10/minute"
    except Exception:
        return "10/minute"

@router.get("/quota", response_model=QuotaResponse)
def get_quota(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the current user's token quota"""
    from datetime import date, datetime
    from app.db.models import Conversation, Message
    
    user_limit = TokenUsageCRUD.get_user_limit(db, current_user.id)
    if not user_limit:
        user_limit = TokenUsageCRUD.create_user_limit(db, current_user.id, initial_limit=5000)
    
    tier = getattr(current_user.plan, "name", "free").lower()
    total_tokens = 5000 if tier == "free" else 50000
    total_requests = 50 if tier == "free" else 500
    
    # Count today's user messages as requests
    today_start = datetime.combine(date.today(), datetime.min.time())
    requests_used = db.query(Message).join(Conversation).filter(
        Conversation.user_id == current_user.id,
        Message.role == "user",
        Message.created_at >= today_start
    ).count()
    
    return {
        "requestsRemaining": max(0, total_requests - requests_used),
        "tokensRemaining": user_limit.daily_limit,
        "totalRequests": total_requests,
        "totalTokens": total_tokens
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

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: Request, body: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chat with the AI under token policy enforcement and tier-based rate limit"""
    tier = getattr(current_user.plan, "name", "free").lower()
    return ChatService.process_chat(body.message, body.conversation_id, current_user.id, tier, db)
