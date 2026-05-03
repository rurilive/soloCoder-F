from typing import List, Dict, Any
from pydantic import BaseModel


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class AdminLogListResponse(BaseModel):
    logs: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
