from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16000)
    conversation_id: Optional[int] = None
    model: Optional[str] = None
    mode: Optional[str] = "standard"
    request_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    response: str
    tokens_used: int
    tokens_remaining: int
    conversation_id: int
    usage_estimated: bool = False
    model_used: Optional[str] = None
    mode_used: Optional[str] = "standard"


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_used: Optional[str] = None
    mode_used: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuotaResponse(BaseModel):
    requestsRemaining: int
    tokensRemaining: int
    totalRequests: int
    totalTokens: int


class ModelInfoResponse(BaseModel):
    id: str
    name: str
    description: str
    requiredPlan: str
