import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.google_oauth import router as google_auth_router
from app.db.models import User, Plans

# Initialize settings
settings = get_settings()

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Create database tables
Base.metadata.create_all(bind=engine)

# Seed default plans if they don't exist
def seed_default_plan():
    """Ensure Free, Super, and Hyper plans exist in the database."""
    db = SessionLocal()
    try:
        default_plans = [
            {"id": 1, "name": "free", "price": 0, "description": "Free plan - 50 requests/day, 5,000 tokens"},
            {"id": 2, "name": "super", "price": 15, "description": "Super plan - 500 requests/day, 50,000 tokens"},
            {"id": 3, "name": "hyper", "price": 39, "description": "Hyper plan - 5,000 requests/day, 500,000 tokens"},
        ]
        for plan_data in default_plans:
            existing = db.query(Plans).filter(Plans.id == plan_data["id"]).first()
            if not existing:
                db.add(Plans(**plan_data))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to seed default plans: {e}")
    finally:
        db.close()


seed_default_plan()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API with user authentication using hybrid architecture",
    version=settings.app_version,
    debug=settings.debug
)

# Set up CORS — allow frontend origins (support both common dev ports and custom domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://gptcraft.in",
        "https://www.gptcraft.in",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Session Middleware (Required for OAuth state/nonce)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Include feature routes
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(google_auth_router)


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    uvicorn.run(app)