from app.routers.auth import router as auth_router
from app.routers.questions import router as questions_router
from app.routers.exams import router as exams_router
from app.routers.users import router as users_router
from app.routers.monitor import router as monitor_router

__all__ = [
    "auth_router",
    "questions_router", 
    "exams_router",
    "users_router",
    "monitor_router"
]
