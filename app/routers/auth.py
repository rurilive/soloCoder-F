import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app import crud
from app.models import User

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"

SESSIONS: dict[str, int] = {}


def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return get_password_hash(password) == password_hash


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.async_session() as session:
        yield session


async def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not session_id or session_id not in SESSIONS:
        return None
    user_id = SESSIONS[session_id]
    user = await crud.get_user_by_id(db, user_id)
    if user and user.is_banned:
        if session_id in SESSIONS:
            del SESSIONS[session_id]
        return None
    return user


class UserResponse(BaseModel):
    id: int
    username: str
    user_type: str

    class Config:
        from_attributes = True


@router.get("/api/me", response_model=Optional[UserResponse])
async def get_me(user: Optional[User] = Depends(get_current_user)):
    if user:
        return UserResponse(id=user.id, username=user.username, user_type=user.user_type)
    return None


@router.post("/api/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(default="normal"),
    db: AsyncSession = Depends(get_db)
):
    existing_user = await crud.get_user_by_username(db, username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    password_hash = get_password_hash(password)
    user = await crud.create_user(db, username, password_hash, user_type)
    
    import uuid
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = user.id
    
    response = JSONResponse(
        content={"success": True, "user": {"id": user.id, "username": user.username, "user_type": user.user_type}}
    )
    response.set_cookie(
        key="session_id", 
        value=session_id, 
        httponly=True,
        samesite="lax"
    )
    return response


@router.post("/api/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user = await crud.get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    import uuid
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = user.id
    
    response = JSONResponse(
        content={"success": True, "user": {"id": user.id, "username": user.username, "user_type": user.user_type}}
    )
    response.set_cookie(
        key="session_id", 
        value=session_id, 
        httponly=True,
        samesite="lax"
    )
    return response


@router.post("/api/logout")
async def logout(
    session_id: Optional[str] = Cookie(None)
):
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
    
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_id")
    return response
