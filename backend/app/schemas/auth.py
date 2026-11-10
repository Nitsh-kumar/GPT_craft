from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request"""
    name: str
    email: EmailStr
    password: str


class UpgradePlanRequest(BaseModel):
    """Upgrade user subscription plan"""
    plan: str


class UserResponse(BaseModel):
    """User data response — aligned with frontend User type"""
    id: int
    name: str
    email: str
    plan: str = "free"  # Computed from the plan relationship

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """Login response with token — uses camelCase aliases to match frontend"""
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(serialization_alias="tokenType")
    user: UserResponse

    model_config = ConfigDict(populate_by_name=True)
