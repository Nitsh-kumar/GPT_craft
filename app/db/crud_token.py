from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import UserDailyLimit

class TokenUsageCRUD:
    @staticmethod
    def get_user_limit(db: Session, user_id: int) -> Optional[UserDailyLimit]:
        return db.query(UserDailyLimit).filter(UserDailyLimit.user_id == user_id).first()

    @staticmethod
    def create_user_limit(db: Session, user_id: int, initial_limit: int = 5000) -> UserDailyLimit:
        user_limit = UserDailyLimit(user_id=user_id, daily_limit=initial_limit)
        db.add(user_limit)
        db.commit()
        db.refresh(user_limit)
        return user_limit

    @staticmethod
    def deduct_tokens(db: Session, user_id: int, tokens_used: int) -> UserDailyLimit:
        user_limit = TokenUsageCRUD.get_user_limit(db, user_id)
        if not user_limit:
            user_limit = TokenUsageCRUD.create_user_limit(db, user_id)
        
        user_limit.daily_limit = max(0, user_limit.daily_limit - tokens_used)
        db.commit()
        db.refresh(user_limit)
        return user_limit
