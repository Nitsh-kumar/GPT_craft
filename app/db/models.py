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
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    plan_id = Column(Integer, ForeignKey("plans.id")  ,  nullable=False)
    plan = relationship("Plans", back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


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
