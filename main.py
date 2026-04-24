import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.routers import canvas_router

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
DB_PATH = BASE_DIR / "canvas.db"
INDEX_HTML = TEMPLATE_DIR / "index.html"

active_connections: Dict[str, Set[WebSocket]] = {}

html_cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global html_cache
    html_cache = INDEX_HTML.read_text(encoding="utf-8")
    
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield


app = FastAPI(title="Collaborative Canvas", lifespan=lifespan)

app.include_router(canvas_router, prefix="/api/canvas")


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return HTMLResponse(content=html_cache)


@app.websocket("/ws/{canvas_id}")
async def websocket_endpoint(websocket: WebSocket, canvas_id: str):
    await websocket.accept()
    
    if canvas_id not in active_connections:
        active_connections[canvas_id] = set()
    active_connections[canvas_id].add(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            for connection in active_connections[canvas_id]:
                if connection != websocket:
                    await connection.send_json(data)
    except WebSocketDisconnect:
        active_connections[canvas_id].remove(websocket)
        if not active_connections[canvas_id]:
            del active_connections[canvas_id]


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
