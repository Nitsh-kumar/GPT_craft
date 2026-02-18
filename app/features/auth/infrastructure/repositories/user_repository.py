from typing import Optional
from sqlalchemy.orm import Session
from app.features.auth.domain.entities import User
from app.features.auth.infrastructure.models import UserModel


class UserRepository:
    """Repository pattern for User data access"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, email: str, hashed_password: str) -> User:
        """Create a new user"""
        user_model = UserModel(email=email, hashed_password=hashed_password)
        self.db.add(user_model)
        self.db.commit()
        self.db.refresh(user_model)
        return self._model_to_entity(user_model)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        user_model = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._model_to_entity(user_model) if user_model else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._model_to_entity(user_model) if user_model else None

    def update(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user"""
        user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user_model:
            return None

        for key, value in kwargs.items():
            if hasattr(user_model, key):
                setattr(user_model, key, value)

        self.db.commit()
        self.db.refresh(user_model)
        return self._model_to_entity(user_model)

    @staticmethod
    def _model_to_entity(model: UserModel) -> User:
        """Convert SQLAlchemy model to domain entity"""
        if model is None:
            return None
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
