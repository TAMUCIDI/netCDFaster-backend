import os
import time
import shutil
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from threading import Thread
import logging
from flask import current_app

logger = logging.getLogger(__name__)


class ResourceManager:
    """Resource management for file operations and memory monitoring"""
    
    def __init__(self, max_file_size_mb=100, max_disk_usage_gb=5, cleanup_interval_hours=1):
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.max_disk_usage = max_disk_usage_gb * 1024 * 1024 * 1024  # Convert to bytes
        self.cleanup_interval = cleanup_interval_hours * 3600  # Convert to seconds
        self.cleanup_thread = None
        self._running = False
    
    def check_system_resources(self):
        """Check if system has enough resources"""
        try:
            # Check available memory
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                raise ResourceWarning(f"System memory usage too high: {memory.percent:.1f}%")
            
            # Check available disk space
            if hasattr(current_app, 'config'):
                upload_folder = current_app.config.get('UPLOAD_FOLDER')
                if upload_folder:
                    disk = psutil.disk_usage(str(upload_folder))
                    if disk.percent > 90:
                        raise ResourceWarning(f"Disk usage too high: {disk.percent:.1f}%")
            
            return True
            
        except Exception as e:
            logger.warning(f"Resource check failed: {str(e)}")
            return False
    
    def validate_file_size(self, file_path):
        """Validate file size against limits"""
        try:
            if isinstance(file_path, str):
                file_size = os.path.getsize(file_path)
            else:
                # File object
                file_path.seek(0, os.SEEK_END)
                file_size = file_path.tell()
                file_path.seek(0)
            
            if file_size > self.max_file_size:
                raise ValueError(f"File size {file_size/1024/1024:.1f}MB exceeds limit of {self.max_file_size/1024/1024:.1f}MB")
            
            return file_size
            
        except Exception as e:
            logger.error(f"File size validation failed: {str(e)}")
            raise
    
    def get_directory_size(self, directory):
        """Calculate total size of directory"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.warning(f"Error calculating directory size: {str(e)}")
        
        return total_size
    
    def cleanup_old_files(self, directory, max_age_hours=24):
        """Clean up files older than specified hours"""
        if not os.path.exists(directory):
            return 0
        
        cleaned_count = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    # Check file age
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"Cleaned up old file: {filename}")
                        
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
        
        return cleaned_count
    
    def enforce_disk_usage_limit(self, directory):
        """Remove oldest files if directory exceeds size limit"""
        current_size = self.get_directory_size(directory)
        
        if current_size <= self.max_disk_usage:
            return 0
        
        # Get files sorted by modification time (oldest first)
        files = []
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)
                    files.append((mtime, file_path, size))
            
            files.sort(key=lambda x: x[0])  # Sort by modification time
            
            removed_count = 0
            target_size = self.max_disk_usage * 0.8  # Remove files until 80% of limit
            
            for mtime, file_path, size in files:
                if current_size <= target_size:
                    break
                
                os.remove(file_path)
                current_size -= size
                removed_count += 1
                logger.info(f"Removed file to enforce disk limit: {os.path.basename(file_path)}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Disk usage enforcement failed: {str(e)}")
            return 0
    
    def start_cleanup_service(self, upload_folder):
        """Start background cleanup service"""
        if self._running:
            return
        
        self._running = True
        
        def cleanup_worker():
            while self._running:
                try:
                    logger.info("Running scheduled cleanup...")
                    
                    # Clean up old files
                    cleaned = self.cleanup_old_files(upload_folder, max_age_hours=24)
                    
                    # Enforce disk usage limits
                    removed = self.enforce_disk_usage_limit(upload_folder)
                    
                    if cleaned > 0 or removed > 0:
                        logger.info(f"Cleanup completed: {cleaned} old files, {removed} files for disk limit")
                    
                except Exception as e:
                    logger.error(f"Cleanup service error: {str(e)}")
                
                # Wait for next cleanup cycle
                time.sleep(self.cleanup_interval)
        
        self.cleanup_thread = Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info("Cleanup service started")
    
    def stop_cleanup_service(self):
        """Stop background cleanup service"""
        self._running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Cleanup service stopped")
    
    def get_resource_stats(self, upload_folder):
        """Get current resource usage statistics"""
        try:
            memory = psutil.virtual_memory()
            
            stats = {
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'cleanup_running': self._running
            }
            
            if os.path.exists(upload_folder):
                disk = psutil.disk_usage(upload_folder)
                directory_size = self.get_directory_size(upload_folder)
                
                stats.update({
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                    'upload_folder_size_mb': directory_size / 1024 / 1024,
                    'upload_folder_limit_mb': self.max_disk_usage / 1024 / 1024
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get resource stats: {str(e)}")
            return {'error': 'Failed to get resource statistics'}


# Global resource manager instance
resource_manager = ResourceManager()