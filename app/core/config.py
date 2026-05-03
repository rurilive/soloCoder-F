import os
from pathlib import Path
from typing import Optional


class Settings:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TEMPLATE_DIR: Path = BASE_DIR / "app" / "templates"
    DB_PATH: Path = BASE_DIR / "canvas.db"
    
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    
    CLEANUP_INTERVAL: int = 60
    INACTIVE_TIMEOUT: int = 300
    
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"


settings = Settings()
