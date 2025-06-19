"""Tests for the CSV to S3 config converter module."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fence_ai.csv_config import CSVCredentialParser, ConfigGenerator, csv_to_config


@pytest.fixture
def sample_csv_path():
    """Create a temporary CSV file with sample AWS credentials."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        f.write("Access key ID,Secret access key\n")
        f.write("AKIAEXAMPLE123456789,abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE\n")
    
    path = Path(f.name)
    yield path
    path.unlink()


@pytest.fixture
def sample_csv_alt_format_path():
    """Create a temporary CSV file with alternative format AWS credentials."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        f.write("User Name,Access Key Id,Secret Access Key\n")
        f.write("test-user,AKIAEXAMPLE123456789,abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE\n")
    
    path = Path(f.name)
    yield path
    path.unlink()


class TestCSVCredentialParser:
    """Test the CSVCredentialParser class."""
    
    def test_init(self):
        """Test parser initialization."""
        parser = CSVCredentialParser()
        assert parser is not None
    
    def test_header_mappings(self):
        """Test that header mappings are properly defined."""
        parser = CSVCredentialParser()
        
        # Check required mappings exist
        assert "access key id" in parser._HEADER_MAPPINGS
        assert "secret access key" in parser._HEADER_MAPPINGS
        
        # Check mappings point to correct boto3 parameter names
        assert parser._HEADER_MAPPINGS["access key id"] == "aws_access_key_id"
        assert parser._HEADER_MAPPINGS["secret access key"] == "aws_secret_access_key"
        
        # Check optional mappings
        assert "session token" in parser._HEADER_MAPPINGS
        assert parser._HEADER_MAPPINGS["session token"] == "aws_session_token"
        assert "region" in parser._HEADER_MAPPINGS
        assert parser._HEADER_MAPPINGS["region"] == "region_name"
    
    def test_required_fields(self):
        """Test that required fields are properly defined."""
        parser = CSVCredentialParser()
        assert "aws_access_key_id" in parser._REQUIRED_FIELDS
        assert "aws_secret_access_key" in parser._REQUIRED_FIELDS
    
    def test_format_types(self):
        """Test that format types are properly defined."""
        parser = CSVCredentialParser()
        assert "standard" in parser._FORMAT_TYPES
        assert "iam_user" in parser._FORMAT_TYPES
        assert "extended" in parser._FORMAT_TYPES
        assert "simple" in parser._FORMAT_TYPES
    
    def test_detect_format_type(self):
        """Test format type detection from headers."""
        parser = CSVCredentialParser()
        
        # Test standard format
        assert parser._detect_format_type(["Access key ID", "Secret access key"]) == "standard"
        
        # Test IAM user format
        assert parser._detect_format_type(["User Name", "Access key ID", "Secret access key"]) == "iam_user"
        
        # Test extended format
        assert parser._detect_format_type(["Access key ID", "Secret access key", "Session Token"]) == "extended"
        
        # Test simple format
        assert parser._detect_format_type(["Key", "Secret"]) == "simple"
        
        # Test unknown but valid format
        assert parser._detect_format_type(["Column1", "Column2", "Column3"]) == "unknown"
        
        # Test invalid format
        with pytest.raises(ValueError):
            parser._detect_format_type(["Single Column"])
    
    def test_map_headers(self):
        """Test mapping headers to credential field names."""
        parser = CSVCredentialParser()
        
        # Test standard headers
        header_map = parser._map_headers(["Access key ID", "Secret access key"])
        assert header_map == {0: "aws_access_key_id", 1: "aws_secret_access_key"}
        
        # Test extended headers
        header_map = parser._map_headers(["Access key ID", "Secret access key", "Session Token", "Region"])
        assert header_map == {
            0: "aws_access_key_id", 
            1: "aws_secret_access_key",
            2: "aws_session_token",
            3: "region_name"
        }
        
        # Test unrecognized headers in two-column format
        header_map = parser._map_headers(["Key", "Value"])
        assert header_map == {0: "aws_access_key_id", 1: "aws_secret_access_key"}
        
        # Test mixed recognized and unrecognized headers
        header_map = parser._map_headers(["Key", "Secret access key", "Extra"])
        assert header_map == {1: "aws_secret_access_key"}
    
    def test_validate_credentials(self):
        """Test credential validation."""
        parser = CSVCredentialParser()
        
        # Test valid credentials
        valid_creds = {
            "aws_access_key_id": "AKIAEXAMPLE123456789",
            "aws_secret_access_key": "abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
        }
        # Should not raise an exception
        parser._validate_credentials(valid_creds)
        
        # Test missing required field
        invalid_creds = {"aws_access_key_id": "AKIAEXAMPLE123456789"}
        with pytest.raises(ValueError):
            parser._validate_credentials(invalid_creds)
        
        # Test invalid access key format (should log warning but not raise exception)
        invalid_format_creds = {
            "aws_access_key_id": "INVALID123456789",
            "aws_secret_access_key": "abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
        }
        with pytest.warns(UserWarning):
            parser._validate_credentials(invalid_format_creds)


class TestConfigGenerator:
    """Test the ConfigGenerator class."""
    
    def test_init(self):
        """Test generator initialization."""
        generator = ConfigGenerator()
        assert generator is not None
    
    # Additional tests will be implemented as part of Task 5


class TestCSVToConfig:
    """Test the csv_to_config function."""
    
    @patch("fence_ai.csv_config.CSVCredentialParser.parse")
    @patch("fence_ai.csv_config.ConfigGenerator.generate")
    def test_csv_to_config(self, mock_generate, mock_parse, sample_csv_path):
        """Test the csv_to_config function."""
        # Setup mocks
        mock_parse.return_value = {
            "aws_access_key_id": "AKIAEXAMPLE123456789",
            "aws_secret_access_key": "abcdefghijklmnopqrstuvwxyz1234567890EXAMPLE"
        }
        mock_generate.return_value = Path("/tmp/config.json")
        
        # Call function
        output_path = Path("/tmp/config.json")
        result = csv_to_config(sample_csv_path, output_path)
        
        # Verify results
        assert result == output_path
        mock_parse.assert_called_once_with(sample_csv_path)
        mock_generate.assert_called_once()
    
    # Additional tests will be implemented as part of Tasks 3 and 5
