import json
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models import User

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.async_session() as session:
        yield session


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    from app.routers.auth import get_current_user
    user = await get_current_user(request, db=db)
    if user and user.user_type == "admin":
        return user
    return None


async def get_ip_address(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class UserListResponse(BaseModel):
    users: list
    total: int
    offset: int
    limit: int


class AdminLogListResponse(BaseModel):
    logs: list
    total: int
    offset: int
    limit: int


@router.get("/api/admin/users", response_model=UserListResponse)
async def get_users(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    admin: Optional[User] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    users = await crud.get_all_users(db, offset=offset, limit=limit)
    total = await crud.get_user_count(db)
    
    return UserListResponse(
        users=[user.to_dict() for user in users],
        total=total,
        offset=offset,
        limit=limit
    )


@router.post("/api/admin/users/{user_id}/vip")
async def set_user_vip(
    user_id: int,
    request: Request,
    is_vip: bool = Form(True),
    admin: Optional[User] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    ip_address: str = Depends(get_ip_address)
):
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    target_user = await crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    new_type = "vip" if is_vip else "normal"
    await crud.update_user_type(db, user_id, new_type)
    
    details = json.dumps({
        "from": target_user.user_type,
        "to": new_type,
        "username": target_user.username
    }, ensure_ascii=False)
    
    await crud.create_admin_log(
        db,
        admin_id=admin.id,
        action="set_vip" if is_vip else "remove_vip",
        target_user_id=user_id,
        details=details,
        ip_address=ip_address
    )
    
    return {"success": True, "message": f"已将用户 {target_user.username} 设置为VIP" if is_vip else f"已取消用户 {target_user.username} 的VIP"}


@router.post("/api/admin/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    request: Request,
    reason: str = Form(default=""),
    admin: Optional[User] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    ip_address: str = Depends(get_ip_address)
):
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    target_user = await crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await crud.ban_user(db, user_id, reason)
    
    details = json.dumps({
        "username": target_user.username,
        "reason": reason
    }, ensure_ascii=False)
    
    await crud.create_admin_log(
        db,
        admin_id=admin.id,
        action="ban_user",
        target_user_id=user_id,
        details=details,
        ip_address=ip_address
    )
    
    return {"success": True, "message": f"已封禁用户 {target_user.username}"}


@router.post("/api/admin/users/{user_id}/unban")
async def unban_user(
    user_id: int,
    request: Request,
    admin: Optional[User] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    ip_address: str = Depends(get_ip_address)
):
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    target_user = await crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await crud.unban_user(db, user_id)
    
    details = json.dumps({
        "username": target_user.username
    }, ensure_ascii=False)
    
    await crud.create_admin_log(
        db,
        admin_id=admin.id,
        action="unban_user",
        target_user_id=user_id,
        details=details,
        ip_address=ip_address
    )
    
    return {"success": True, "message": f"已解封用户 {target_user.username}"}


@router.get("/api/admin/logs", response_model=AdminLogListResponse)
async def get_logs(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    admin: Optional[User] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    logs = await crud.get_admin_logs(db, offset=offset, limit=limit)
    total = await crud.get_admin_log_count(db)
    
    logs_with_admin_info = []
    for log in logs:
        log_dict = log.to_dict()
        admin_user = await crud.get_user_by_id(db, log.admin_id)
        log_dict["admin_username"] = admin_user.username if admin_user else None
        
        if log.target_user_id:
            target_user = await crud.get_user_by_id(db, log.target_user_id)
            log_dict["target_username"] = target_user.username if target_user else None
        
        logs_with_admin_info.append(log_dict)
    
    return AdminLogListResponse(
        logs=logs_with_admin_info,
        total=total,
        offset=offset,
        limit=limit
    )
