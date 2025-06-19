"""CSV to S3 Config Converter for Fence AI.

Provides functionality to convert AWS CSV credential files to configuration files
compatible with the Fence AI S3 access system. This allows users to easily import
AWS credentials from standard CSV exports and use them with the Fence AI library.

The module supports different CSV formats and can generate both JSON and YAML
configuration files with appropriate permissions.
"""

from __future__ import annotations

import csv
import json
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    _HAS_YAML = False

from fence_ai.core.logger import get_logger

__all__ = ["CSVCredentialParser", "ConfigGenerator", "csv_to_config"]

logger = get_logger(__name__)


class CSVCredentialParser:
    """Parser for AWS CSV credential files.
    
    Handles different CSV formats and extracts credential information.
    """
    
    # Common header variations in AWS CSV credential files
    # Maps CSV column headers (lowercase) to boto3 credential parameter names
    _HEADER_MAPPINGS = {
        # Access Key ID variations
        "access key id": "aws_access_key_id",
        "access key": "aws_access_key_id",
        "accesskeyid": "aws_access_key_id",
        "aws access key id": "aws_access_key_id",
        "aws_access_key_id": "aws_access_key_id",
        "access_key_id": "aws_access_key_id",
        "accesskey": "aws_access_key_id",
        "key id": "aws_access_key_id",
        "id": "aws_access_key_id",  # For simple two-column formats
        
        # Secret Access Key variations
        "secret access key": "aws_secret_access_key",
        "secret key": "aws_secret_access_key",
        "secretaccesskey": "aws_secret_access_key",
        "aws secret access key": "aws_secret_access_key",
        "aws_secret_access_key": "aws_secret_access_key",
        "secret_access_key": "aws_secret_access_key",
        "secretkey": "aws_secret_access_key",
        "secret": "aws_secret_access_key",  # For simple two-column formats
        
        # Session Token variations (optional)
        "session token": "aws_session_token",
        "security token": "aws_session_token",
        "aws session token": "aws_session_token",
        "aws_session_token": "aws_session_token",
        "sessiontoken": "aws_session_token",
        "token": "aws_session_token",
        
        # Region variations (optional)
        "region": "region_name",
        "aws region": "region_name",
        "region name": "region_name",
        "region_name": "region_name",
        
        # Other fields that might be in CSV but aren't used for credentials
        "user name": None,
        "username": None,
        "user": None,
        "iam user": None,
        "arn": None,
        "account id": None,
        "account": None,
        "console login link": None
    }
    
    # Required credential fields
    _REQUIRED_FIELDS = ["aws_access_key_id", "aws_secret_access_key"]
    
    # Optional credential fields
    _OPTIONAL_FIELDS = ["aws_session_token", "region_name"]
    
    # CSV format types we support
    _FORMAT_TYPES = {
        "standard": "Standard AWS CSV with 'Access key ID' and 'Secret access key' columns",
        "iam_user": "IAM User CSV with username and credentials",
        "extended": "Extended format with additional fields like region, token, etc.",
        "simple": "Simple two-column format with keys and secrets"
    }
    
    def __init__(self) -> None:
        """Initialize the CSV credential parser."""
        pass
    
    def parse(self, csv_path: str | Path) -> Dict[str, Any]:
        """Parse AWS CSV credential file into a structured dictionary.
        
        Parameters
        ----------
        csv_path : str | Path
            Path to the CSV file containing AWS credentials.
            
        Returns
        -------
        Dict[str, Any]
            Dictionary with normalized credential keys.
            
        Raises
        ------
        FileNotFoundError
            If the CSV file does not exist.
        ValueError
            If the CSV file format is invalid or missing required fields.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        
        logger.debug("Parsing CSV credentials from %s", path)
        
        try:
            # First, detect the CSV format and extract headers
            with path.open("r", encoding="utf-8") as f:
                # Read a small sample to detect dialect
                sample = f.read(4096)
                f.seek(0)
                
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
                
                if not has_header:
                    raise ValueError("CSV file must have headers")
                
                reader = csv.reader(f, dialect)
                headers = next(reader)
                
                # Get the first data row if it exists
                try:
                    first_row = next(reader)
                except StopIteration:
                    raise ValueError("CSV file contains headers but no data")
                
                # Detect format type
                format_type = self._detect_format_type(headers)
                logger.debug("Detected CSV format: %s", format_type)
                
                # Map headers to credential keys
                header_map = self._map_headers(headers)
                
                # Extract credentials from the first row
                credentials = self._extract_credentials(header_map, first_row)
                
                # Validate required fields
                self._validate_credentials(credentials)
                
                return credentials
                
        except csv.Error as e:
            raise ValueError(f"Invalid CSV format: {e}")
    
    def _detect_format_type(self, headers: List[str]) -> str:
        """Detect the CSV format type based on headers.
        
        Parameters
        ----------
        headers : List[str]
            List of header strings from the CSV file.
            
        Returns
        -------
        str
            Format type identifier.
        """
        headers_lower = [h.lower() for h in headers]
        
        # Check for IAM user format (has username column)
        if any(h in ["user name", "username", "user", "iam user"] for h in headers_lower):
            return "iam_user"
        
        # Check for extended format (has additional fields beyond key and secret)
        if any(h in ["session token", "token", "region"] for h in headers_lower):
            return "extended"
        
        # Check for standard format (exactly Access key ID and Secret access key)
        if len(headers) == 2 and "access" in headers_lower[0] and "secret" in headers_lower[1]:
            return "standard"
        
        # Default to simple format
        if len(headers) == 2:
            return "simple"
        
        # If we can't determine the format but there are at least two columns,
        # we'll try to extract credentials anyway
        if len(headers) >= 2:
            return "unknown"
        
        raise ValueError("CSV format not recognized. Must have at least Access Key ID and Secret Access Key columns.")
    
    def _map_headers(self, headers: List[str]) -> Dict[int, str]:
        """Map CSV headers to credential field names.
        
        Parameters
        ----------
        headers : List[str]
            List of header strings from the CSV file.
            
        Returns
        -------
        Dict[int, str]
            Mapping of column indices to credential field names.
        """
        header_map = {}
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if header_lower in self._HEADER_MAPPINGS:
                mapped_name = self._HEADER_MAPPINGS[header_lower]
                if mapped_name is not None:  # Skip fields mapped to None
                    header_map[i] = mapped_name
        
        # For simple two-column format with unrecognized headers
        if len(headers) == 2 and len(header_map) == 0:
            logger.warning("Unrecognized headers in two-column CSV, assuming [access_key_id, secret_access_key]")
            header_map = {0: "aws_access_key_id", 1: "aws_secret_access_key"}
        
        return header_map
    
    def _extract_credentials(self, header_map: Dict[int, str], row: List[str]) -> Dict[str, Any]:
        """Extract credential values from a CSV row.
        
        Parameters
        ----------
        header_map : Dict[int, str]
            Mapping of column indices to credential field names.
        row : List[str]
            List of values from a CSV row.
            
        Returns
        -------
        Dict[str, Any]
            Dictionary of credential values.
        """
        credentials = {}
        
        for i, field_name in header_map.items():
            if i < len(row) and row[i]:  # Check index bounds and non-empty value
                credentials[field_name] = row[i]
        
        return credentials
    
    def _validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """Validate that required credential fields are present.
        
        Parameters
        ----------
        credentials : Dict[str, Any]
            Dictionary of credential values.
            
        Raises
        ------
        ValueError
            If required fields are missing.
        """
        missing = [field for field in self._REQUIRED_FIELDS if field not in credentials]
        if missing:
            raise ValueError(f"Missing required credential fields: {', '.join(missing)}")
        
        # Basic format validation for access key ID (starts with 'AKIA' or 'ASIA')
        access_key = credentials.get("aws_access_key_id", "")
        if not (access_key.startswith("AKIA") or access_key.startswith("ASIA")):
            warning_msg = "Access key ID may be invalid (doesn't start with AKIA or ASIA)"
            logger.warning(warning_msg)
            warnings.warn(warning_msg)


class ConfigGenerator:
    """Generator for S3 config files from parsed credentials.
    
    Supports both JSON and YAML output formats.
    """
    
    def __init__(self) -> None:
        """Initialize the config generator."""
        pass
    
    def generate(
        self, 
        credentials: Dict[str, Any], 
        output_path: str | Path, 
        format: str = "json",
        region: str = "us-east-1",
        **kwargs: Any
    ) -> Path:
        """Generate a config file from parsed credentials.
        
        Parameters
        ----------
        credentials : Dict[str, Any]
            Parsed credentials dictionary.
        output_path : str | Path
            Path where the config file will be written.
        format : str, optional
            Output format, either "json" or "yaml". Default is "json".
        region : str, optional
            AWS region to use. Default is "us-east-1".
        **kwargs : Any
            Additional parameters to include in the config.
            
        Returns
        -------
        Path
            Path to the generated config file.
            
        Raises
        ------
        ValueError
            If the format is not supported or credentials are invalid.
        """
        # Implementation will be added in Task 5
        logger.debug("Generating %s config at %s", format, output_path)
        return Path(output_path)


def csv_to_config(
    csv_path: str | Path, 
    output_path: str | Path, 
    format: str = "json",
    region: str = "us-east-1",
    **kwargs: Any
) -> Path:
    """Convert AWS CSV credentials to a config file.
    
    Parameters
    ----------
    csv_path : str | Path
        Path to the CSV file containing AWS credentials.
    output_path : str | Path
        Path where the config file will be written.
    format : str, optional
        Output format, either "json" or "yaml". Default is "json".
    region : str, optional
        AWS region to use. Default is "us-east-1".
    **kwargs : Any
        Additional parameters to include in the config.
        
    Returns
    -------
    Path
        Path to the generated config file.
        
    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If the CSV format is invalid or the output format is not supported.
    """
    parser = CSVCredentialParser()
    generator = ConfigGenerator()
    
    credentials = parser.parse(csv_path)
    return generator.generate(
        credentials, 
        output_path, 
        format=format,
        region=region,
        **kwargs
    )
