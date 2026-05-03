from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select as sa_select

from app import crud
from app.models import User, Canvas
from app.core.dependencies import get_db, get_current_user, get_current_admin
from app.core.config import settings
from app.schemas.canvas import RoomInfo, CanvasCheckResult
from app.schemas.user import UserInfo

router = APIRouter()

room_html_cache: Optional[str] = None
canvas_html_cache: Optional[str] = None
auth_html_cache: Optional[str] = None
admin_html_cache: Optional[str] = None


def load_templates():
    global room_html_cache, canvas_html_cache, auth_html_cache, admin_html_cache
    room_html_cache = (settings.TEMPLATE_DIR / "room.html").read_text(encoding="utf-8")
    canvas_html_cache = (settings.TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    auth_html_cache = (settings.TEMPLATE_DIR / "auth.html").read_text(encoding="utf-8")
    admin_html = settings.TEMPLATE_DIR / "admin.html"
    admin_html_cache = admin_html.read_text(encoding="utf-8") if admin_html.exists() else ""


@router.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return HTMLResponse(content=room_html_cache)


@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return HTMLResponse(content=auth_html_cache)


@router.get("/admin", response_class=HTMLResponse)
async def get_admin_page(
    request: Request,
    user = Depends(get_current_admin)
):
    if not user or user.user_type != "admin":
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=admin_html_cache)


@router.get("/canvas/{room_id}", response_class=HTMLResponse)
async def get_canvas(
    room_id: str,
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    canvas = await crud.get_canvas(db, room_id)
    
    if room_id == "default":
        if not canvas:
            await crud.create_canvas(db, room_id, owner_id=None, is_private=False)
        return HTMLResponse(content=canvas_html_cache)
    
    if not user:
        raise HTTPException(status_code=403, detail="请先登录以使用其他画板")
    
    if not canvas:
        user_canvas_count = await crud.get_user_canvas_count(db, user.id)
        if user.user_type != "vip" and user_canvas_count >= 2:
            raise HTTPException(status_code=403, detail="普通用户最多只能保留2个画板")
        canvas = await crud.create_canvas(db, room_id, owner_id=user.id, is_private=False)
    else:
        if canvas.is_private and canvas.owner_id != user.id and user.user_type != "vip":
            raise HTTPException(status_code=403, detail="这是私密画板，仅创建者可访问")
    
    return HTMLResponse(content=canvas_html_cache)


@router.get("/api/user/info", response_model=Optional[UserInfo])
async def get_user_info(
    request: Request,
    user = Depends(get_current_user)
):
    if user:
        return UserInfo(id=user.id, username=user.username, user_type=user.user_type)
    return None


@router.get("/api/user/canvases")
async def get_user_canvases(
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user:
        return []
    canvases = await crud.get_user_canvases(db, user.id)
    return [c.to_dict() for c in canvases]


@router.post("/api/canvas/{room_id}/create")
async def create_canvas(
    room_id: str,
    request: Request,
    is_private: bool = False,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    if room_id == "default":
        raise HTTPException(status_code=400, detail="不能使用default作为自定义画板名")
    
    existing = await crud.get_canvas(db, room_id)
    if existing:
        raise HTTPException(status_code=400, detail="该画板已存在")
    
    user_canvas_count = await crud.get_user_canvas_count(db, user.id)
    if user.user_type != "vip" and user_canvas_count >= 2:
        raise HTTPException(status_code=403, detail="普通用户最多只能保留2个画板")
    
    if is_private and user.user_type != "vip":
        raise HTTPException(status_code=403, detail="仅VIP用户可以创建私密画板")
    
    canvas = await crud.create_canvas(db, room_id, owner_id=user.id, is_private=is_private)
    return {"success": True, "canvas": canvas.to_dict()}


@router.get("/api/rooms", response_model=List[RoomInfo])
async def get_active_rooms(
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.core.state import active_connections
    
    rooms = []
    
    default_canvas = await crud.get_canvas(db, "default")
    if not default_canvas:
        await crud.create_canvas(db, "default", owner_id=None, is_private=False)
    
    rooms.append(RoomInfo(
        id="default",
        users=len(active_connections.get("default", set())),
        is_private=False,
        owner=None
    ))
    
    query = sa_select(Canvas).where(Canvas.canvas_id != "default")
    result = await db.execute(query)
    all_canvases = result.scalars().all()
    
    for canvas in all_canvases:
        if canvas.is_private:
            if not user:
                continue
            if canvas.owner_id != user.id and user.user_type != "vip":
                continue
        
        owner = None
        if canvas.owner_id:
            owner_user = await crud.get_user_by_id(db, canvas.owner_id)
            if owner_user:
                owner = owner_user.username
        
        rooms.append(RoomInfo(
            id=canvas.canvas_id,
            users=len(active_connections.get(canvas.canvas_id, set())),
            is_private=canvas.is_private,
            owner=owner
        ))
    
    return rooms


@router.get("/api/canvas/{room_id}/check", response_model=CanvasCheckResult)
async def check_canvas(
    room_id: str,
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if room_id == "default":
        return CanvasCheckResult(
            exists=True,
            can_create=True,
            can_access=True,
            is_private=False,
            owner=None
        )
    
    canvas = await crud.get_canvas(db, room_id)
    
    if canvas:
        if canvas.is_private:
            if not user:
                return CanvasCheckResult(
                    exists=True,
                    can_create=False,
                    can_access=False,
                    is_private=True,
                    owner=None,
                    reason="这是私密画板，请登录"
                )
            if canvas.owner_id != user.id and user.user_type != "vip":
                return CanvasCheckResult(
                    exists=True,
                    can_create=False,
                    can_access=False,
                    is_private=True,
                    owner=None,
                    reason="这是私密画板，仅创建者可访问"
                )
        
        owner = None
        if canvas.owner_id:
            owner_user = await crud.get_user_by_id(db, canvas.owner_id)
            if owner_user:
                owner = owner_user.username
        
        return CanvasCheckResult(
            exists=True,
            can_create=False,
            can_access=True,
            is_private=canvas.is_private,
            owner=owner
        )
    
    if not user:
        return CanvasCheckResult(
            exists=False,
            can_create=False,
            can_access=False,
            reason="请先登录以创建新画板"
        )
    
    user_canvas_count = await crud.get_user_canvas_count(db, user.id)
    if user.user_type != "vip" and user_canvas_count >= 2:
        return CanvasCheckResult(
            exists=False,
            can_create=False,
            can_access=False,
            reason="普通用户最多只能保留2个画板"
        )
    
    return CanvasCheckResult(
        exists=False,
        can_create=True,
        can_access=True
    )
