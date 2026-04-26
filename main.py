import asyncio
import os
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Cookie, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from pydantic import BaseModel

from app.database import Base
from app.routers import canvas_router, auth_router
from app import crud
from app.routers.auth import SESSIONS, get_current_user

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
DB_PATH = BASE_DIR / "canvas.db"
INDEX_HTML = TEMPLATE_DIR / "index.html"
ROOM_HTML = TEMPLATE_DIR / "room.html"
AUTH_HTML = TEMPLATE_DIR / "auth.html"

active_connections: Dict[str, Set[WebSocket]] = {}
room_last_activity: Dict[str, datetime] = {}

room_html_cache = None
canvas_html_cache = None
auth_html_cache = None

CLEANUP_INTERVAL = 30
INACTIVE_TIMEOUT = 60


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.async_session() as session:
        yield session


async def cleanup_inactive_rooms(app: FastAPI):
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        
        now = datetime.now()
        rooms_to_remove = []
        
        for room_id, last_active in room_last_activity.items():
            if room_id == "default":
                continue
            if room_id in active_connections and len(active_connections[room_id]) > 0:
                continue
            if (now - last_active).total_seconds() >= INACTIVE_TIMEOUT:
                rooms_to_remove.append(room_id)
        
        for room_id in rooms_to_remove:
            async with app.state.async_session() as session:
                await crud.delete_canvas(session, room_id)
            if room_id in room_last_activity:
                del room_last_activity[room_id]
            print(f"[CLEANUP] 删除不活跃画板: {room_id}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global room_html_cache, canvas_html_cache, auth_html_cache
    room_html_cache = ROOM_HTML.read_text(encoding="utf-8")
    canvas_html_cache = INDEX_HTML.read_text(encoding="utf-8")
    auth_html_cache = AUTH_HTML.read_text(encoding="utf-8")
    
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    cleanup_task = asyncio.create_task(cleanup_inactive_rooms(app))
    
    yield
    
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Collaborative Canvas", lifespan=lifespan)

app.include_router(canvas_router, prefix="/api/canvas")
app.include_router(auth_router)


class RoomInfo(BaseModel):
    id: str
    users: int
    is_private: bool
    owner: Optional[str]


class UserInfo(BaseModel):
    id: int
    username: str
    user_type: str


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return HTMLResponse(content=room_html_cache)


@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return HTMLResponse(content=auth_html_cache)


@app.get("/canvas/{room_id}", response_class=HTMLResponse)
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


@app.get("/api/user/info", response_model=Optional[UserInfo])
async def get_user_info(
    request: Request,
    user = Depends(get_current_user)
):
    if user:
        return UserInfo(id=user.id, username=user.username, user_type=user.user_type)
    return None


@app.get("/api/user/canvases")
async def get_user_canvases(
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user:
        return []
    canvases = await crud.get_user_canvases(db, user.id)
    return [c.to_dict() for c in canvases]


@app.post("/api/canvas/{room_id}/create")
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


@app.get("/api/rooms", response_model=List[RoomInfo])
async def get_active_rooms(
    request: Request,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    from sqlalchemy import select as sa_select
    from app.models import Canvas
    
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


class CanvasCheckResult(BaseModel):
    exists: bool
    can_create: bool
    can_access: bool
    is_private: Optional[bool] = None
    owner: Optional[str] = None
    reason: Optional[str] = None


@app.get("/api/canvas/{room_id}/check", response_model=CanvasCheckResult)
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


@app.websocket("/ws/{canvas_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    canvas_id: str,
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    user = None
    if session_id and session_id in SESSIONS:
        user_id = SESSIONS[session_id]
        user = await crud.get_user_by_id(db, user_id)
    
    if canvas_id != "default" and not user:
        await websocket.close(code=1008)
        return
    
    canvas = await crud.get_canvas(db, canvas_id)
    if not canvas:
        if canvas_id == "default":
            canvas = await crud.create_canvas(db, canvas_id, owner_id=None, is_private=False)
        elif user:
            user_canvas_count = await crud.get_user_canvas_count(db, user.id)
            if user.user_type != "vip" and user_canvas_count >= 2:
                await websocket.close(code=1008)
                return
            canvas = await crud.create_canvas(db, canvas_id, owner_id=user.id, is_private=False)
    
    if canvas and canvas.is_private:
        if not user or (canvas.owner_id != user.id and user.user_type != "vip"):
            await websocket.close(code=1008)
            return
    
    await websocket.accept()
    
    if canvas_id not in active_connections:
        active_connections[canvas_id] = set()
    active_connections[canvas_id].add(websocket)
    room_last_activity[canvas_id] = datetime.now()
    
    try:
        while True:
            data = await websocket.receive_json()
            room_last_activity[canvas_id] = datetime.now()
            
            for connection in active_connections[canvas_id]:
                if connection != websocket:
                    await connection.send_json(data)
    except WebSocketDisconnect:
        active_connections[canvas_id].remove(websocket)
        if not active_connections[canvas_id]:
            del active_connections[canvas_id]
        room_last_activity[canvas_id] = datetime.now()


def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


if __name__ == "__main__":
    import uvicorn
    port = get_free_port()
    print(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
