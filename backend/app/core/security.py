from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

# Password hashing context
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# In-memory cache for Supabase JWKS public keys
_JWKS_CACHE: Optional[Dict[str, Any]] = None


class SecurityService:
    """Security utilities for password, token management, and Supabase JWKS verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using argon2"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        settings = get_settings()
        
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode = {"email": email, "exp": expire}
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def _get_supabase_jwks(supabase_url: str) -> Optional[Dict[str, Any]]:
        global _JWKS_CACHE
        if _JWKS_CACHE is not None:
            return _JWKS_CACHE
        try:
            jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            response = httpx.get(jwks_url, timeout=5.0)
            if response.status_code == 200:
                _JWKS_CACHE = response.json()
                return _JWKS_CACHE
        except Exception:
            pass
        return None

    @staticmethod
    def decode_token_claims(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and verify JWT token claims.
        Supports Supabase ES256/RS256 tokens via JWKS, as well as symmetric HS256 tokens.
        Returns a dictionary containing 'email', 'sub' (if present), and 'name' (if present).
        """
        settings = get_settings()

        # 1. Attempt Supabase JWKS verification if Supabase URL is configured
        if settings.supabase_url:
            jwks = SecurityService._get_supabase_jwks(settings.supabase_url)
            if jwks:
                try:
                    payload = jwt.decode(
                        token,
                        jwks,
                        algorithms=["ES256", "RS256"],
                        audience="authenticated",
                        options={"verify_aud": False}  # Lenient audience verification
                    )
                    email = payload.get("email")
                    sub = payload.get("sub")
                    meta = payload.get("user_metadata") or {}
                    name = meta.get("full_name") or meta.get("name") or (email.split("@")[0] if email else "User")
                    if email:
                        return {
                            "email": email,
                            "sub": sub,
                            "name": name,
                            "payload": payload
                        }
                except JWTError:
                    pass

        # 2. Attempt Supabase JWT Secret if configured (symmetric HS256)
        if settings.supabase_jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
                email = payload.get("email")
                sub = payload.get("sub")
                meta = payload.get("user_metadata") or {}
                name = meta.get("full_name") or meta.get("name") or (email.split("@")[0] if email else "User")
                if email:
                    return {
                        "email": email,
                        "sub": sub,
                        "name": name,
                        "payload": payload
                    }
            except JWTError:
                pass

        # 3. Fallback to local app secret key (for testing and legacy tokens)
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            email: str = payload.get("email")
            if email:
                return {
                    "email": email,
                    "sub": payload.get("sub"),
                    "name": payload.get("name") or email.split("@")[0],
                    "payload": payload
                }
        except JWTError:
            pass

        return None

    @staticmethod
    def decode_access_token(token: str) -> Optional[str]:
        """
        Verify and decode JWT token, returns email if valid, None otherwise.
        Maintains backward compatibility with all existing callers.
        """
        claims = SecurityService.decode_token_claims(token)
        if claims:
            return claims.get("email")
        return None
