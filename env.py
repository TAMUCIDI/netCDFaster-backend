from environs import Env
from pathlib import Path

env = Env()
env.read_env()

# Path: .env
BASE_DIR = env("BASE_DIR", Path(__file__).resolve().parent)
TMP_DIR = env("TMP_DIR", BASE_DIR / "tmp")