from fastapi import HTTPException, status
from app.features.auth.infrastructure.repositories.user_repository import UserRepository
from app.core.security import SecurityService
from app.features.auth.domain.entities import User


class RegisterUseCase:
    """Use case for user registration"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, email: str, password: str) -> User:
        """
        Register a new user
        
        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password and create user
        hashed_password = SecurityService.hash_password(password)
        user = self.user_repository.create(email, hashed_password)

        return user
