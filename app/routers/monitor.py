from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User, MonitorRecord
from app.models.monitor import MonitorEventType
from app.models.user import UserRole
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/monitor", tags=["监控"])


class MonitorEventCreate(BaseModel):
    exam_id: int
    event_type: str
    event_detail: Optional[str] = None


class MonitorEventResponse(BaseModel):
    id: int
    exam_id: int
    user_id: int
    event_type: str
    event_detail: Optional[str]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]

    class Config:
        from_attributes = True


@router.post("/event")
def record_event(
    event_data: MonitorEventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    new_record = MonitorRecord(
        exam_id=event_data.exam_id,
        user_id=current_user.id,
        event_type=event_data.event_type,
        event_detail=event_data.event_detail,
        timestamp=datetime.utcnow(),
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    db.add(new_record)
    db.commit()
    
    return {"message": "事件记录成功"}


@router.get("/exam/{exam_id}", response_model=List[MonitorEventResponse])
def get_exam_monitor_records(
    exam_id: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    query = db.query(MonitorRecord).filter(MonitorRecord.exam_id == exam_id)
    
    if user_id:
        query = query.filter(MonitorRecord.user_id == user_id)
    
    records = query.order_by(MonitorRecord.timestamp.desc()).all()
    return records


@router.get("/exam/{exam_id}/summary")
def get_exam_monitor_summary(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    records = db.query(MonitorRecord).filter(
        MonitorRecord.exam_id == exam_id
    ).all()
    
    user_events = {}
    event_types = {}
    
    for record in records:
        if record.user_id not in user_events:
            user_events[record.user_id] = 0
        user_events[record.user_id] += 1
        
        if record.event_type not in event_types:
            event_types[record.event_type] = 0
        event_types[record.event_type] += 1
    
    suspicious_users = []
    for user_id, count in user_events.items():
        if count > 5:
            user = db.query(User).filter(User.id == user_id).first()
            suspicious_users.append({
                "user_id": user_id,
                "username": user.username if user else None,
                "real_name": user.real_name if user else None,
                "event_count": count
            })
    
    return {
        "exam_id": exam_id,
        "total_events": len(records),
        "total_users": len(user_events),
        "event_type_summary": event_types,
        "suspicious_users": suspicious_users
    }


@router.get("/user/{user_id}/exam/{exam_id}", response_model=List[MonitorEventResponse])
def get_user_exam_monitor_records(
    user_id: int,
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    records = db.query(MonitorRecord).filter(
        MonitorRecord.exam_id == exam_id,
        MonitorRecord.user_id == user_id
    ).order_by(MonitorRecord.timestamp).all()
    
    return records
