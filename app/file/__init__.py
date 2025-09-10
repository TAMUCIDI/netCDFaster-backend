from werkzeug.utils import secure_filename
from pathlib import Path
import os
import hashlib
import logging
import numpy as np
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, session, send_file

from .fileProcess import read_metadata, query_variable, plot_subset
from ..schemas import FileUploadSchema, VariablePlotSchema, RemoteFileQuerySchema
from ..utils import validate_request, success_response, error_response, APIError, safe_file_operation
from ..resource_manager import resource_manager
from ..model.model import get_model_status, reload_model

logger = logging.getLogger(__name__)

file_bp = Blueprint('file', __name__, url_prefix='/file')

def convert_numpy_types(obj):
    """Convert numpy types to JSON serializable Python types"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    else:
        return obj

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
        
        # Calculate file content hash to avoid duplicates
        file.seek(0)
        hasher = hashlib.md5()
        for chunk in iter(lambda: file.read(4096), b""):
            hasher.update(chunk)
        file_hash = hasher.hexdigest()
        file.seek(0)  # Reset file pointer for saving
        
        # Use hash as filename to avoid duplicates
        hashed_filename = f"{file_hash}.nc"
        tmp_file_path = os.path.join(upload_folder, hashed_filename)
        
        # Check if file already exists
        if os.path.exists(tmp_file_path):
            logger.info(f"File already exists, reusing: {hashed_filename} (original: {filename})")
            # Verify existing file size matches
            actual_size = os.path.getsize(tmp_file_path)
            if actual_size != file_size:
                logger.warning(f"Existing file size mismatch, re-saving: {hashed_filename}")
                file.save(tmp_file_path)
        else:
            logger.info(f"Saving new file: {hashed_filename} (original: {filename})")
            file.save(tmp_file_path)
            
            # Verify saved file
            actual_size = os.path.getsize(tmp_file_path)
            if actual_size != file_size:
                raise APIError("File upload verification failed", 500)
        
        # Save file info to session
        session['file_path'] = str(tmp_file_path)
        session['file_hash'] = file_hash
        session['original_filename'] = filename
        session['file_type'] = 'local'
        
        logger.info(f"File processed: {filename} -> {hashed_filename} ({file_size/1024/1024:.2f}MB), Session: {session.sid}")
        
        # Read metadata with error handling
        metaInfo = read_metadata(tmp_file_path)
        
        # Convert numpy types to JSON serializable types
        metaInfo = convert_numpy_types(metaInfo)
        
        # Add file info to response
        metaInfo['upload_info'] = {
            'original_filename': filename,
            'file_size_mb': round(file_size / 1024 / 1024, 2),
            'file_hash': file_hash,
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

@file_bp.route('/remoteQuery', methods=['POST'])
@validate_request(RemoteFileQuerySchema)
@safe_file_operation
def remote_query(validated_data):
    try:
        # Check system resources first
        if not resource_manager.check_system_resources():
            raise APIError("System resources insufficient for remote file processing", 503)
        
        remote_url = validated_data['url']
        
        logger.info(f"Querying remote NetCDF file: {remote_url}")
        
        # Read metadata from remote URL directly
        metaInfo = read_metadata(remote_url)
        
        # Store remote URL in session for later variable queries
        session['remote_url'] = remote_url
        session['file_type'] = 'remote'
        
        # Convert numpy types to JSON serializable types
        metaInfo = convert_numpy_types(metaInfo)
        
        # Add remote file info to response
        metaInfo['remote_info'] = {
            'url': remote_url,
            'access_time': datetime.now().isoformat(),
            'file_type': 'remote_netcdf'
        }
        
        return success_response(metaInfo, "Remote NetCDF file metadata retrieved successfully")
        
    except Exception as e:
        logger.error(f"Remote query failed for URL {remote_url}: {str(e)}")
        # Provide more specific error messages
        if "No such file or directory" in str(e) or "file not found" in str(e).lower():
            raise APIError("Remote NetCDF file not found or inaccessible", 404)
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            raise APIError("Access denied to remote NetCDF file", 403)
        elif "timeout" in str(e).lower():
            raise APIError("Timeout accessing remote NetCDF file", 408)
        else:
            raise APIError(f"Failed to process remote NetCDF file: {str(e)}", 500)

@file_bp.route('/detail/<string:var_name>', methods=['GET'])
@safe_file_operation
def variable_name(var_name):
    try:
        # Validate variable name
        if not var_name or len(var_name.strip()) == 0:
            raise APIError("Variable name cannot be empty", 400)
        
        if len(var_name) > 100:
            raise APIError("Variable name too long", 400)
        
        # Determine file source and get appropriate path/URL
        file_type = session.get('file_type')
        
        if file_type == 'local':
            # Handle local uploaded file
            file_path = session.get('file_path')
            if not file_path:
                raise APIError("No uploaded file found. Please upload a file first", 404)
            
            file_path = Path(file_path)
            if not file_path.exists():
                raise APIError("Uploaded file no longer exists", 404)
            
            logger.info(f"Querying variable: {var_name} from local file, Session: {session.sid}")
            data_source = file_path
            
        elif file_type == 'remote':
            # Handle remote URL file
            remote_url = session.get('remote_url')
            if not remote_url:
                raise APIError("No remote file URL found. Please query a remote file first", 404)
            
            logger.info(f"Querying variable: {var_name} from remote URL: {remote_url}, Session: {session.sid}")
            data_source = remote_url
            
        else:
            # No file source available
            raise APIError("No file source found. Please upload a file or query a remote URL first", 404)
        
        # Query variable with error handling
        variable_info = query_variable(data_source, var_name)
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
        # Determine file source and get appropriate path/URL
        file_type = session.get('file_type')
        
        if file_type == 'local':
            # Handle local uploaded file
            file_path = session.get('file_path')
            if not file_path:
                raise APIError("No uploaded file found. Please upload a file first", 404)
            
            file_path = Path(file_path)
            if not file_path.exists():
                raise APIError("Uploaded file no longer exists", 404)
            
            data_source = file_path
            
        elif file_type == 'remote':
            # Handle remote URL file
            remote_url = session.get('remote_url')
            if not remote_url:
                raise APIError("No remote file URL found. Please query a remote file first", 404)
            
            data_source = remote_url
            
        else:
            # No file source available
            raise APIError("No file source found. Please upload a file or query a remote URL first", 404)
        
        # Check if variable info exists in session
        var_name = validated_data['varName']
        if var_name not in session:
            raise APIError(f"Variable '{var_name}' not found. Please query variable details first", 404)
        
        # Validate coordinates against actual data ranges
        variable_coords = session[var_name]['coords']
        
        # Find longitude coordinate and validate range
        lon_coord = None
        for coord in variable_coords:
            coord_name = coord['name'].lower()
            if any(name in coord_name for name in ['lon', 'longitude', 'x']):
                lon_coord = coord
                break
        
        if lon_coord:
            lon_min = float(lon_coord['min'])
            lon_max = float(lon_coord['max'])
            req_lon_min = validated_data['lonMin']
            req_lon_max = validated_data['lonMax']
            
            if req_lon_min < lon_min or req_lon_max > lon_max:
                raise APIError(f"Longitude range [{req_lon_min}, {req_lon_max}] is outside data bounds [{lon_min}, {lon_max}]", 400)
        
        # Find latitude coordinate and validate range
        lat_coord = None
        for coord in variable_coords:
            coord_name = coord['name'].lower()
            if any(name in coord_name for name in ['lat', 'latitude', 'y']):
                lat_coord = coord
                break
        
        if lat_coord:
            lat_min = float(lat_coord['min'])
            lat_max = float(lat_coord['max'])
            req_lat_min = validated_data['latMin']
            req_lat_max = validated_data['latMax']
            
            if req_lat_min < lat_min or req_lat_max > lat_max:
                raise APIError(f"Latitude range [{req_lat_min}, {req_lat_max}] is outside data bounds [{lat_min}, {lat_max}]", 400)
        
        logger.info(f"Plotting variable: {var_name}, Session: {session.sid}")
        
        # Generate plot with error handling
        fig_buf = plot_subset(data_source, validated_data, session)
        
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