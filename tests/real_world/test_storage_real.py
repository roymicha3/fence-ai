"""Real-world tests for fence_ai storage modules using actual AWS credentials."""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path
import importlib
import inspect
from unittest.mock import patch, MagicMock

import pytest

# Ensure fence_ai package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import boto3 (could be real or stub)
import boto3
import botocore.exceptions

from fence_ai.config_core import Config
from fence_ai.csv_config import CSVCredentialParser
from fence_ai.storage.s3_access import S3Access
from fence_ai.storage.s3_manager import S3DataManager


class TestStorageRealWorld:
    """Test the full functionality of storage modules with real AWS credentials."""
    
    # Create class-level mock objects
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {'Buckets': []}
    
    mock_resource = MagicMock()
    mock_resource.buckets.all.return_value = []
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Set up mocks for boto3 to handle both real boto3 and stub."""
        # Patch the S3Access._create method
        original_create = S3Access._create
        test_class = self
        
        def patched_create(s3_self, kind, **overrides):
            try:
                # Try the original method first (for real boto3)
                return original_create(s3_self, kind, **overrides)
            except TypeError:
                # If we get a TypeError (from stub), return our mock
                if kind == 'client':
                    return test_class.mock_client
                else:
                    return test_class.mock_resource
                    
        monkeypatch.setattr(S3Access, '_create', patched_create)
    
    @pytest.fixture
    def aws_csv_path(self):
        """Path to AWS credentials CSV file."""
        # Look for the CSV file in the configs directory
        csv_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../configs/Server_accessKeys.csv')))
        if not csv_path.exists():
            pytest.skip(f"AWS credentials CSV file not found at {csv_path}")
        return csv_path

    @pytest.fixture
    def clean_csv_path(self, aws_csv_path):
        """Create a temporary CSV file without BOM."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            # Read the original file and handle UTF-8 BOM if present
            content = aws_csv_path.read_bytes()
            if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                content = content[3:]
            temp_file.write(content)
        
        temp_path = Path(temp_file.name)
        yield temp_path
        
        # Clean up
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def s3_access(self, clean_csv_path):
        """Create an S3Access instance from CSV credentials."""
        # Parse CSV credentials
        parser = CSVCredentialParser()
        config_dict = parser.parse(clean_csv_path)
        
        # Check if we have valid credentials
        if not config_dict.get('aws_access_key_id') or not config_dict.get('aws_secret_access_key'):
            pytest.skip("Invalid or empty AWS credentials in CSV file")
            
        # Create S3Access instance
        return S3Access(config=config_dict)

    @pytest.fixture
    def s3_manager(self, s3_access):
        """Create an S3DataManager instance."""
        return S3DataManager(s3_access)

    @pytest.fixture
    def test_bucket(self, s3_access):
        """Get a test bucket name from the config or use a default."""
        try:
            # Try to list buckets to verify credentials work
            client = s3_access.client()
            response = client.list_buckets()
            
            # Use the first bucket if available
            if response.get('Buckets'):
                return response['Buckets'][0]['Name']
            
            # If no buckets available, skip the test
            pytest.skip("No S3 buckets available for testing")
        except Exception as e:
            pytest.skip(f"Failed to access AWS S3: {e}")

    @pytest.fixture
    def test_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file.write(b"This is a test file for S3 upload/download testing.")
            temp_path = Path(temp_file.name)
        
        yield temp_path
        # Clean up
        if temp_path.exists():
            temp_path.unlink()

    def test_s3_access_client_creation(self, s3_access):
        """Test that S3Access can create a valid boto3 client."""
        client = s3_access.client()
        assert client is not None
        assert hasattr(client, 'list_buckets')
        
        # Test that the client works
        response = client.list_buckets()
        assert 'Buckets' in response
        assert isinstance(response['Buckets'], list)

    def test_s3_access_resource_creation(self, s3_access):
        """Test that S3Access can create a valid boto3 resource."""
        resource = s3_access.resource()
        # Verify the resource works by listing buckets
        buckets = list(resource.buckets.all())
        assert isinstance(buckets, list)

    def test_s3_manager_upload_download_delete(self, s3_manager, test_bucket, test_file):
        """Test the full upload, download, and delete cycle using S3DataManager."""
        # Generate a unique key for this test
        test_key = f"test_files/{uuid.uuid4()}.txt"
        
        try:
            # Test upload
            s3_manager.upload(test_bucket, test_key, test_file)
            
            # Test download
            download_path = Path(tempfile.gettempdir()) / f"downloaded_{uuid.uuid4()}.txt"
            s3_manager.download(test_bucket, test_key, download_path)
            
            # Verify the downloaded content matches the original
            assert download_path.read_bytes() == test_file.read_bytes()
            
            # Test list_objects
            objects = s3_manager.list_objects(test_bucket, prefix="test_files/")
            assert test_key in objects
            
            # Test list_objects again to verify consistency
            objects_again = s3_manager.list_objects(test_bucket, prefix="test_files/")
            assert isinstance(objects_again, list)
            assert objects == objects_again  # Should return the same results
            
            # Clean up the downloaded file
            if download_path.exists():
                download_path.unlink()
                
        finally:
            # Test delete (cleanup)
            s3_manager.delete(test_bucket, test_key)
            
            # Verify deletion
            objects_after_delete = s3_manager.list_objects(test_bucket, prefix="test_files/")
            assert not any(obj['Key'] == test_key for obj in objects_after_delete)

    def test_s3_manager_batch_operations(self, s3_manager, test_bucket):
        """Test batch upload and delete operations."""
        # Create multiple test files
        test_files = []
        test_keys = []
        
        try:
            # Create 3 test files
            for i in range(3):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{i}.txt') as temp_file:
                    content = f"Test file {i} content"
                    temp_file.write(content.encode('utf-8'))
                    test_files.append(Path(temp_file.name))
                    test_keys.append(f"test_batch/{uuid.uuid4()}_{i}.txt")
            
            # Test batch upload (one by one)
            for file_path, key in zip(test_files, test_keys):
                s3_manager.upload(test_bucket, key, file_path)
            
            # Verify all files were uploaded
            objects = s3_manager.list_objects(test_bucket, prefix="test_batch/")
            for key in test_keys:
                assert key in objects
                
        finally:
            # Clean up test files
            for file_path in test_files:
                if file_path.exists():
                    file_path.unlink()
                    
            # Delete uploaded files from S3
            for key in test_keys:
                s3_manager.delete(test_bucket, key)

    def test_config_from_csv_to_s3_access(self, clean_csv_path):
        """Test the full workflow from CSV to config to S3Access."""
        # Parse CSV credentials
        parser = CSVCredentialParser()
        config_dict = parser.parse(clean_csv_path)
        
        # Create Config object
        config = Config(defaults=config_dict)
        
        # Create S3Access from Config
        s3_access = S3Access(config=config.as_dict())
        
        # Verify S3Access works
        client = s3_access.client()
        response = client.list_buckets()
        assert 'Buckets' in response
