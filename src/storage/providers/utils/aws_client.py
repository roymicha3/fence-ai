"""S3 client providing upload/download/delete using per-call connections.

Each method opens an S3Connection, performs the action, then closes it.
This keeps caller code minimal while ensuring connections aren't reused
beyond the scope of a single operation.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

import dotenv
from omegaconf import DictConfig

from storage.providers.utils.aws_conn import S3Connection


class S3Client:
    """High-level helper that reuses configured credential + config paths."""

    def __init__(
        self,
        env_file: str | Path = ".env",
        config: Optional[DictConfig] = None
    ) -> None:
        # Load environment variables from .env file
        env_path = Path(env_file)
        if env_path.exists():
            dotenv.load_dotenv(env_path)
        else:
            dotenv.load_dotenv()
            
        # Get AWS credentials directly from environment
        self._creds = {
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        }
        
        # Get storage configuration from provided config
        if config is None:
            raise ValueError("S3 configuration is required")
            
        self._region = config.get("region")
        self._bucket_default = config.get("name")

    # ------------------------------------------------------------------
    def upload_file(self, local_path: str | Path, bucket: str, key: str) -> None:
        with S3Connection(self._creds, self._region) as conn:
            conn.client.upload_file(str(local_path), bucket, key)

    def download_file(self, bucket: str, key: str, dest_path: str | Path):
        with S3Connection(self._creds, self._region) as conn:
            conn.client.download_file(bucket, key, str(dest_path))

    def delete_file(self, bucket: str, key: str):
        with S3Connection(self._creds, self._region) as conn:
            conn.client.delete_object(Bucket=bucket, Key=key)
