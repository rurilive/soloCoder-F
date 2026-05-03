from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class RoomInfo(BaseModel):
    id: str
    users: int
    is_private: bool
    owner: Optional[str]


class CanvasCheckResult(BaseModel):
    exists: bool
    can_create: bool
    can_access: bool
    is_private: Optional[bool] = None
    owner: Optional[str] = None
    reason: Optional[str] = None


class ActionCreate(BaseModel):
    canvas_id: str
    action_type: str
    action_data: Dict[str, Any]


class ActionResponse(BaseModel):
    id: int
    canvas_id: str
    action_type: str
    action_data: Dict[str, Any]
    sequence: int
    
    model_config = ConfigDict(from_attributes=True)
