from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    TMP_DIR = BASE_DIR / "tmp"
    SESSION_SECRET_KEY = '123456'