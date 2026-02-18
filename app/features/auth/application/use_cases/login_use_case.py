from fastapi import HTTPException, status
from app.features.auth.infrastructure.repositories.user_repository import UserRepository
from app.core.security import SecurityService
from app.features.auth.domain.entities import User


class LoginUseCase:
    """Use case for user login"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, email: str, password: str) -> tuple[User, str]:
        """
        Authenticate user and generate access token
        
        Returns:
            Tuple of (User entity, access token)
            
        Raises:
            HTTPException: If credentials are invalid or user is inactive
        """
        # Get user by email
        user = self.user_repository.get_by_email(email)
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

        # Create access token
        access_token = SecurityService.create_access_token(user.email)

        return user, access_token
