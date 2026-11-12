import json
from contextlib import aclosing
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, Request, HTTPException, Response
from app.api.streaming import CancellableStreamingResponse
from typing import List
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
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
from app.ai.llm import MODEL_CATALOG

router = APIRouter(prefix="/chat", tags=["chat"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.get_user_by_token(token, db)




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
    return TokenUsageCRUD.quota(db, current_user.id, current_user.plan.lower())


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


async def prepare_chat(body, current_user, db):
    return await run_in_threadpool(
        ChatService.prepare, message=body.message, conversation_id=body.conversation_id,
        user_id=current_user.id, user_tier=current_user.plan.lower(), db=db,
        model_id=body.model, mode=body.mode,
        request_id=str(body.request_id) if body.request_id else None,
    )


@router.post("/stream")
async def chat_stream_endpoint(
    request: Request, body: ChatRequest,
    current_user=Depends(get_current_user), db: Session = Depends(get_db),
):
    prepared = await prepare_chat(body, current_user, db)

    async def stream():
        async with aclosing(ChatService.events(prepared)) as events:
            async for event in events:
                yield f"data: {json.dumps(event)}\n\n"

    return CancellableStreamingResponse(stream(), on_disconnect=prepared.cancel.set, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: Request, body: ChatRequest,
    current_user=Depends(get_current_user), db: Session = Depends(get_db),
):
    prepared = await prepare_chat(body, current_user, db)
    text = ""
    result = None
    # Close and settle before raising an HTTP error or returning a response.
    async with aclosing(ChatService.events(prepared)) as events:
        async for event in events:
            if event["type"] == "chunk":
                text += event["content"]
            elif event["type"] == "error":
                raise HTTPException(event["status"], event["error"])
            elif event["type"] == "done":
                result = {key: value for key, value in event.items() if key != "type"}
    return ChatResponse(response=text, **result)
