import os
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
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE")
    SESSION_COOKIE_SECURE = False
    SESSION_REDIS = redis.Redis.from_url("redis://default:iE3DH0q7yjFAK4iLhCYiZHxuuWb0Z7tU@redis-15722.c244.us-east-1-2.ec2.redns.redis-cloud.com:15722")

    @classmethod
    def init_app(cls, app):
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

