from werkzeug.utils import secure_filename
from pathlib import Path
import os
import time
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, session, send_file

from .fileProcess import read_metadata, query_variable, plot_subset
from ..schemas import FileUploadSchema, VariablePlotSchema
from ..utils import validate_request, success_response, error_response, APIError, safe_file_operation
from ..resource_manager import resource_manager
from ..model.model import get_model_status, reload_model

logger = logging.getLogger(__name__)

file_bp = Blueprint('file', __name__, url_prefix='/file')

@file_bp.route('/upload', methods=['POST'])
@validate_request(FileUploadSchema)
@safe_file_operation
def upload_file(validated_data):
    tmp_file_path = None
    try:
        # Check system resources first
        if not resource_manager.check_system_resources():
            raise APIError("System resources insufficient for file processing", 503)
        
        file = validated_data['file']
        filename = secure_filename(file.filename)
        
        # Check upload folder exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            raise APIError("Upload directory not configured properly", 500)
        
        # Validate file size using resource manager
        file_size = resource_manager.validate_file_size(file)
        
        # Generate unique filename to avoid conflicts
        timestamp = str(int(time.time()))
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        tmp_file_path = os.path.join(upload_folder, unique_filename)
        
        file.save(tmp_file_path)
        
        # Verify saved file
        actual_size = os.path.getsize(tmp_file_path)
        if actual_size != file_size:
            raise APIError("File upload verification failed", 500)
        
        # Save file path to session with cleanup timestamp
        session['file_path'] = str(tmp_file_path)
        session['upload_time'] = time.time()
        session['original_filename'] = filename
        
        logger.info(f"File uploaded: {filename} -> {unique_filename} ({file_size/1024/1024:.2f}MB), Session: {session.sid}")
        
        # Read metadata with error handling
        metaInfo = read_metadata(tmp_file_path)
        
        # Add file info to response
        metaInfo['upload_info'] = {
            'original_filename': filename,
            'file_size_mb': round(file_size / 1024 / 1024, 2),
            'upload_time': datetime.now().isoformat()
        }
        
        return success_response(metaInfo, "File uploaded successfully")
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Clean up file if it exists
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
                logger.info(f"Cleaned up failed upload: {tmp_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup file: {cleanup_error}")
        raise

@file_bp.route('/detail/<string:var_name>', methods=['GET'])
@safe_file_operation
def variable_name(var_name):
    try:
        # Validate variable name
        if not var_name or len(var_name.strip()) == 0:
            raise APIError("Variable name cannot be empty", 400)
        
        if len(var_name) > 100:
            raise APIError("Variable name too long", 400)
        
        # Get file path from session
        file_path = session.get('file_path')
        if not file_path:
            raise APIError("No uploaded file found. Please upload a file first", 404)
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise APIError("Uploaded file no longer exists", 404)
        
        logger.info(f"Querying variable: {var_name}, Session: {session.sid}")
        
        # Query variable with error handling
        variable_info = query_variable(file_path, var_name)
        session[var_name] = variable_info
        
        return success_response(variable_info, f"Variable '{var_name}' information retrieved")
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Variable query failed: {str(e)}")
        raise APIError(f"Failed to query variable '{var_name}'", 500)

@file_bp.route('/varplot', methods=['GET'])
@validate_request(VariablePlotSchema)
@safe_file_operation
def plot_variable(validated_data):
    try:
        # Get file path from session
        file_path = session.get('file_path')
        if not file_path:
            raise APIError("No uploaded file found. Please upload a file first", 404)
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise APIError("Uploaded file no longer exists", 404)
        
        # Check if variable info exists in session
        var_name = validated_data['varName']
        if var_name not in session:
            raise APIError(f"Variable '{var_name}' not found. Please query variable details first", 404)
        
        logger.info(f"Plotting variable: {var_name}, Session: {session.sid}")
        
        # Generate plot with error handling
        fig_buf = plot_subset(file_path, validated_data, session)
        
        return send_file(fig_buf, mimetype='image/png')
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Plot generation failed: {str(e)}")
        raise APIError("Failed to generate plot", 500)


@file_bp.route('/resources', methods=['GET'])
def get_resource_stats():
    """Get current system resource usage statistics"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        stats = resource_manager.get_resource_stats(upload_folder)
        
        return success_response(stats, "Resource statistics retrieved")
        
    except Exception as e:
        logger.error(f"Failed to get resource stats: {str(e)}")
        raise APIError("Failed to retrieve resource statistics", 500)


@file_bp.route('/model/status', methods=['GET'])
def get_ml_model_status():
    """Get ML model loading status and health check"""
    try:
        status = get_model_status()
        return success_response(status, "Model status retrieved")
        
    except Exception as e:
        logger.error(f"Failed to get model status: {str(e)}")
        raise APIError("Failed to retrieve model status", 500)


@file_bp.route('/model/reload', methods=['POST'])
def reload_ml_model():
    """Force reload of the ML model"""
    try:
        success = reload_model()
        
        if success:
            return success_response(
                {"reloaded": True}, 
                "Model reloaded successfully"
            )
        else:
            return success_response(
                {"reloaded": False}, 
                "Model reload failed, using fallback strategy"
            )
        
    except Exception as e:
        logger.error(f"Failed to reload model: {str(e)}")
        raise APIError("Failed to reload model", 500)