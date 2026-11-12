from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base




class Plans(Base):
    """Plans database model"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="plan")

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name})>"


class User(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth/Supabase users
    supabase_uid = Column(String, unique=True, index=True, nullable=True)  # Supabase auth.users UUID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    plan = relationship("Plans", back_populates="users")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class OAuthAccount(Base):
    """OAuth account database model for third-party providers like Google"""
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # e.g., 'google'
    provider_user_id = Column(String, unique=True, index=True, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(Integer, nullable=True)

    user = relationship("User", back_populates="oauth_accounts")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<OAuthAccount(provider='{self.provider}', user_id={self.user_id})>"


class UserDailyLimit(Base):
    """User daily limit database model"""
    __tablename__ = "user_daily_limit"

    id = Column(Integer, primary_key=True, index=True , autoincrement=True )
    user_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    daily_limit = Column(Integer, nullable=False)

    # created_at = Column(DateTime, server_default=func.now())
    # updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserDailyLimit(id={self.id}, user_id={self.user_id})>"


class Conversation(Base):
    """Conversation database model"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, default="New Conversation")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"


class Message(Base):
    """Message database model"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}')>"


class UserPreferences(Base):
    """User personalization and custom instructions model"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    custom_instructions_profile = Column(Text, nullable=True)  # What the AI should know about the user
    custom_instructions_style = Column(Text, nullable=True)    # How the AI should respond
    memory_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences(user_id={self.user_id}, memory_enabled={self.memory_enabled})>"


class UserMemory(Base):
    """Durable episodic memory fact stored for a user"""
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    category = Column(String, nullable=False, default="general")  # 'tech_stack', 'preference', 'project', 'general'
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="memories")
    source_conversation = relationship("Conversation")

    def __repr__(self):
        return f"<UserMemory(id={self.id}, user_id={self.user_id}, category='{self.category}')>"


class AgentApproval(Base):
    """Pending or resolved Human-In-The-Loop approval request for Tier 2/3 tools"""
    __tablename__ = "agent_approvals"

    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    tool_name = Column(String, nullable=False)
    tier = Column(Integer, default=2, nullable=False)
    parameters = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    diff = Column(Text, nullable=True)
    status = Column(String, default="pending", nullable=False)
    user_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", backref="approvals")
    user = relationship("User", backref="approvals")

    def __repr__(self):
        return f"<AgentApproval(id='{self.id}', tool='{self.tool_name}', status='{self.status}')>"
