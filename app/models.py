from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer, func
from datetime import datetime
from app.database import Base


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
