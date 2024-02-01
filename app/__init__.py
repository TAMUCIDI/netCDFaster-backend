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
        supports_credentials=True)

    session = Session()
    session.init_app(app)

    # register module blueprints
    app.register_blueprint(file_bp)

    return app