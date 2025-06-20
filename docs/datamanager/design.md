# S3 Storage Manager - Simple MVP
# Modular design with clean separation of concerns and easy extensibility

import os
import boto3
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Iterator
from dataclasses import dataclass
import logging
from functools import wraps

# =======================
# Configuration Module
# =======================

@dataclass
class S3Config:
    """Simple configuration management"""
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    region_name: str = "us-east-1"
    endpoint_url: Optional[str] = None
    bucket: Optional[str] = None
    
    def __post_init__(self):
        # Auto-fill from environment if not provided
        self.aws_access_key_id = self.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = self.aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region_name = os.getenv("AWS_REGION", self.region_name)
        self.endpoint_url = self.endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.bucket = self.bucket or os.getenv("S3_BUCKET")
        
        # Basic validation
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS credentials are required")
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables only"""
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
        """Create config from dictionary"""
        return cls(**config_dict)


# =======================
# Exception Handling
# =======================

class S3StorageError(Exception):
    """Base exception for S3 storage operations"""
    pass

class S3ConnectionError(S3StorageError):
    """Connection-related errors"""
    pass

class S3ObjectNotFound(S3StorageError):
    """Object not found errors"""
    pass

class S3PermissionError(S3StorageError):
    """Permission-related errors"""
    pass


# =======================
# Connection Management
# =======================

class S3Connection:
    """Manages S3 client connection"""
    
    def __init__(self, config: S3Config):
        self.config = config
        self._client = None
        self.logger = logging.getLogger(__name__)
    
    @property
    def client(self):
        """Lazy-loaded S3 client"""
        if self._client is None:
            try:
                session = boto3.Session(
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    region_name=self.config.region_name
                )
                self._client = session.client(
                    "s3",
                    endpoint_url=self.config.endpoint_url
                )
                self.logger.info("S3 client initialized successfully")
            except Exception as e:
                raise S3ConnectionError(f"Failed to create S3 client: {e}")
        return self._client
    
    def get_client(self):
        """Get the S3 client"""
        return self.client


# =======================
# Abstract Interface
# =======================

class StorageInterface(ABC):
    """Abstract interface for storage operations - enables future backends"""
    
    @abstractmethod
    def upload(self, key: str, data, **kwargs): 
        pass
    
    @abstractmethod
    def download(self, key: str, **kwargs): 
        pass
    
    @abstractmethod
    def delete(self, key: str, **kwargs): 
        pass
    
    @abstractmethod
    def list(self, prefix: str = '', **kwargs) -> Iterator[str]: 
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool: 
        pass


# =======================
# Hook System for Extensibility
# =======================

class HookRegistry:
    """Simple hook system for pre/post operation events"""
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register(self, event: str, func: Callable):
        """Register a hook function for an event"""
        self.hooks.setdefault(event, []).append(func)
        logging.getLogger(__name__).debug(f"Registered hook for {event}")
    
    def emit(self, event: str, **kwargs):
        """Emit an event to all registered hooks"""
        for func in self.hooks.get(event, []):
            try:
                func(**kwargs)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Hook {func.__name__} failed: {e}")

# Global hook registry
hooks = HookRegistry()


# =======================
# Utilities
# =======================

def normalize_key(key: str) -> str:
    """Normalize S3 key by removing leading slashes"""
    return key.lstrip('/')

def simple_retry(max_attempts: int = 3):
    """Simple retry decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    logging.getLogger(__name__).warning(f"Attempt {attempt + 1} failed: {e}")
            raise last_exception
        return wrapper
    return decorator


# =======================
# S3 Operations Implementation
# =======================

