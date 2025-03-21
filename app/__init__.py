# public modules
from pathlib import Path
import redis

# flask modules
from flask import Flask
from flask_cors import CORS
from flask_session import Session

# local modules
from .config import Config
from .file import file_bp

def create_app():
    app = Flask(__name__)
    # load config
    app.config.from_object(Config)

    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://0.0.0.0/3000"
        ],  # 生产环境应指定具体域名
        methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"]
    )

    Session(app)

    # register module blueprints
    app.register_blueprint(file_bp)

    return app