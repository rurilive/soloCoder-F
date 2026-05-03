from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Form, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models import User
from app.core.dependencies import get_db, get_current_user
from app.core.security import (
    get_password_hash,
    verify_password,
    create_session,
    delete_session,
)
from app.schemas.user import UserResponse

router = APIRouter()


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
    
    session_id = create_session(user.id)
    
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
    
    session_id = create_session(user.id)
    
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
    delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_id")
    return response
