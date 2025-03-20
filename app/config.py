from pathlib import Path
import redis
class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TMP_DIR = BASE_DIR / "tmp"
    SECRET_KEY = '123456'
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    SESSION_REDIS = redis.Redis(
        host='redis-15722.c244.us-east-1-2.ec2.redns.redis-cloud.com',
        port=15722,
        password='iE3DH0q7yjFAK4iLhCYiZHxuuWb0Z7tU'
    )

