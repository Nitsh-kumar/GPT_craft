from typing import Optional
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "Auth Service API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./app.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI API Keys
    groq_api_key: Optional[str] = None
    
    max_output_tokens: int = Field(default=1024, ge=1, le=4096)
    generation_timeout_seconds: int = Field(default=60, ge=1, le=90)
    chat_burst_limit: int = Field(default=10, ge=1, le=100)

    # Frontend URL (for CORS and OAuth redirects)
    frontend_url: str = "http://localhost:3000"
    
    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # Supabase Auth & Database
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_jwt_secret: Optional[str] = None
    
    model_config = ConfigDict(
        env_file=(".env", "backend/.env"),
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()

