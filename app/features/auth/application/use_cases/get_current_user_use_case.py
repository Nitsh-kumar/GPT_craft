from fastapi import HTTPException, status
from app.features.auth.infrastructure.repositories.user_repository import UserRepository
from app.core.security import SecurityService
from app.features.auth.domain.entities import User


class GetCurrentUserUseCase:
    """Use case for getting current authenticated user"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, token: str) -> User:
        """
        Get current user from token
        
        Raises:
            HTTPException: If token is invalid or user not found
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # Verify and extract email from token
        email = SecurityService.verify_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        # Get user by email
        user = self.user_repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user
