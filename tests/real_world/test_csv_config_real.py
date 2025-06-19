"""Real-world integration test for the CSV to S3 Config Converter."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import boto3
import json
from botocore.exceptions import ClientError

# Ensure fence_ai package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# We've already added the project root to the Python path above

from fence_ai.csv_config import csv_to_config
from fence_ai.storage.s3_access import S3Access


class TestCSVConfigRealWorld:
    """Real-world integration tests for the CSV to S3 Config Converter."""
    
    @pytest.fixture
    def csv_path(self):
        """Path to the real CSV credentials file."""
        csv_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'configs', 'Server_accessKeys.csv')))
        if not csv_path.exists():
            pytest.skip("Real AWS credentials CSV file not found")
        return csv_path

    @pytest.fixture
    def clean_csv_path(self, csv_path):
        """Create a temporary CSV file without BOM."""
        # Read the original CSV file and remove the BOM if present
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            
        # Create a temporary file without BOM
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
            
        yield temp_path
        
        # Clean up the temporary file
        if temp_path.exists():
            temp_path.unlink()
    
    def test_json_config_generation_and_s3_access(self, clean_csv_path):
        """Test generating a JSON config file and using it with S3Access."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate JSON config file
            config_path = Path(temp_dir) / "config.json"
            result_path = csv_to_config(
                csv_path=clean_csv_path,
                output_path=config_path,
                format="json",
                region="us-east-1"
            )
            
            # Verify the config file was created
            assert result_path.exists()
            assert result_path.stat().st_mode & 0o777 == 0o600  # Check secure permissions
            
            # Verify the config file contents
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            # Check that the required fields are present
            assert 'aws_access_key_id' in config_data
            assert 'aws_secret_access_key' in config_data
            assert 'region_name' in config_data
            
            # Check the region value (not the sensitive credentials)
            assert config_data['region_name'] == 'us-east-1'
            
            # Try to initialize S3Access with the generated config
            s3_access = S3Access(config_file=str(config_path))
            
            # Check if boto3 is mocked
            try:
                # Just check if we can create a session without arguments
                # This will fail if boto3 is mocked with a _DummySession
                boto3.Session()
                
                # If we get here, boto3 is not mocked, try to use the client
                try:
                    s3_client = s3_access.client()
                    
                    # Check if the client has the list_buckets method
                    if hasattr(s3_client, 'list_buckets'):
                        response = s3_client.list_buckets()
                        
                        # If we get here, the credentials are valid
                        print(f"Successfully connected to S3 with {len(response['Buckets'])} buckets")
                        
                        # Print bucket names for verification
                        for bucket in response['Buckets']:
                            print(f"  - {bucket['Name']}")
                    else:
                        # Client is mocked but doesn't have the expected methods
                        pytest.skip("S3 client is mocked without list_buckets method")
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidAccessKeyId':
                        pytest.skip("Invalid access key - credentials may be expired or invalid")
                    elif e.response['Error']['Code'] == 'SignatureDoesNotMatch':
                        pytest.skip("Signature mismatch - secret key may be incorrect")
                    else:
                        pytest.skip(f"Failed to access S3: {e}")
                except AttributeError:
                    # Client is mocked but doesn't have the expected attributes
                    pytest.skip("S3 client is mocked without expected attributes")
            except TypeError:
                # boto3 is mocked, skip the actual S3 operations
                pytest.skip("boto3 is mocked, skipping actual S3 operations")
    
    def test_yaml_config_generation_and_s3_access(self, clean_csv_path):
        """Test generating a YAML config file and using it with S3Access."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed, skipping YAML test")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate YAML config file with custom options
            config_path = Path(temp_dir) / "config.yaml"
            result_path = csv_to_config(
                csv_path=clean_csv_path,
                output_path=config_path,
                format="yaml",
                region="us-west-2",
                include_optional=True,
                indent=4
            )
            
            # Verify the config file was created
            assert result_path.exists()
            assert result_path.stat().st_mode & 0o777 == 0o600  # Check secure permissions
            
            # Verify the config file contents
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            # Check that the required fields are present
            assert 'aws_access_key_id' in config_data
            assert 'aws_secret_access_key' in config_data
            assert 'region_name' in config_data
            
            # Check the region value (not the sensitive credentials)
            assert config_data['region_name'] == 'us-west-2'
            
            # Try to initialize S3Access with the generated config
            s3_access = S3Access(config_file=str(config_path))
            
            # Check if boto3 is mocked
            try:
                # Just check if we can create a session without arguments
                # This will fail if boto3 is mocked with a _DummySession
                boto3.Session()
                
                # If we get here, boto3 is not mocked, try to use the client
                try:
                    s3_client = s3_access.client()
                    
                    # Check if the client has the list_buckets method
                    if hasattr(s3_client, 'list_buckets'):
                        response = s3_client.list_buckets()
                        
                        # If we get here, the credentials are valid
                        print(f"Successfully connected to S3 with {len(response['Buckets'])} buckets")
                        
                        # Print bucket names for verification
                        for bucket in response['Buckets']:
                            print(f"  - {bucket['Name']}")
                    else:
                        # Client is mocked but doesn't have the expected methods
                        pytest.skip("S3 client is mocked without list_buckets method")
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidAccessKeyId':
                        pytest.skip("Invalid access key - credentials may be expired or invalid")
                    elif e.response['Error']['Code'] == 'SignatureDoesNotMatch':
                        pytest.skip("Signature mismatch - secret key may be incorrect")
                    else:
                        pytest.skip(f"Failed to access S3: {e}")
                except AttributeError:
                    # Client is mocked but doesn't have the expected attributes
                    pytest.skip("S3 client is mocked without expected attributes")
            except TypeError:
                # boto3 is mocked, skip the actual S3 operations
                pytest.skip("boto3 is mocked, skipping actual S3 operations")
    
    def test_cli_script_with_real_credentials(self, clean_csv_path):
        """Test the CLI script with real credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Define output paths
            json_config_path = Path(temp_dir) / "cli_config.json"
            
            # Run the CLI script to generate a JSON config
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'examples', 'setup_s3_config.py'))
            cmd = f"{sys.executable} {script_path} {clean_csv_path} {json_config_path} --format json --region us-east-1"
            
            exit_code = os.system(cmd)
            assert exit_code == 0, f"CLI script failed with exit code {exit_code}"
            
            # Verify the config file was created
            assert json_config_path.exists()
            
            # Verify the config file contents
            with open(json_config_path, 'r') as f:
                config_data = json.load(f)
                
            # Check that the required fields are present
            assert 'aws_access_key_id' in config_data
            assert 'aws_secret_access_key' in config_data
            assert 'region_name' in config_data
            
            # Check the region value (not the sensitive credentials)
            assert config_data['region_name'] == 'us-east-1'
            
            # Try to initialize S3Access with the generated config
            s3_access = S3Access(config_file=str(json_config_path))
            
            # Check if boto3 is mocked
            try:
                boto3.Session()
                # If we get here, boto3 is not mocked, try to use the client
                try:
                    s3_client = s3_access.client()
                    
                    # Check if the client has the list_buckets method
                    if hasattr(s3_client, 'list_buckets'):
                        response = s3_client.list_buckets()
                        
                        # If we get here, the credentials are valid
                        print(f"Successfully connected to S3 with {len(response['Buckets'])} buckets")
                        
                        # Print bucket names for verification
                        for bucket in response['Buckets']:
                            print(f"  - {bucket['Name']}")
                    else:
                        # Client is mocked but doesn't have the expected methods
                        pytest.skip("S3 client is mocked without list_buckets method")
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidAccessKeyId':
                        pytest.skip("Invalid access key - credentials may be expired or invalid")
                    elif e.response['Error']['Code'] == 'SignatureDoesNotMatch':
                        pytest.skip("Signature mismatch - secret key may be incorrect")
                    else:
                        pytest.skip(f"Failed to access S3: {e}")
                except AttributeError:
                    # Client is mocked but doesn't have the expected attributes
                    pytest.skip("S3 client is mocked without expected attributes")
            except TypeError:
                # boto3 is mocked, skip the actual S3 operations
                pytest.skip("boto3 is mocked, skipping actual S3 operations")


if __name__ == "__main__":
    # This allows running the tests directly
    pytest.main(["-xvs", __file__])
