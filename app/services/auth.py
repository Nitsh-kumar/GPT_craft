from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User
from app.core.security import SecurityService
from app.schemas.auth import UserResponse


class AuthService:
    """Centralized authentication business logic"""

    @staticmethod
    def _user_to_response(user: User) -> UserResponse:
        """Convert a User ORM model to a UserResponse with plan name."""
        plan_name = "free"
        if user.plan:
            plan_name = user.plan.name.lower()
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            plan=plan_name
        )

    @staticmethod
    def register(email: str, password: str, name: str, db: Session) -> UserResponse:
        # Check if user already exists 
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = SecurityService.hash_password(password)
        user = User(
            email=email, 
            name=name, 
            hashed_password=hashed_password,
            plan_id=1 # Default to Free plan
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AuthService._user_to_response(user)

    @staticmethod
    def login(email: str, password: str, db: Session) -> tuple[UserResponse, str]:
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Handle OAuth-only users trying to use password login
        if user.hashed_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses Google Sign-In. Please use the 'Sign in with Google' button."
            )
        
        # Verify password
        if not SecurityService.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        access_token = SecurityService.create_access_token(user.email)
        return AuthService._user_to_response(user), access_token

    @staticmethod
    def get_user_by_token(token: str, db: Session) -> UserResponse:
        email = SecurityService.decode_access_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return AuthService._user_to_response(user)
