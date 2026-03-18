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

# Seed default plan if it doesn't exist
def seed_default_plan():
    """Ensure at least a 'Free' plan exists (id=1) for OAuth user creation."""
    db = SessionLocal()
    try:
        existing = db.query(Plans).filter(Plans.id == 1).first()
        if not existing:
            free_plan = Plans(id=1, name="free", price=0, description="Free plan - 50 requests/day")
            db.add(free_plan)
            db.commit()
            print("✅ Seeded default 'free' plan (id=1)")
        else:
            print("✅ Default plan already exists")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to seed default plan: {e}")
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

# Set up CORS — allow frontend origins (support both common dev ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
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