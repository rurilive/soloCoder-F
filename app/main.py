from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import User
from app.models.user import UserRole
from app.security import get_password_hash
from app.routers import auth_router, questions_router, exams_router, users_router, monitor_router


def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                real_name="管理员",
                role=UserRole.ADMIN
            )
            db.add(admin)
            db.commit()
            print(f"默认管理员账户已创建: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(questions_router)
app.include_router(exams_router)
app.include_router(users_router)
app.include_router(monitor_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/questions", response_class=HTMLResponse)
async def questions_page(request: Request):
    return templates.TemplateResponse("questions.html", {"request": request})


@app.get("/exams", response_class=HTMLResponse)
async def exams_page(request: Request):
    return templates.TemplateResponse("exams.html", {"request": request})


@app.get("/exam/{exam_id}", response_class=HTMLResponse)
async def exam_page(request: Request, exam_id: int):
    return templates.TemplateResponse("exam.html", {"request": request, "exam_id": exam_id})


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    return templates.TemplateResponse("results.html", {"request": request})


@app.get("/monitor/{exam_id}", response_class=HTMLResponse)
async def monitor_page(request: Request, exam_id: int):
    return templates.TemplateResponse("monitor.html", {"request": request, "exam_id": exam_id})


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
