import os
from datetime import timedelta
from dotenv import load_dotenv

from pathlib import Path
import redis

load_dotenv(dotenv_path=".env")


class Config:
    """Base configuration for production and development"""

    # Flask environment
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = FLASK_ENV == "development"

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set. This is required for production.")

    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]

    # Upload folder
    UPLOAD_FOLDER = Path(f"{os.getcwd()}/{os.getenv('UPLOAD_FOLDER', 'uploads')}").resolve()

    # URL prefix for the application
    URL_PREFIX = os.getenv("URL_PREFIX", "/netcdfaster-backend")
    # Validate URL_PREFIX format
    if URL_PREFIX and not URL_PREFIX.startswith("/"):
        raise ValueError("URL_PREFIX must start with '/', got: " + URL_PREFIX)

    # Session configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'netcdf:'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'netcdf_session'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Session cookie security based on environment
    if FLASK_ENV == "production":
        SESSION_COOKIE_SAMESITE = "Strict"
        SESSION_COOKIE_SECURE = True
    else:
        SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
        SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"

    # Redis configuration
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        raise ValueError("REDIS_URL environment variable is not set. This is required for session management.")
    SESSION_REDIS = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    @classmethod
    def init_app(cls, app):
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        # Initialize resource manager
        from .resource_manager import resource_manager
        resource_manager.start_cleanup_service(cls.UPLOAD_FOLDER)

