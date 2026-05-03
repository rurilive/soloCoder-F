from typing import Optional
from fastapi import Depends, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SESSIONS, get_user_id_from_session
from app import crud
from app.models import User


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.async_session() as session:
        yield session


async def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    user_id = get_user_id_from_session(session_id)
    if not user_id:
        return None
    
    user = await crud.get_user_by_id(db, user_id)
    if user and user.is_banned:
        if session_id:
            from app.core.security import delete_session
            delete_session(session_id)
        return None
    
    return user


async def get_current_admin(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    user = await get_current_user(request, session_id, db)
    
    if user and user.user_type == "admin":
        return user
    return None


async def get_ip_address(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
