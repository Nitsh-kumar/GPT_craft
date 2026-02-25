import uvicorn
from fastapi import FastAPI
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes.auth import router as auth_router
from app.db.models import User

# Initialize settings
settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API with user authentication using hybrid architecture",
    version=settings.app_version,
    debug=settings.debug
)

# Include feature routes
app.include_router(auth_router)


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