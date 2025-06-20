"""
Storage Interface module.

This module defines the abstract interface for storage operations.
"""

from abc import ABC, abstractmethod
from typing import Iterator


class StorageInterface(ABC):
    """
    Abstract interface for storage operations.
    
    This interface defines the standard methods that all storage backends must implement.
    It enables future alternative implementations (Local, Azure, GCP, etc.).
    """
    
    @abstractmethod
    def upload(self, key: str, data, **kwargs): 
        """
        Upload data to storage.
        
        Args:
            key: Object key
            data: Data to upload (bytes or file-like object)
            **kwargs: Additional arguments for the storage backend
        """
        pass
    
    @abstractmethod
    def download(self, key: str, **kwargs): 
        """
        Download data from storage.
        
        Args:
            key: Object key
            **kwargs: Additional arguments for the storage backend
            
        Returns:
            bytes: The downloaded data
        """
        pass
    
    @abstractmethod
    def delete(self, key: str, **kwargs): 
        """
        Delete an object from storage.
        
        Args:
            key: Object key
            **kwargs: Additional arguments for the storage backend
        """
        pass
    
    @abstractmethod
    def list(self, prefix: str = '', **kwargs) -> Iterator[str]: 
        """
        List objects in storage with optional prefix.
        
        Args:
            prefix: Optional prefix to filter objects
            **kwargs: Additional arguments for the storage backend
            
        Returns:
            Iterator[str]: Iterator of object keys
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool: 
        """
        Check if an object exists in storage.
        
        Args:
            key: Object key
            
        Returns:
            bool: True if the object exists, False otherwise
        """
        pass
