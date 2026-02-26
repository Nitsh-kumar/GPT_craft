from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tokens_used: int
    tokens_remaining: int
