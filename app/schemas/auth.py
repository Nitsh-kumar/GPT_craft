from pydantic import BaseModel, EmailStr
from datetime import datetime

class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    """User registration request"""
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """User data response"""
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    """Login response with token"""
    access_token: str
    token_type: str
    user: UserResponse
