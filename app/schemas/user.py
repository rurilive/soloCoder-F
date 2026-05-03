from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    user_type: str
    
    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):
    id: int
    username: str
    user_type: str
    
    model_config = ConfigDict(from_attributes=True)
