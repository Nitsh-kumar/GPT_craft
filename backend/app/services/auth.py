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
        claims = SecurityService.decode_token_claims(token)
        if not claims or not claims.get("email"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        email = claims["email"]
        sub = claims.get("sub")
        name = claims.get("name") or email.split("@")[0]

        # 1. Lookup by supabase_uid if present
        user = None
        if sub:
            user = db.query(User).filter(User.supabase_uid == sub).first()
        
        # 2. Lookup by email fallback
        if not user:
            user = db.query(User).filter(User.email == email).first()
            if user:
                changed = False
                if sub and not user.supabase_uid:
                    user.supabase_uid = sub
                    changed = True
                if name and (not user.name or user.name.strip() in ("", "User")):
                    user.name = name
                    changed = True
                if changed:
                    db.commit()
                    db.refresh(user)
        
        # 3. If user signed up via Supabase and does not exist in DB yet, auto-provision
        if not user:
            free_plan = db.query(Plans).filter(Plans.name == "free").first()
            plan_id = free_plan.id if free_plan else 1
            user = User(
                email=email,
                name=name,
                supabase_uid=sub,
                plan_id=plan_id,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 4. Ensure user daily token limit exists for today
        user_limit = TokenUsageCRUD.get_user_limit(db, user.id)
        if not user_limit:
            plan_name = user.plan.name.lower() if user.plan else "free"
            TokenUsageCRUD.create_user_limit(
                db, 
                user.id, 
                initial_limit=PLAN_QUOTAS.get(plan_name, {}).get("tokens", 5000)
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return AuthService._user_to_response(user)

    @staticmethod
    def upgrade_plan(user_id: int, plan_name: str, db: Session) -> UserResponse:
        # Entitlements must come from verified billing or an administrator, never
        # a user-supplied plan name. Keep the endpoint closed until billing exists.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plan changes are currently unavailable. Your current plan is unchanged.",
        )
