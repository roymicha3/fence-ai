"""Integration tests for the CSV to S3 config converter module."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fence_ai.csv_config as csv_config
from fence_ai.csv_config import csv_to_config
from fence_ai.storage.s3_access import S3Access


@pytest.fixture
def sample_csv_path():
    """Create a temporary CSV file with sample AWS credentials."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        f.write("Access key ID,Secret access key\n")
        f.write("AKIAEXAMPLE123456789,abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE\n")
    
    path = Path(f.name)
    yield path
    path.unlink()


class TestCSVConfigIntegration:
    """Integration tests for the CSV to S3 config converter."""
    
    @patch('boto3.Session')
    def test_integration_with_s3_access(self, mock_session, sample_csv_path):
        """Test integration with S3Access class."""
        # Setup mock boto3 session
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Generate config file
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            # Convert CSV to config
            result_path = csv_to_config(
                csv_path=sample_csv_path,
                output_path=config_path,
                format="json",
                region="us-east-1"
            )
            
            assert result_path.exists()
            
            # Read the generated config file
            config_data = json.loads(config_path.read_text())
            
            # Verify config file contents
            assert config_data["aws_access_key_id"] == "AKIAEXAMPLE123456789"
            assert config_data["aws_secret_access_key"] == "abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
            assert config_data["region_name"] == "us-east-1"
            
            # Try to initialize S3Access with the generated config
            s3_access = S3Access(config_file=str(config_path))
            
            # Create a client to verify the flow works
            client = s3_access.client()
            
            # Verify boto3 Session was called with the right credentials
            mock_session.assert_called_once_with(
                aws_access_key_id="AKIAEXAMPLE123456789",
                aws_secret_access_key="abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
            )
    
    @patch('boto3.Session')
    def test_integration_with_custom_options(self, mock_session, sample_csv_path):
        """Test integration with S3Access class using custom options."""
        # Setup mock boto3 session
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Generate config file with custom options
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            # Convert CSV to config with custom options
            result_path = csv_to_config(
                csv_path=sample_csv_path,
                output_path=config_path,
                format="json",
                region="us-west-2",
                include_optional=True,
                indent=4,
                endpoint_url="http://localhost:4566"  # LocalStack endpoint
            )
            
            assert result_path.exists()
            
            # Read the generated config file
            config_data = json.loads(config_path.read_text())
            
            # Verify config file contents
            assert config_data["aws_access_key_id"] == "AKIAEXAMPLE123456789"
            assert config_data["aws_secret_access_key"] == "abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
            assert config_data["region_name"] == "us-west-2"
            assert config_data["endpoint_url"] == "http://localhost:4566"
            
            # Try to initialize S3Access with the generated config
            s3_access = S3Access(config_file=str(config_path))
            
            # Create a client to verify the flow works
            client = s3_access.client()
            
            # Verify boto3 Session was called with the right credentials
            mock_session.assert_called_once_with(
                aws_access_key_id="AKIAEXAMPLE123456789",
                aws_secret_access_key="abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
            )
