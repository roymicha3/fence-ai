"""Real-world test configuration for Fence AI."""
import sys
import os
import importlib

# Add the parent tests directory to path to access shared fixtures
# But don't import the conftest.py from there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure we're using the real boto3, not the stub
import pytest

@pytest.fixture(scope="session", autouse=True)
def use_real_boto3():
    """Ensure we're using the real boto3 module for real-world tests."""
    # If boto3 is already imported as a stub, remove it
    if 'boto3' in sys.modules:
        del sys.modules['boto3']
    if 'botocore.exceptions' in sys.modules:
        del sys.modules['botocore.exceptions']
    
    # Import the real boto3
    import boto3
    import botocore.exceptions
    
    # Make sure we're using the real boto3
    try:
        # This will fail if we're using the stub
        boto3.Session()
    except TypeError:
        pytest.skip("Real boto3 is required for real-world tests")
