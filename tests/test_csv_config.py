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
import fence_ai.csv_config as csv_config
from fence_ai.csv_config import CSVCredentialParser, ConfigGenerator, csv_to_config

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


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
    """Tests for the ConfigGenerator class."""
    
    def test_init(self):
        """Test ConfigGenerator initialization."""
        # Test default initialization
        generator = csv_config.ConfigGenerator()
        assert generator is not None
        assert generator.include_optional is True
        assert generator.indent == 2
        
        # Test custom initialization
        generator = csv_config.ConfigGenerator(include_optional=False, indent=4)
        assert generator.include_optional is False
        assert generator.indent == 4
    
    def test_validate_credentials(self, tmp_path):
        """Test credential validation."""
        generator = csv_config.ConfigGenerator()
        
        # Valid credentials
        valid_creds = {
            "aws_access_key_id": "AKIAEXAMPLE",
            "aws_secret_access_key": "secret"
        }
        # This should not raise an exception
        generator._validate_credentials(valid_creds)
        
        # Invalid credentials - missing access key
        invalid_creds = {"aws_secret_access_key": "secret"}
        with pytest.raises(ValueError, match="Missing required credential fields"):
            generator._validate_credentials(invalid_creds)
        
        # Invalid credentials - missing secret key
        invalid_creds = {"aws_access_key_id": "AKIAEXAMPLE"}
        with pytest.raises(ValueError, match="Missing required credential fields"):
            generator._validate_credentials(invalid_creds)
    
    def test_prepare_config_data(self):
        """Test preparation of config data."""
        generator = csv_config.ConfigGenerator()
        
        # Test with minimal credentials
        creds = {
            "aws_access_key_id": "AKIAEXAMPLE",
            "aws_secret_access_key": "secret"
        }
        config_data = generator._prepare_config_data(creds, "us-west-2")
        assert config_data["aws_access_key_id"] == "AKIAEXAMPLE"
        assert config_data["aws_secret_access_key"] == "secret"
        assert config_data["region_name"] == "us-west-2"
        
        # Test with optional fields
        creds["aws_session_token"] = "token123"
        config_data = generator._prepare_config_data(creds, "us-east-1")
        assert config_data["aws_session_token"] == "token123"
        
        # Test with additional kwargs
        config_data = generator._prepare_config_data(creds, "us-east-1", endpoint_url="http://localhost:4566")
        assert config_data["endpoint_url"] == "http://localhost:4566"
        
        # Test with include_optional=False
        generator = csv_config.ConfigGenerator(include_optional=False)
        config_data = generator._prepare_config_data(creds, "us-east-1")
        assert "aws_session_token" not in config_data
        assert "region_name" not in config_data
        
        # Test with include_optional=False but explicit kwargs
        config_data = generator._prepare_config_data(creds, "us-east-1", region_name="eu-west-1")
        assert "region_name" in config_data
        assert config_data["region_name"] == "eu-west-1"
    
    def test_generate_json(self, tmp_path):
        """Test JSON config file generation."""
        # Test with default indent
        generator = csv_config.ConfigGenerator()
        config_data = {
            "aws_access_key_id": "AKIAEXAMPLE",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1"
        }
        
        output_path = tmp_path / "config.json"
        generator._generate_json(config_data, output_path)
        
        # Verify the file exists and has the correct content
        assert output_path.exists()
        loaded_data = json.loads(output_path.read_text())
        assert loaded_data == config_data
        
        # Test with custom indent
        generator = csv_config.ConfigGenerator(indent=4)
        output_path = tmp_path / "config_indent4.json"
        generator._generate_json(config_data, output_path)
        
        # Verify the file exists and has the correct content
        assert output_path.exists()
        loaded_data = json.loads(output_path.read_text())
        assert loaded_data == config_data
        
        # Check that the file content has the correct indentation
        file_content = output_path.read_text()
        assert '    "' in file_content  # 4-space indentation
    
    @pytest.mark.skipif(not csv_config._HAS_YAML, reason="PyYAML not installed")
    def test_generate_yaml(self, tmp_path):
        """Test YAML config file generation."""
        # Test with default indent
        generator = csv_config.ConfigGenerator()
        config_data = {
            "aws_access_key_id": "AKIAEXAMPLE",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1"
        }
        
        output_path = tmp_path / "config.yaml"
        generator._generate_yaml(config_data, output_path)
        
        # Verify the file exists and has the correct content
        assert output_path.exists()
        with open(output_path, "r") as f:
            loaded_data = yaml.safe_load(f)
        assert loaded_data == config_data
        
        # Test with custom indent
        generator = csv_config.ConfigGenerator(indent=4)
        output_path = tmp_path / "config_indent4.yaml"
        generator._generate_yaml(config_data, output_path)
        
        # Verify the file exists and has the correct content
        assert output_path.exists()
        with open(output_path, "r") as f:
            loaded_data = yaml.safe_load(f)
        assert loaded_data == config_data
        
        # Check indentation in the raw file content
        file_content = output_path.read_text()
        # In YAML, indentation matters for nested structures
        # We'd need a nested structure to properly test indentation
        nested_data = {
            "aws": {
                "credentials": {
                    "aws_access_key_id": "AKIAEXAMPLE",
                    "aws_secret_access_key": "secret"
                }
            }
        }
        nested_output_path = tmp_path / "nested_config.yaml"
        generator._generate_yaml(nested_data, nested_output_path)
        nested_content = nested_output_path.read_text()
        # Check for 4-space indentation
        assert "    credentials:" in nested_content
    
    def test_generate(self, tmp_path):
        """Test the main generate method."""
        generator = csv_config.ConfigGenerator()
        credentials = {
            "aws_access_key_id": "AKIAEXAMPLE",
            "aws_secret_access_key": "secret"
        }
        
        # Test JSON generation with default options
        json_path = tmp_path / "config.json"
        result = generator.generate(
            credentials=credentials,
            output_path=json_path,
            format="json",
            region="us-west-2"
        )
        
        assert result == json_path
        assert json_path.exists()
        loaded_data = json.loads(json_path.read_text())
        assert loaded_data["aws_access_key_id"] == "AKIAEXAMPLE"
        assert loaded_data["region_name"] == "us-west-2"
        
        # Test with custom indent
        json_path_indent4 = tmp_path / "config_indent4.json"
        result = generator.generate(
            credentials=credentials,
            output_path=json_path_indent4,
            format="json",
            region="us-west-2",
            indent=4
        )
        
        assert result == json_path_indent4
        assert json_path_indent4.exists()
        file_content = json_path_indent4.read_text()
        assert '    "' in file_content  # 4-space indentation
        
        # Test with include_optional=False
        json_path_no_optional = tmp_path / "config_no_optional.json"
        result = generator.generate(
            credentials=credentials,
            output_path=json_path_no_optional,
            format="json",
            region="us-west-2",
            include_optional=False
        )
        
        assert result == json_path_no_optional
        assert json_path_no_optional.exists()
        loaded_data = json.loads(json_path_no_optional.read_text())
        assert "region_name" not in loaded_data
        
        # Test with invalid format
        with pytest.raises(ValueError, match="Unsupported format"):
            generator.generate(
                credentials=credentials,
                output_path=tmp_path / "invalid.txt",
                format="txt"
            )


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
