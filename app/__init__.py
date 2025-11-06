# public modules
from pathlib import Path
import redis
import logging
import sys

# flask modules
from flask import Flask
from flask_cors import CORS
from flask_session import Session

# local modules
from .config import Config
from .file import file_bp
from .utils import error_response, APIError

def setup_logging(app):
    """Configure logging for the application"""
    # Remove default Flask logger handlers
    app.logger.handlers.clear()

    # Set root logger level based on environment
    if Config.FLASK_ENV == 'production':
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create console handler that outputs to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # Configure specific loggers
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)

    # Ensure fileProcess logger is configured
    fileprocess_logger = logging.getLogger('app.file.fileProcess')
    fileprocess_logger.setLevel(log_level)

    # Suppress overly verbose third-party loggers
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('redis').setLevel(logging.WARNING)

    app.logger.info(f"Logging configured for {Config.FLASK_ENV} environment (level: {logging.getLevelName(log_level)})")

def create_app():
    app = Flask(__name__)
    # load config
    app.config.from_object(Config)

    # Setup logging first, before any other operations
    setup_logging(app)

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

    # Debug endpoint for session diagnostics
    @app.route('/debug/session', methods=['GET'])
    def debug_session():
        """Debug endpoint to inspect current session state"""
        from flask import request as flask_request, session as flask_session
        return {
            "session_id": flask_session.sid,
            "session_data": {key: str(value)[:100] for key, value in flask_session.items()},  # Truncate large values
            "session_keys": list(flask_session.keys()),
            "cookies_received": dict(flask_request.cookies),
            "flask_env": Config.FLASK_ENV,
            "url_prefix": Config.URL_PREFIX
        }, 200

    # Register module blueprints with URL prefix from config
    # URL_PREFIX is the application-level prefix (e.g., /netcdfaster-backend)
    # file_bp routes start from /file (e.g., /upload, /detail, etc.)
    # Combined route: URL_PREFIX/file/upload
    url_prefix = Config.URL_PREFIX + '/file'
    app.register_blueprint(file_bp, url_prefix=url_prefix)

    return app