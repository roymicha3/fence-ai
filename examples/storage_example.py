#!/usr/bin/env python
"""
Storage Manager Example

This example demonstrates how to use the storage-agnostic interface
with different storage providers (S3 and local filesystem).
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fence_ai.s3_storage_manager import (
    StorageInterface,
    S3StorageProvider, 
    LocalStorageProvider,
    StorageProviderFactory
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def upload_and_download_example(provider: StorageInterface, key: str, content: str) -> None:
    """
    Example function to upload and download content using a storage provider.
    
    Args:
        provider: Storage provider instance
        key: Object key to use for the example
        content: Content to upload
    """
    # Get storage location information
    location = provider.get_storage_location()
    provider_type = provider.__class__.__name__
    logger.info(f"Using {provider_type} with storage location: {location}")
    
    # Upload content
    logger.info(f"Uploading content to key: {key}")
    upload_result = provider.upload(key, content)
    logger.info(f"Upload successful: {upload_result}")
    
    # Check if object exists
    exists = provider.exists(key)
    logger.info(f"Object exists: {exists}")
    
    # Get metadata
    metadata = provider.get_metadata(key)
    logger.info(f"Object metadata: {metadata}")
    
    # Download content
    logger.info(f"Downloading content from key: {key}")
    downloaded_content = provider.download(key)
    logger.info(f"Downloaded content: {downloaded_content.decode('utf-8')}")
    
    # List objects
    logger.info(f"Listing objects with prefix: {os.path.dirname(key)}")
    objects = list(provider.list(prefix=os.path.dirname(key)))
    logger.info(f"Found {len(objects)} objects")
    for obj in objects:
        logger.info(f"  - {obj['key']} ({obj['size']} bytes)")
    
    # Delete object
    logger.info(f"Deleting object: {key}")
    delete_result = provider.delete(key)
    logger.info(f"Delete successful: {delete_result}")
    
    # Verify deletion
    exists = provider.exists(key)
    logger.info(f"Object exists after deletion: {exists}")


def main():
    """Main function to run the example."""
    # Example content
    example_key = "examples/test-file.txt"
    example_content = "This is a test file created by the storage example script."
    
    # Create temporary directory for local storage
    temp_dir = Path("/tmp/storage-example")
    temp_dir.mkdir(exist_ok=True)
    
    # Example 1: Using S3StorageProvider directly
    try:
        logger.info("=== Example 1: Using S3StorageProvider directly ===")
        # Replace with your actual AWS credentials and bucket name
        # If using IAM roles, you can omit aws_access_key_id and aws_secret_access_key
        s3_provider = S3StorageProvider(
            connection=S3Connection(
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
                bucket_name=os.environ.get("S3_BUCKET_NAME")
            )
        )
        
        # Run the example with S3 provider
        upload_and_download_example(s3_provider, example_key, example_content)
    except Exception as e:
        logger.error(f"S3 example failed: {e}")
    
    # Example 2: Using LocalStorageProvider directly
    try:
        logger.info("\n=== Example 2: Using LocalStorageProvider directly ===")
        local_provider = LocalStorageProvider(base_path=str(temp_dir))
        
        # Run the example with local provider
        upload_and_download_example(local_provider, example_key, example_content)
    except Exception as e:
        logger.error(f"Local storage example failed: {e}")
    
    # Example 3: Using StorageProviderFactory for S3
    try:
        logger.info("\n=== Example 3: Using StorageProviderFactory for S3 ===")
        s3_config = {
            "provider": "s3",
            "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.environ.get("AWS_REGION", "us-east-1"),
            "bucket_name": os.environ.get("S3_BUCKET_NAME")
        }
        
        s3_provider = StorageProviderFactory.create_provider(s3_config)
        
        # Run the example with factory-created S3 provider
        upload_and_download_example(s3_provider, example_key, example_content)
    except Exception as e:
        logger.error(f"S3 factory example failed: {e}")
    
    # Example 4: Using StorageProviderFactory for local storage
    try:
        logger.info("\n=== Example 4: Using StorageProviderFactory for local storage ===")
        local_config = {
            "provider": "local",
            "base_path": str(temp_dir)
        }
        
        local_provider = StorageProviderFactory.create_provider(local_config)
        
        # Run the example with factory-created local provider
        upload_and_download_example(local_provider, example_key, example_content)
    except Exception as e:
        logger.error(f"Local storage factory example failed: {e}")


if __name__ == "__main__":
    # Import here to avoid circular imports
    from fence_ai.s3_storage_manager.connection import S3Connection
    
    main()
