import time
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

# In-memory cache for Supabase JWKS public keys (bounded by TTL and url)
_JWKS_CACHE_TTL_SECONDS = 300
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
    def _jwks_has_kid(jwks: Optional[Dict[str, Any]], kid: Optional[str]) -> bool:
        if not kid or not isinstance(jwks, dict):
            return True
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            return False
        return any(isinstance(k, dict) and k.get("kid") == kid for k in keys)

    @staticmethod
    def _get_supabase_jwks(
        supabase_url: str,
        kid: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        global _JWKS_CACHE
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        now = time.monotonic()

        cached_jwks: Optional[Dict[str, Any]] = None
        cache_valid = False
        if isinstance(_JWKS_CACHE, dict):
            if (
                "jwks" in _JWKS_CACHE
                and "fetched_at" in _JWKS_CACHE
                and _JWKS_CACHE.get("url") == jwks_url
                and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_CACHE_TTL_SECONDS
            ):
                cached_jwks = _JWKS_CACHE["jwks"]
                cache_valid = True

        if cache_valid and not force_refresh and SecurityService._jwks_has_kid(cached_jwks, kid):
            return cached_jwks

        try:
            response = httpx.get(jwks_url, timeout=5.0)
            if response.status_code == 200:
                jwks = response.json()
                _JWKS_CACHE = {
                    "url": jwks_url,
                    "jwks": jwks,
                    "fetched_at": now,
                }
                return jwks
        except Exception:
            pass

        if cache_valid and not force_refresh:
            return cached_jwks
        return None

    @staticmethod
    def _extract_supabase_claims(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        aud = payload.get("aud")
        valid_aud = (
            aud == "authenticated"
            if isinstance(aud, str)
            else isinstance(aud, list) and "authenticated" in aud
        )
        if not valid_aud:
            return None
        email = payload.get("email")
        if not email:
            return None
        sub = payload.get("sub")
        meta = payload.get("user_metadata") or {}
        name = meta.get("full_name") or meta.get("name") or email.split("@")[0]
        return {
            "email": email,
            "sub": sub,
            "name": name,
            "payload": payload,
        }

    @staticmethod
    def decode_token_claims(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and verify JWT token claims.
        Supports Supabase ES256/RS256 tokens via JWKS, as well as symmetric HS256 tokens.
        Returns a dictionary containing 'email', 'sub' (if present), and 'name' (if present).
        """
        settings = get_settings()
        token_kid: Optional[str] = None
        try:
            token_kid = jwt.get_unverified_header(token).get("kid")
        except JWTError:
            token_kid = None

        # 1. Attempt Supabase JWKS verification if Supabase URL is configured
        if settings.supabase_url:
            jwks = SecurityService._get_supabase_jwks(settings.supabase_url, kid=token_kid)
            if jwks:
                try:
                    payload = jwt.decode(
                        token,
                        jwks,
                        algorithms=["ES256", "RS256"],
                        audience="authenticated",
                    )
                    claims = SecurityService._extract_supabase_claims(payload)
                    if claims:
                        return claims
                except JWTError:
                    pass

        # 2. Attempt Supabase JWT Secret if configured (symmetric HS256)
        if settings.supabase_jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
                claims = SecurityService._extract_supabase_claims(payload)
                if claims:
                    return claims
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
