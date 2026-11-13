import json
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from app.db.models import Conversation, Message, AgentApproval

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

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True

    @staticmethod
    def create_or_update_approval(
        db: Session,
        action_id: str,
        conversation_id: int,
        user_id: int,
        tool_name: str,
        tier: int,
        parameters: Any,
        rationale: str,
        diff: Optional[str] = None,
    ) -> AgentApproval:
        params_str = json.dumps(parameters) if isinstance(parameters, (dict, list)) else str(parameters)
        approval = db.query(AgentApproval).filter(AgentApproval.id == action_id).first()
        if not approval:
            approval = AgentApproval(
                id=action_id,
                conversation_id=conversation_id,
                user_id=user_id,
                tool_name=tool_name,
                tier=tier,
                parameters=params_str,
                rationale=rationale,
                diff=diff,
                status="pending",
            )
            db.add(approval)
        else:
            approval.conversation_id = conversation_id
            approval.user_id = user_id
            approval.tool_name = tool_name
            approval.tier = tier
            approval.parameters = params_str
            approval.rationale = rationale
            approval.diff = diff
            approval.status = "pending"
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def get_pending_approval(db: Session, conversation_id: int, user_id: int) -> Optional[AgentApproval]:
        return db.query(AgentApproval).filter(
            AgentApproval.conversation_id == conversation_id,
            AgentApproval.user_id == user_id,
            AgentApproval.status == "pending",
        ).order_by(AgentApproval.created_at.desc()).first()

    @staticmethod
    def get_approval_by_id(db: Session, action_id: str, user_id: Optional[int] = None) -> Optional[AgentApproval]:
        query = db.query(AgentApproval).filter(AgentApproval.id == action_id)
        if user_id is not None:
            query = query.filter(AgentApproval.user_id == user_id)
        return query.first()

    @staticmethod
    def resolve_approval(
        db: Session,
        action_id: str,
        decision: str,
        feedback: Optional[str] = None,
    ) -> Optional[AgentApproval]:
        approval = db.query(AgentApproval).filter(AgentApproval.id == action_id).first()
        if not approval:
            return None
        approval.status = decision
        if feedback is not None:
            approval.user_feedback = feedback
        db.commit()
        db.refresh(approval)
        return approval