class S3Operations(StorageInterface):
    """Concrete implementation of storage operations for S3"""
    
    def __init__(self, connection: S3Connection, bucket: str):
        self.connection = connection
        self.bucket = bucket
        self.logger = logging.getLogger(__name__)
    
    @simple_retry(max_attempts=3)
    def upload(self, key: str, data, **kwargs):
        """Upload data to S3"""
        try:
            key = normalize_key(key)
            client = self.connection.get_client()
            
            if hasattr(data, 'read'):
                # File-like object
                client.upload_fileobj(data, self.bucket, key, ExtraArgs=kwargs)
            elif isinstance(data, (str, bytes)):
                # String or bytes
                client.put_object(Bucket=self.bucket, Key=key, Body=data, **kwargs)
            else:
                raise ValueError("Data must be file-like object, string, or bytes")
            
            self.logger.info(f"Uploaded {key} to {self.bucket}")
            
        except Exception as e:
            if "NoSuchBucket" in str(e):
                raise S3StorageError(f"Bucket {self.bucket} does not exist")
            elif "AccessDenied" in str(e):
                raise S3PermissionError(f"Access denied for {key}")
            else:
                raise S3StorageError(f"Upload failed for {key}: {e}")
    
    @simple_retry(max_attempts=3)
    def download(self, key: str, **kwargs):
        """Download data from S3"""
        try:
            key = normalize_key(key)
            client = self.connection.get_client()
            response = client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
            
        except client.exceptions.NoSuchKey:
            raise S3ObjectNotFound(f"{key} not found in bucket {self.bucket}")
        except Exception as e:
            if "AccessDenied" in str(e):
                raise S3PermissionError(f"Access denied for {key}")
            else:
                raise S3StorageError(f"Download failed for {key}: {e}")
    
    @simple_retry(max_attempts=3)
    def delete(self, key: str, **kwargs):
        """Delete object from S3"""
        try:
            key = normalize_key(key)
            client = self.connection.get_client()
            client.delete_object(Bucket=self.bucket, Key=key, **kwargs)
            self.logger.info(f"Deleted {key} from {self.bucket}")
            
        except Exception as e:
            if "AccessDenied" in str(e):
                raise S3PermissionError(f"Access denied for {key}")
            else:
                raise S3StorageError(f"Delete failed for {key}: {e}")
    
    @simple_retry(max_attempts=3)
    def list(self, prefix: str = '', **kwargs) -> Iterator[str]:
        """List objects in S3 with optional prefix"""
        try:
            prefix = normalize_key(prefix)
            client = self.connection.get_client()
            paginator = client.get_paginator('list_objects_v2')
            
            page_iterator = paginator.paginate(
                Bucket=self.bucket, 
                Prefix=prefix,
                **kwargs
            )
            
            for page in page_iterator:
                for obj in page.get('Contents', []):
                    yield obj['Key']
                    
        except Exception as e:
            raise S3StorageError(f"List failed for prefix {prefix}: {e}")
    
    @simple_retry(max_attempts=3)
    def exists(self, key: str) -> bool:
        """Check if object exists in S3"""
        try:
            key = normalize_key(key)
            client = self.connection.get_client()
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            raise S3StorageError(f"Exists check failed for {key}: {e}")


# =======================
# Main Storage Manager
# =======================

class S3StorageManager:
    """Main user-facing API that orchestrates all components"""
    
    def __init__(self, config: Optional[S3Config] = None, bucket: Optional[str] = None):
        # Use provided config or create from environment
        self.config = config or S3Config.from_env()
        
        # Use provided bucket or config bucket
        self.bucket = bucket or self.config.bucket
        if not self.bucket:
            raise ValueError("Bucket must be specified in config or constructor")
        
        # Initialize components
        self.connection = S3Connection(self.config)
        self.operations = S3Operations(self.connection, self.bucket)
        self.logger = logging.getLogger(__name__)
    
    def upload(self, key: str, data, **kwargs):
        """Upload data to S3 with hooks"""
        hooks.emit("pre_upload", key=key, bucket=self.bucket, data=data)
        try:
            self.operations.upload(key, data, **kwargs)
            hooks.emit("post_upload", key=key, bucket=self.bucket, success=True)
        except Exception as e:
            hooks.emit("post_upload", key=key, bucket=self.bucket, success=False, error=e)
            raise
    
    def download(self, key: str, **kwargs):
        """Download data from S3 with hooks"""
        hooks.emit("pre_download", key=key, bucket=self.bucket)
        try:
            result = self.operations.download(key, **kwargs)
            hooks.emit("post_download", key=key, bucket=self.bucket, success=True, size=len(result))
            return result
        except Exception as e:
            hooks.emit("post_download", key=key, bucket=self.bucket, success=False, error=e)
            raise
    
    def delete(self, key: str, **kwargs):
        """Delete object from S3 with hooks"""
        hooks.emit("pre_delete", key=key, bucket=self.bucket)
        try:
            self.operations.delete(key, **kwargs)
            hooks.emit("post_delete", key=key, bucket=self.bucket, success=True)
        except Exception as e:
            hooks.emit("post_delete", key=key, bucket=self.bucket, success=False, error=e)
            raise
    
    def list(self, prefix: str = '', **kwargs) -> List[str]:
        """List objects in S3 with hooks"""
        hooks.emit("pre_list", prefix=prefix, bucket=self.bucket)
        try:
            result = list(self.operations.list(prefix, **kwargs))
            hooks.emit("post_list", prefix=prefix, bucket=self.bucket, success=True, count=len(result))
            return result
        except Exception as e:
            hooks.emit("post_list", prefix=prefix, bucket=self.bucket, success=False, error=e)
            raise
    
    def exists(self, key: str) -> bool:
        """Check if object exists"""
        return self.operations.exists(key)
    
    # Convenience methods
    def upload_file(self, file_path: str, key: Optional[str] = None, **kwargs):
        """Upload a file to S3"""
        if key is None:
            key = os.path.basename(file_path)
        
        with open(file_path, 'rb') as f:
            self.upload(key, f, **kwargs)
    
    def download_file(self, key: str, file_path: str):
        """Download object to a file"""
        data = self.download(key)
        with open(file_path, 'wb') as f:
            f.write(data)


