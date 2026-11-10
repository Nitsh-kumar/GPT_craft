from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Conversation, Message

class ChatCRUD:
    @staticmethod
    def create_conversation(db: Session, user_id: int, title: str) -> Conversation:
        db_conv = Conversation(user_id=user_id, title=title)
        db.add(db_conv)
        db.commit()
        db.refresh(db_conv)
        return db_conv

    @staticmethod
    def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_conversations_for_user(db: Session, user_id: int) -> List[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.created_at.desc()).all()

    @staticmethod
    def add_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
        db_msg = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(db_msg)
        db.commit()
        db.refresh(db_msg)
        return db_msg

    @staticmethod
    def get_messages_for_conversation(db: Session, conversation_id: int) -> List[Message]:
        return db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
