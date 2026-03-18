from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.services.auth import AuthService
from app.db.models import User

router = APIRouter(prefix="/chat", tags=["chat"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.get_user_by_token(token, db)

limiter = Limiter(key_func=get_remote_address)

def get_rate_limit_based_on_tier(request: Request):
    """Dynamic rate limiter based on user tier extracted from request state"""
    try:
        current_user = request.state.user
        if current_user and current_user.plan and current_user.plan.name.lower() == "pro":
            return "50/minute"
        return "10/minute"
    except Exception:
        # Fallback to strictest limit if we can't determine tier
        return "10/minute"

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: Request, body: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chat with the AI under token policy enforcement and tier-based rate limit"""
    tier = getattr(current_user.plan, "name", "free").lower()
    return ChatService.process_chat(body.message, current_user.id, tier, db)
