from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User
from app.core.security import SecurityService

class AuthService:
    """Centralized authentication business logic"""

    @staticmethod
    def register(email: str, password: str, name: str, db: Session) -> User:
        # Check if user already exists 
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = SecurityService.hash_password(password)
        user = User(email=email, name=name, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(email: str, password: str, db: Session) -> tuple[User, str]:
        # Check if user exists , This is like : select * from users where email = email limit 1
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
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
        return user, access_token

    @staticmethod
    def get_user_by_token(token: str, db: Session) -> User:
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
        
        return user
