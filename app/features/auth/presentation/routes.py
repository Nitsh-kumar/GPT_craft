from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.features.auth.application.dto.schemas import (
    LoginRequest,
    RegisterRequest,
    LoginResponseDTO,
    RegisterResponseDTO,
    UserDTO,
    TokenDTO
)
from app.features.auth.application.use_cases.register_use_case import RegisterUseCase
from app.features.auth.application.use_cases.login_use_case import LoginUseCase
from app.features.auth.application.use_cases.get_current_user_use_case import GetCurrentUserUseCase
from app.features.auth.infrastructure.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Dependency injection for UserRepository"""
    return UserRepository(db)


@router.post("/register", response_model=RegisterResponseDTO, status_code=201)
def register(
    request: RegisterRequest,
    user_repository: UserRepository = Depends(get_user_repository)
):
    """
    Register a new user
    
    - **email**: User email address
    - **password**: User password
    """
    use_case = RegisterUseCase(user_repository)
    user = use_case.execute(request.email, request.password)
    
    return RegisterResponseDTO(
        id=user.id,
        email=user.email,
        message="User registered successfully"
    )


@router.post("/login", response_model=LoginResponseDTO)
def login(
    request: LoginRequest,
    user_repository: UserRepository = Depends(get_user_repository)
):
    """
    Login user with email and password
    
    - **email**: User email address
    - **password**: User password
    
    Returns JWT access token and user information
    """
    use_case = LoginUseCase(user_repository)
    user, access_token = use_case.execute(request.email, request.password)
    
    return LoginResponseDTO(
        token=TokenDTO(access_token=access_token, token_type="bearer"),
        user=UserDTO(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )


@router.get("/me", response_model=UserDTO)
def get_current_user(
    token: str = Query(..., description="Bearer token from login"),
    user_repository: UserRepository = Depends(get_user_repository)
):
    """
    Get current authenticated user
    
    - **token**: JWT access token
    """
    use_case = GetCurrentUserUseCase(user_repository)
    user = use_case.execute(token)
    
    return UserDTO(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
