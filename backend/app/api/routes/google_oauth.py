from fastapi import APIRouter, Depends, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import get_settings
from app.services.auth import AuthService
from app.core.security import SecurityService
from app.db.models import User, OAuthAccount
from starlette.responses import RedirectResponse

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
        
        # 1. Check if user already has this Google account linked
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_id
        ).first()
        
        if oauth_account:
            user = oauth_account.user
            # Update tokens
            oauth_account.access_token = token.get('access_token')
            oauth_account.refresh_token = token.get('refresh_token', oauth_account.refresh_token)
            oauth_account.expires_at = token.get('expires_at')
        else:
            # 2. Check if user exists by email
            user = db.query(User).filter(User.email == email).first()
            if not user:
                # Create new user with default Free plan (id=1)
                user = User(
                    email=email,
                    name=name or email.split('@')[0],
                    hashed_password=None,  # OAuth user — no password
                    plan_id=1 
                )
                db.add(user)
                db.flush()  # Get user.id without committing yet
            
            # Link Google account
            new_oauth = OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_user_id=google_id,
                access_token=token.get('access_token'),
                refresh_token=token.get('refresh_token'),
                expires_at=token.get('expires_at')
            )
            db.add(new_oauth)
        
        db.commit()
        
        # 3. Create app session token (JWT)
        access_token = SecurityService.create_access_token(user.email)
        
        # Redirect back to frontend with token
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?token={access_token}")

    except Exception as e:
        print(f"Google OAuth error: {e}")
        import traceback
        traceback.print_exc()
        # Redirect back to login with error details
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=auth_failed&details={error_msg}")
