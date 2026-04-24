from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class MonitorEventType(str, enum.Enum):
    WINDOW_BLUR = "window_blur"
    WINDOW_FOCUS = "window_focus"
    VISIBILITY_HIDDEN = "visibility_hidden"
    VISIBILITY_VISIBLE = "visibility_visible"
    FULLSCREEN_ENTER = "fullscreen_enter"
    FULLSCREEN_EXIT = "fullscreen_exit"
    COPY_DETECTED = "copy_detected"
    PASTE_DETECTED = "paste_detected"
    TAB_SWITCH = "tab_switch"
    MOUSE_LEAVE = "mouse_leave"


class MonitorRecord(Base):
    __tablename__ = "monitor_records"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    event_type = Column(String(50), nullable=False)
    event_detail = Column(String(500))
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="monitor_records")

    def __repr__(self):
        return f"<MonitorRecord {self.id} - {self.event_type}>"
