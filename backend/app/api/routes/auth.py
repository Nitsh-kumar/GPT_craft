from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse, LoginResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register new user"""
    user = AuthService.register(request.email, request.password, request.name, db)
    return user


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token"""
    user, access_token = AuthService.login(request.email, request.password, db)
    response = LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )
    return response.model_dump(by_alias=True)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    token: str = Query(..., description="Bearer token"),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    user = AuthService.get_user_by_token(token, db)
    return user
