from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date
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
    generation = relationship("GenerationDetails", back_populates="message", uselist=False,
                              cascade="all, delete-orphan")

    @property
    def model_used(self):
        return self.generation.model_used if self.generation else None

    @property
    def mode_used(self):
        return self.generation.mode_used if self.generation else None


    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}')>"


class DailyQuota(Base):
    """Durable UTC usage; independent of deletable conversation history."""
    __tablename__ = "daily_quotas"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    date = Column(Date, primary_key=True)
    tokens_remaining = Column(Integer, nullable=False)
    requests_used = Column(Integer, nullable=False, default=0)
    burst_window = Column(Integer, nullable=False, default=0)
    burst_count = Column(Integer, nullable=False, default=0)


class QuotaReservation(Base):
    __tablename__ = "quota_reservations"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    reserved_tokens = Column(Integer, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    unfunded_tokens = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="pending")
    expires_at = Column(Integer, nullable=False, index=True)


class GenerationDetails(Base):
    __tablename__ = "generation_details"
    message_id = Column(Integer, ForeignKey("messages.id"), primary_key=True)
    model_used = Column(String, nullable=False)
    mode_used = Column(String, nullable=False)
    message = relationship("Message", back_populates="generation")
