import logging
import urllib.parse
from fastapi import APIRouter, Depends, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import get_settings
from app.services.auth import AuthService, InactiveAccountError
from starlette.responses import RedirectResponse

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth/google", tags=["google-auth"])

# Frontend URLs (configurable via settings)
FRONTEND_URL = settings.frontend_url
FRONTEND_LOGIN_URL = f"{FRONTEND_URL}/login"
FRONTEND_SUCCESS_URL = f"{FRONTEND_URL}/auth-success"

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login")
async def login(request: Request):
    """Redirect to Google Login"""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=failed_to_get_user_info")
        
        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')
        
        if not email or not google_id:
            return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=invalid_user_data_from_google")

        try:
            access_token = AuthService.login_with_google(
                db,
                email=email,
                name=name,
                google_id=google_id,
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token"),
                expires_at=token.get("expires_at"),
            )
        except InactiveAccountError:
            return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=account_inactive")

        # Redirect back to frontend with token in URL fragment (never sent to servers/logs)
        encoded_token = urllib.parse.quote(access_token, safe=".-_")
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}#access_token={encoded_token}")

    except Exception:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=auth_failed")
