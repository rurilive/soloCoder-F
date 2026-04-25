from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer, func, ForeignKey, Boolean
from datetime import datetime
from app.database import Base
from enum import Enum


class UserType(str, Enum):
    GUEST = "guest"
    NORMAL = "normal"
    VIP = "vip"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    user_type: Mapped[str] = mapped_column(String(20), default=UserType.NORMAL)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "user_type": self.user_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Canvas(Base):
    __tablename__ = "canvases"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canvas_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "canvas_id": self.canvas_id,
            "owner_id": self.owner_id,
            "is_private": self.is_private,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None
        }


class CanvasAction(Base):
    __tablename__ = "canvas_actions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canvas_id: Mapped[str] = mapped_column(String(100), index=True)
    action_type: Mapped[str] = mapped_column(String(20))
    action_data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    
    def to_dict(self):
        return {
            "id": self.id,
            "canvas_id": self.canvas_id,
            "action_type": self.action_type,
            "action_data": self.action_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sequence": self.sequence
        }
