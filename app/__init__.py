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
from .utils import error_response, APIError

def create_app():
    app = Flask(__name__)
    # load config
    app.config.from_object(Config)

    # Configure CORS with environment-based origins
    CORS(
        app,
        supports_credentials=True,
        origins=Config.CORS_ORIGINS,
        methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"]
    )

    Session(app)

    # Initialize configuration
    Config.init_app(app)

    # register error handlers
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return error_response(error, error.status_code)

    @app.errorhandler(404)
    def handle_not_found(error):
        return error_response(APIError("Resource not found"), 404)

    @app.errorhandler(500)
    def handle_internal_error(error):
        return error_response(APIError("Internal server error"), 500)

    # Health check endpoint for Kubernetes and container orchestration
    @app.route('/health', methods=['GET'])
    def health_check():
        try:
            # Check Redis connectivity
            if hasattr(app.config, 'SESSION_REDIS'):
                app.config['SESSION_REDIS'].ping()
            return {"status": "healthy", "service": "netcdf-backend"}, 200
        except Exception as e:
            return {"status": "unhealthy", "service": "netcdf-backend", "error": str(e)}, 503

    # Register module blueprints with URL prefix from config
    # URL_PREFIX is the application-level prefix (e.g., /netcdfaster-backend)
    # file_bp routes start from /file (e.g., /upload, /detail, etc.)
    # Combined route: URL_PREFIX/file/upload
    url_prefix = Config.URL_PREFIX + '/file'
    app.register_blueprint(file_bp, url_prefix=url_prefix)

    return app