from functools import wraps
from flask import jsonify, request
from marshmallow import ValidationError
import logging
import traceback

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API Exception"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


def error_response(error, status_code=400):
    """Standard error response format"""
    return jsonify({
        'error': error.__class__.__name__,
        'message': str(error),
        'status_code': status_code
    }), status_code


def success_response(data=None, message='Success'):
    """Standard success response format"""
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)


def validate_request(schema_class):
    """Decorator for request validation"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                schema = schema_class()
                
                if request.method == 'POST':
                    if request.content_type and 'multipart/form-data' in request.content_type:
                        # Handle file uploads
                        data = request.files.to_dict()
                        data.update(request.form.to_dict())
                    else:
                        data = request.get_json() or {}
                else:
                    data = request.args.to_dict()
                
                validated_data = schema.load(data)
                return f(validated_data, *args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Validation error: {e.messages}")
                return error_response(APIError(str(e.messages)), 400)
            except APIError as e:
                logger.error(f"API error: {e.message}")
                return error_response(e, e.status_code)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                return error_response(APIError("Internal server error"), 500)
                
        return decorated_function
    return decorator


def safe_file_operation(func):
    """Decorator for safe file operations with proper error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            raise APIError(f"File not found: {str(e)}", 404)
        except PermissionError as e:
            raise APIError(f"Permission denied: {str(e)}", 403)
        except OSError as e:
            raise APIError(f"File operation failed: {str(e)}", 500)
        except Exception as e:
            logger.error(f"File operation error: {str(e)}")
            raise APIError("File processing failed", 500)
    return wrapper