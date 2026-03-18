from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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
    """User data response — aligned with frontend User type"""
    id: int
    name: str
    email: str
    plan: str = "free"  # Computed from the plan relationship

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with token — uses camelCase aliases to match frontend"""
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(serialization_alias="tokenType")
    user: UserResponse

    class Config:
        populate_by_name = True
