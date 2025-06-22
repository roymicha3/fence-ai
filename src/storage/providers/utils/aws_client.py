"""S3 client providing upload/download/delete using per-call connections.

Each method opens an S3Connection, performs the action, then closes it.
This keeps caller code minimal while ensuring connections aren't reused
beyond the scope of a single operation.
"""
from __future__ import annotations

from pathlib import Path

from storage.providers.utils.aws_conn import S3Connection
from storage.creds.credentials_loader import load_credentials
from storage.config.storage_config_loader import load_storage_config


class S3Client:
    """High-level helper that reuses configured credential + config paths."""

    def __init__(
        self,
        cred_src: str | Path = "creds/Server_accessKeys.csv",
        cfg_src: str | Path = "configs/bucket.yaml",
    ) -> None:
                # Load once at construction time
        self._creds = load_credentials(cred_src)
        cfg = load_storage_config(cfg_src)
        self._region = cfg.get("region")
        self._bucket_default = cfg.get("name")

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
