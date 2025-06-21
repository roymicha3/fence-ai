"""Minimal PoC for uploading and downloading files to AWS S3.

Credentials are expected in a CSV file located at ``configs/Server_accessKeys.csv`` with the
header::

    aws_access_key_id,aws_secret_access_key

and a single data row. No additional error handling or custom exceptions are
implemented yet – those will be added once the final design is approved.
"""
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from credentials_loader import load_credentials
from storage_config_loader import load_storage_config

# Default paths (can be overridden)
CSV_PATH = Path("configs/Server_accessKeys.csv")
BUCKET_CFG = load_storage_config("configs/bucket.yaml")

def get_s3_client(config_path: Path | str = CSV_PATH):
    """Return a boto3 S3 client using creds from *config_path* and region from BUCKET_CFG."""
    creds = load_credentials(config_path)
    return boto3.client('s3', region_name=BUCKET_CFG.get('region'), **creds)

def upload_file(local_path: str, bucket: str, key: str):
    """Upload *local_path* to S3 at ``bucket/key`` using fresh credentials."""
    client = get_s3_client()
    client.upload_file(local_path, bucket, key)

def download_file(bucket: str, key: str, dest_path: str):
    """Download ``bucket/key`` from S3 into *dest_path* using fresh credentials."""
    client = get_s3_client()
    client.download_file(bucket, key, dest_path)

def delete_file(bucket: str, key: str):
    """Delete ``bucket/key`` from S3 using fresh credentials."""
    client = get_s3_client()
    client.delete_object(Bucket=bucket, Key=key)

if __name__ == "__main__":
    # Demonstration only – adjust values or comment out when integrating.
    try:
        upload_file("demo.txt", BUCKET_CFG['name'], "demo.txt")
        download_file(BUCKET_CFG['name'], "demo.txt", "downloaded_demo.txt")
        delete_file(BUCKET_CFG['name'], "demo.txt")
        print("Upload, download, and delete completed successfully.")
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")
