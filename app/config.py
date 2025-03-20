import os
from dotenv import load_dotenv

from pathlib import Path
import redis

load_dotenv(dotenv_path=".env")
class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TMP_DIR = BASE_DIR / "tmp"
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE")
    SESSION_COOKIE_SECURE = False
    SESSION_REDIS = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
    )