# =======================
# Example Usage & Extensions
# =======================

def setup_logging_hooks():
    """Example: Setup logging hooks for all operations"""
    
    def log_operation_start(**kwargs):
        logging.info(f"Starting operation: {kwargs}")
    
    def log_operation_end(**kwargs):
        if kwargs.get('success'):
            logging.info(f"Operation completed successfully: {kwargs}")
        else:
            logging.error(f"Operation failed: {kwargs}")
    
    # Register hooks for all operations
    for event in ['pre_upload', 'pre_download', 'pre_delete', 'pre_list']:
        hooks.register(event, log_operation_start)
    
    for event in ['post_upload', 'post_download', 'post_delete', 'post_list']:
        hooks.register(event, log_operation_end)


def main():
    """Example usage"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    setup_logging_hooks()
    
    # Initialize manager
    config = S3Config(
        aws_access_key_id="your-key",
        aws_secret_access_key="your-secret", 
        bucket="my-bucket"
    )
    
    # Or from environment
    # manager = S3StorageManager()  # Uses S3Config.from_env()
    
    manager = S3StorageManager(config)
    
    try:
        # Basic operations
        manager.upload("test.txt", b"Hello, World!")
        
        data = manager.download("test.txt")
        print(f"Downloaded: {data.decode()}")
        
        files = manager.list("test")
        print(f"Files: {files}")
        
        exists = manager.exists("test.txt")
        print(f"File exists: {exists}")
        
        # File operations
        # manager.upload_file("/local/file.txt", "remote/file.txt")
        # manager.download_file("remote/file.txt", "/local/downloaded.txt")
        
        manager.delete("test.txt")
        
    except S3StorageError as e:
        print(f"Storage error: {e}")


# =======================
# Extension Examples
# =======================

class MetricsHook:
    """Example: Metrics collection hook"""
    
    def __init__(self):
        self.metrics = {"uploads": 0, "downloads": 0, "deletes": 0}
    
    def track_upload(self, **kwargs):
        if kwargs.get('success'):
            self.metrics["uploads"] += 1
    
    def track_download(self, **kwargs):
        if kwargs.get('success'):
            self.metrics["downloads"] += 1
    
    def track_delete(self, **kwargs):
        if kwargs.get('success'):
            self.metrics["deletes"] += 1
    
    def register_hooks(self):
        hooks.register("post_upload", self.track_upload)
        hooks.register("post_download", self.track_download)
        hooks.register("post_delete", self.track_delete)


# Future extension: Other storage backends
class LocalStorageOperations(StorageInterface):
    """Example: Local filesystem backend (for testing or hybrid setups)"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def upload(self, key: str, data, **kwargs):
        file_path = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if hasattr(data, 'read'):
            with open(file_path, 'wb') as f:
                f.write(data.read())
        else:
            with open(file_path, 'wb') as f:
                f.write(data if isinstance(data, bytes) else data.encode())
    
    def download(self, key: str, **kwargs):
        file_path = os.path.join(self.base_path, key)
        with open(file_path, 'rb') as f:
            return f.read()
    
    def delete(self, key: str, **kwargs):
        file_path = os.path.join(self.base_path, key)
        os.remove(file_path)
    
    def list(self, prefix: str = '', **kwargs):
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.base_path)
                if rel_path.startswith(prefix):
                    yield rel_path.replace(os.sep, '/')
    
    def exists(self, key: str) -> bool:
        file_path = os.path.join(self.base_path, key)
        return os.path.exists(file_path)


if __name__ == "__main__":
    main()