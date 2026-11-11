from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import UserPreferences, UserMemory


class MemoryCRUD:
    @staticmethod
    def get_or_create_preferences(db: Session, user_id: int) -> UserPreferences:
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        if not prefs:
            prefs = UserPreferences(
                user_id=user_id,
                custom_instructions_profile=None,
                custom_instructions_style=None,
                memory_enabled=True,
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        return prefs

    @staticmethod
    def update_preferences(
        db: Session,
        user_id: int,
        profile: Optional[str] = None,
        style: Optional[str] = None,
        memory_enabled: Optional[bool] = None,
    ) -> UserPreferences:
        prefs = MemoryCRUD.get_or_create_preferences(db, user_id)
        if profile is not None:
            prefs.custom_instructions_profile = profile
        if style is not None:
            prefs.custom_instructions_style = style
        if memory_enabled is not None:
            prefs.memory_enabled = memory_enabled

        db.commit()
        db.refresh(prefs)
        return prefs

    @staticmethod
    def get_user_memories(db: Session, user_id: int, active_only: bool = True) -> List[UserMemory]:
        query = db.query(UserMemory).filter(UserMemory.user_id == user_id)
        if active_only:
            query = query.filter(UserMemory.is_active == True)
        return query.order_by(UserMemory.created_at.desc()).all()

    @staticmethod
    def get_memory(db: Session, user_id: int, memory_id: int) -> Optional[UserMemory]:
        return db.query(UserMemory).filter(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id,
        ).first()

    @staticmethod
    def create_memory(
        db: Session,
        user_id: int,
        content: str,
        category: str = "general",
        conversation_id: Optional[int] = None,
    ) -> UserMemory:
        clean_content = content.strip()
        # Avoid exact duplicate active memories for the user
        existing = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.content == clean_content,
            UserMemory.is_active == True,
        ).first()
        if existing:
            return existing

        memory = UserMemory(
            user_id=user_id,
            category=category,
            content=clean_content,
            is_active=True,
            source_conversation_id=conversation_id,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def delete_memory(db: Session, user_id: int, memory_id: int) -> bool:
        memory = MemoryCRUD.get_memory(db, user_id, memory_id)
        if not memory:
            return False
        db.delete(memory)
        db.commit()
        return True

    @staticmethod
    def clear_all_memories(db: Session, user_id: int) -> int:
        deleted_count = db.query(UserMemory).filter(UserMemory.user_id == user_id).delete()
        db.commit()
        return deleted_count
