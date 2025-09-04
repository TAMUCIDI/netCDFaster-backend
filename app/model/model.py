import os
import joblib
from math import ceil
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

X_columns = [
    'lon_len',
    'lat_len', 
    'time_len', 
    'file_size',
    'var_dim_len', 
    'variable_size', 
    'lon_query_len', 
    'lat_query_len',
    'time_query_len'
]

# Global model cache
_model_cache = None
_model_path = None

def get_query_policy(n):
    # 定义表格数据，NaN用np.nan表示
    data = [
        [np.nan, np.nan, np.nan],  # 第1行
        [2.0, 2.0, 2.0],           # 第2行
        [4.0, 4.0, 4.0],           # 第3行
        [2.0, np.nan, np.nan],     # 第4行
        [np.nan, 2.0, np.nan],     # 第5行
        [np.nan, np.nan, 2.0],     # 第6行
        [np.nan, 2.0, 4.0],        # 第7行
        [2.0, np.nan, 4.0],        # 第8行
        [2.0, 4.0, np.nan],        # 第9行
    ]
    if 0 <= n <= 8:
        return data[n]  # 输入1对应索引0，依此类推
    else:
        raise ValueError("输入必须为1到9之间的整数")

def calculate_chunk_size(total_length, num_divisions):
    if np.isnan(num_divisions):
        return None
    else:
        return ceil(total_length / num_divisions)


def get_default_chunking_strategy(x_array):
    """Default chunking strategy when ML model is not available"""
    try:
        file_size_mb = x_array[3] / (1024 * 1024)
        
        # Simple heuristic based on file size
        if file_size_mb < 50:  # Small files
            return {
                'lon': None,
                'lat': None,  
                'time': None
            }
        elif file_size_mb < 500:  # Medium files
            return {
                'lon': calculate_chunk_size(x_array[6], 2),
                'lat': calculate_chunk_size(x_array[7], 2),
                'time': calculate_chunk_size(x_array[8], 2) if x_array[4] == 3 else None
            }
        else:  # Large files
            return {
                'lon': calculate_chunk_size(x_array[6], 4),
                'lat': calculate_chunk_size(x_array[7], 4),
                'time': calculate_chunk_size(x_array[8], 4) if x_array[4] == 3 else None
            }
    except Exception as e:
        logger.warning(f"Default chunking strategy failed: {e}")
        # Ultra-safe fallback
        return {
            'lon': calculate_chunk_size(x_array[6], 2) if x_array[6] > 100 else None,
            'lat': calculate_chunk_size(x_array[7], 2) if x_array[7] > 100 else None,
            'time': None
        }


def load_model():
    """Load ML model with proper error handling and caching"""
    global _model_cache, _model_path
    
    try:
        load_dotenv(dotenv_path=".env")
        model_path = os.getenv("MODEL_PKL_PATH")
        
        if not model_path:
            logger.warning("MODEL_PKL_PATH not set in environment variables")
            return None
        
        model_path = Path(model_path)
        
        if not model_path.exists():
            logger.warning(f"Model file not found at: {model_path}")
            return None
        
        # Check if we need to reload the model
        if _model_cache is None or _model_path != str(model_path):
            logger.info(f"Loading ML model from: {model_path}")
            _model_cache = joblib.load(str(model_path))
            _model_path = str(model_path)
            logger.info("ML model loaded successfully")
        
        return _model_cache
        
    except Exception as e:
        logger.error(f"Failed to load ML model: {str(e)}")
        return None


def validate_prediction_input(x_array):
    """Validate input for prediction"""
    if not isinstance(x_array, (list, np.ndarray)):
        raise ValueError("Input must be a list or numpy array")
    
    if len(x_array) != 9:
        raise ValueError(f"Input array must have exactly 9 elements, got {len(x_array)}")
    
    # Check for reasonable value ranges
    if x_array[0] <= 0 or x_array[1] <= 0:  # lon_len, lat_len
        raise ValueError("Longitude and latitude lengths must be positive")
    
    if x_array[3] <= 0 or x_array[5] <= 0:  # file_size, variable_size
        raise ValueError("File and variable sizes must be positive")
    
    return True

def predict_query_chunk(x_array):
    """
    Predict optimal chunking strategy using ML model with fallback mechanism
    
    Args:
        x_array: List/array of 9 numerical features
        
    Returns:
        dict: Chunking configuration for xarray
    """
    try:
        # Validate input
        validate_prediction_input(x_array)
        
        # Convert to numpy array if needed
        if not isinstance(x_array, np.ndarray):
            x_array = np.array(x_array)
        
        # Try to load and use ML model
        model = load_model()
        
        if model is not None:
            try:
                # Reshape for single prediction
                x_input = x_array.reshape(1, -1)
                
                # Make prediction
                y_pred = model.predict(x_input).reshape(-1)
                policy_index = int(y_pred[0])
                
                # Validate prediction result
                if not (0 <= policy_index <= 8):
                    logger.warning(f"Model prediction out of range: {policy_index}, using default strategy")
                    return get_default_chunking_strategy(x_array)
                
                # Convert to chunking policy
                policy_table = get_query_policy(policy_index)
                
                chunk_dict = {
                    'lon': calculate_chunk_size(x_array[6], policy_table[0]),
                    'lat': calculate_chunk_size(x_array[7], policy_table[1]),
                    'time': calculate_chunk_size(x_array[8], policy_table[2]) if x_array[4] == 3 else None,
                }
                
                logger.info(f"ML Prediction - Policy: {policy_index}, Chunks: lon={chunk_dict['lon']}, lat={chunk_dict['lat']}, time={chunk_dict['time']}")
                return chunk_dict
                
            except Exception as e:
                logger.error(f"ML model prediction failed: {str(e)}")
                logger.info("Falling back to default chunking strategy")
        else:
            logger.info("ML model not available, using default chunking strategy")
        
        # Fallback to default strategy
        chunk_dict = get_default_chunking_strategy(x_array)
        logger.info(f"Default Strategy - Chunks: lon={chunk_dict['lon']}, lat={chunk_dict['lat']}, time={chunk_dict['time']}")
        
        return chunk_dict
        
    except Exception as e:
        logger.error(f"Chunking prediction completely failed: {str(e)}")
        # Ultra-safe emergency fallback
        return {
            'lon': None,
            'lat': None,
            'time': None
        }


def reload_model():
    """Force reload of the ML model"""
    global _model_cache, _model_path
    _model_cache = None
    _model_path = None
    logger.info("Model cache cleared, will reload on next prediction")
    return load_model() is not None


def get_model_status():
    """Get current model loading status"""
    model = load_model()
    return {
        'model_available': model is not None,
        'model_path': _model_path,
        'fallback_strategy': 'heuristic-based' if model is None else 'ml-based'
    }