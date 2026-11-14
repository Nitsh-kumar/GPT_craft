from typing import Optional
from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache

PLACEHOLDER_SECRET_KEYS = frozenset({
    "",
    "your-secret-key-change-in-production",
    "replace_with_a_new_random_secret",
    "changeme",
    "change-me",
    "secret",
})


def validate_runtime_secret_key(settings: "Settings") -> None:
    """Reject default or placeholder signing secrets when debug mode is disabled."""
    normalized = (settings.secret_key or "").strip().lower()
    if not settings.debug and normalized in PLACEHOLDER_SECRET_KEYS:
        raise ValueError(
            "SECRET_KEY must be set to a strong non-placeholder value when debug is False"
        )


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

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        validate_runtime_secret_key(self)
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()

