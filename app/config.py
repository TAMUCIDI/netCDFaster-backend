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
        host='redis-15719.c325.us-east-1-4.ec2.cloud.redislabs.com',
        port=15719,
        password='PMYtfgnI4RC6Q0UTGTy4yRdjA7K8nuiI'
    )

