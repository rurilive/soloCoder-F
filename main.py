import asyncio
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Cookie
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.routers import canvas_router, auth_router, admin_router, pages_router
from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, SESSIONS
from app.core.state import active_connections, room_last_activity
from app.routers.pages import load_templates


async def cleanup_inactive_rooms(app: FastAPI):
    while True:
        await asyncio.sleep(settings.CLEANUP_INTERVAL)
        
        async with app.state.async_session() as session:
            inactive_canvases = await crud.get_inactive_canvases(session, settings.INACTIVE_TIMEOUT)
            
            rooms_to_remove = []
            for canvas in inactive_canvases:
                room_id = canvas.canvas_id
                
                if room_id == "default":
                    continue
                
                if room_id in active_connections and len(active_connections[room_id]) > 0:
                    continue
                
                rooms_to_remove.append(room_id)
            
            for room_id in rooms_to_remove:
                await crud.delete_canvas(session, room_id)
                if room_id in room_last_activity:
                    del room_last_activity[room_id]
                print(f"[CLEANUP] 删除不活跃画板: {room_id}")


async def migrate_database(engine):
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        
        if "is_banned" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0"))
            print("[MIGRATION] Added is_banned column to users table")
        
        if "banned_reason" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN banned_reason VARCHAR(256)"))
            print("[MIGRATION] Added banned_reason column to users table")
        
        if "banned_at" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN banned_at DATETIME"))
            print("[MIGRATION] Added banned_at column to users table")
        
        await conn.commit()


async def init_default_admin(engine):
    async with async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)() as session:
        admin_user = await crud.get_user_by_username(session, settings.DEFAULT_ADMIN_USERNAME)
        
        if not admin_user:
            password_hash = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            admin_user = await crud.create_user(
                session,
                username=settings.DEFAULT_ADMIN_USERNAME,
                password_hash=password_hash,
                user_type="admin"
            )
            print(f"[INIT] Created default admin user: {settings.DEFAULT_ADMIN_USERNAME} / {settings.DEFAULT_ADMIN_PASSWORD}")
        else:
            if admin_user.user_type != "admin":
                await crud.update_user_type(session, admin_user.id, "admin")
                print("[INIT] Updated admin user to admin type")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_templates()
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await migrate_database(engine)
    await init_default_admin(engine)
    
    app.state.async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    cleanup_task = asyncio.create_task(cleanup_inactive_rooms(app))
    
    yield
    
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Collaborative Canvas", lifespan=lifespan)

app.include_router(pages_router)
app.include_router(canvas_router, prefix="/api/canvas")
app.include_router(auth_router)
app.include_router(admin_router)


@app.websocket("/ws/{canvas_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    canvas_id: str,
    session_id: Optional[str] = Cookie(None)
):
    user = None
    
    async with websocket.app.state.async_session() as db:
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
        
        await crud.update_canvas_activity(db, canvas_id)
    
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
        
        async with websocket.app.state.async_session() as db:
            await crud.update_canvas_activity(db, canvas_id)
        
        room_last_activity[canvas_id] = datetime.now()


def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


if __name__ == "__main__":
    import uvicorn
    port = 6555
    print(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
