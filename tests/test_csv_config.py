"""Tests for the CSV to S3 config converter module."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

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
    
    # Additional tests will be implemented as part of Task 3


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
