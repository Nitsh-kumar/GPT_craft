from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """User entity - domain model independent of frameworks"""
    email: str
    hashed_password: str
    id: int = None
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
