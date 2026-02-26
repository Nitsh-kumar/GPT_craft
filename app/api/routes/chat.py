from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.services.auth import AuthService
from app.db.models import User

router = APIRouter(prefix="/chat", tags=["chat"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.get_user_by_token(token, db)

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chat with the AI under token policy enforcement"""
    return ChatService.process_chat(request.message, current_user.id, db)
