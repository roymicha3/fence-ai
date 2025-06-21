"""Minimal PoC for uploading and downloading files to AWS S3.

Credentials are expected in a CSV file located at ``configs/Server_accessKeys.csv`` with the
header::

    aws_access_key_id,aws_secret_access_key

and a single data row. No additional error handling or custom exceptions are
implemented yet – those will be added once the final design is approved.
"""
from pathlib import Path
import csv
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from credentials_loader import load_credentials

# Path to the credentials CSV (adjust if necessary)
CSV_PATH = Path("configs/Server_accessKeys.csv")  # default

def get_s3_client(config_path: Path | str = CSV_PATH):
    """Return a boto3 S3 client configured with credentials from *csv_path*."""
    creds = load_credentials(config_path)
    return boto3.client('s3', **creds)

def upload_file(local_path: str, bucket: str, key: str):
    """Upload *local_path* to S3 at ``bucket/key`` using fresh credentials."""
    client = get_s3_client()
    client.upload_file(local_path, bucket, key)

def download_file(bucket: str, key: str, dest_path: str):
    """Download ``bucket/key`` from S3 into *dest_path* using fresh credentials."""
    client = get_s3_client()
    client.download_file(bucket, key, dest_path)

if __name__ == "__main__":
    # Demonstration only – adjust values or comment out when integrating.
    try:
        upload_file("demo.txt", "fence-ai", "demo.txt")
        download_file("fence-ai", "demo.txt", "downloaded_demo.txt")
        print("Upload and download completed successfully.")
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")
