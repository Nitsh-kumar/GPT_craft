from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User, Plans, OAuthAccount
from app.core.security import SecurityService
from app.schemas.auth import UserResponse


class InactiveAccountError(Exception):
    """Raised when an authenticated account is marked inactive."""


class AuthService:
    """Centralized authentication and subscription business logic"""

    @staticmethod
    def _ensure_active(user: User) -> None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

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

        AuthService._ensure_active(user)
        
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
            if user:
                AuthService._ensure_active(user)
        
        # 2. Lookup by email fallback
        if not user:
            user = db.query(User).filter(User.email == email).first()
            if user:
                AuthService._ensure_active(user)
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

        AuthService._ensure_active(user)
        
        return AuthService._user_to_response(user)

    @staticmethod
    def login_with_google(
        db: Session,
        *,
        email: str,
        name: Optional[str],
        google_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> str:
        """Resolve or provision a Google OAuth user and issue an app session token."""
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_id,
        ).first()

        if oauth_account:
            user = oauth_account.user
            if not user.is_active:
                raise InactiveAccountError()
            oauth_account.access_token = access_token
            oauth_account.refresh_token = refresh_token if refresh_token is not None else oauth_account.refresh_token
            oauth_account.expires_at = expires_at
        else:
            user = db.query(User).filter(User.email == email).first()
            if user and not user.is_active:
                raise InactiveAccountError()
            if not user:
                user = User(
                    email=email,
                    name=name or email.split("@")[0],
                    hashed_password=None,
                    plan_id=1,
                )
                db.add(user)
                db.flush()

            db.add(
                OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=google_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                )
            )

        db.commit()
        if not user.is_active:
            raise InactiveAccountError()
        return SecurityService.create_access_token(user.email)

    @staticmethod
    def upgrade_plan(user_id: int, plan_name: str, db: Session) -> UserResponse:
        # Entitlements must come from verified billing or an administrator, never
        # a user-supplied plan name. Keep the endpoint closed until billing exists.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plan changes are currently unavailable. Your current plan is unchanged.",
        )
