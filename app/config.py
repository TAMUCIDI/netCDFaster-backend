import os
from datetime import timedelta
from dotenv import load_dotenv

from pathlib import Path
import redis

load_dotenv(dotenv_path=".env")
class Config:
    UPLOAD_FOLDER = Path(f"{os.getcwd()}/{os.getenv('UPLOAD_FOLDER')}").resolve()
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'netcdf:'
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'netcdf_session'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_REDIS = redis.Redis.from_url(os.getenv("REDIS_URL"))

    @classmethod
    def init_app(cls, app):
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Initialize resource manager
        from .resource_manager import resource_manager
        resource_manager.start_cleanup_service(cls.UPLOAD_FOLDER)

