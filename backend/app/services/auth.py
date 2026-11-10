from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User, Plans
from app.db.crud_token import TokenUsageCRUD
from app.core.security import SecurityService
from app.schemas.auth import UserResponse
from app.ai.llm import PLAN_QUOTAS


class AuthService:
    """Centralized authentication and subscription business logic"""

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
            plan_id=1  # Default to Free plan
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AuthService._user_to_response(user)

    @staticmethod
    def login(email: str, password: str, db: Session) -> tuple[UserResponse, str]:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if user.hashed_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses Google Sign-In. Please use the 'Sign in with Google' button."
            )
        
        if not SecurityService.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

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
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return AuthService._user_to_response(user)

    @staticmethod
    def upgrade_plan(user_id: int, plan_name: str, db: Session) -> UserResponse:
        normalized = plan_name.strip().lower()
        if normalized not in ("free", "super", "hyper"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan. Choose from: free, super, hyper"
            )

        plan_obj = db.query(Plans).filter(Plans.name == normalized).first()
        if not plan_obj:
            plan_map = {"free": (1, 0), "super": (2, 15), "hyper": (3, 39)}
            pid, price = plan_map[normalized]
            plan_obj = Plans(id=pid, name=normalized, price=price, description=f"{normalized.capitalize()} plan")
            db.add(plan_obj)
            db.flush()

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.plan_id = plan_obj.id
        db.commit()
        db.refresh(user)

        # Update daily token limit to match the new tier's allowance
        new_token_limit = PLAN_QUOTAS[normalized]["tokens"]
        user_limit = TokenUsageCRUD.get_user_limit(db, user.id)
        if user_limit:
            user_limit.daily_limit = new_token_limit
            db.commit()
        else:
            TokenUsageCRUD.create_user_limit(db, user.id, initial_limit=new_token_limit)

        return AuthService._user_to_response(user)
