from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# Request DTOs
class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Register request"""
    Name: str
    email: EmailStr
    password: str


# Response DTOs
class UserDTO(BaseModel):
    """User response DTO"""
    id: int
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenDTO(BaseModel):
    """Token response DTO"""
    access_token: str
    token_type: str


class LoginResponseDTO(BaseModel):
    """Login response with token and user info"""
    token: TokenDTO
    user: UserDTO


class RegisterResponseDTO(BaseModel):
    """Register response"""
    id: int
    email: str
    message: str
