"""High-level helpers for S3 data operations (storage package)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fence_ai.core.logger import get_logger
from .s3_access import S3Access, S3AccessError

__all__ = [
    "S3UploadError",
    "S3DownloadError",
    "S3ListError",
    "S3DeleteError",
    "S3DataManager",
]


class S3UploadError(RuntimeError):
    """Raised when a file upload to S3 fails."""


class S3DownloadError(RuntimeError):
    """Raised when an S3 download fails."""


class S3ListError(RuntimeError):
    """Raised when listing S3 objects fails."""


class S3DeleteError(RuntimeError):
    """Raised when deleting an S3 object fails."""


logger = get_logger(__name__)


class S3DataManager:
    """Convenience wrapper that exposes higher-level S3 operations."""

    def __init__(self, s3_access: Optional[S3Access] = None) -> None:
        self._access = s3_access or S3Access()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upload(self, bucket: str, key: str, file_path: str | Path, **extra_args: Any) -> None:
        logger.info("Uploading %s to s3://%s/%s", file_path, bucket, key)
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(file_path)
        try:
            client = self._access.client()
        except S3AccessError as exc:
            logger.exception("S3 client initialisation failed")
            raise S3UploadError("Failed to initialise S3 client") from exc
        try:
            client.upload_file(str(path), bucket, key, ExtraArgs=extra_args or None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Upload failed")
            raise S3UploadError(f"Failed to upload {path} to s3://{bucket}/{key}") from exc

    def download(self, bucket: str, key: str, local_path: str | Path) -> Path:
        logger.info("Downloading s3://%s/%s to %s", bucket, key, local_path)
        dst = Path(local_path)
        if not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            client = self._access.client()
        except S3AccessError as exc:
            logger.exception("S3 client initialisation failed")
            raise S3DownloadError("Failed to initialise S3 client") from exc
        try:
            client.download_file(bucket, key, str(dst))
            return dst
        except Exception as exc:  # noqa: BLE001
            logger.exception("Download failed")
            raise S3DownloadError(f"Failed to download s3://{bucket}/{key} to {dst}") from exc

    def delete(self, bucket: str, key: str) -> None:
        logger.info("Deleting s3://%s/%s", bucket, key)
        try:
            client = self._access.client()
        except S3AccessError as exc:
            logger.exception("S3 client initialisation failed")
            raise S3DeleteError("Failed to initialise S3 client") from exc
        try:
            client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Delete failed")
            raise S3DeleteError(f"Failed to delete s3://{bucket}/{key}") from exc

    def list_objects(self, bucket: str, prefix: str | None = None) -> list[str]:
        logger.info("Listing objects in %s with prefix=%s", bucket, prefix)
        try:
            client = self._access.client()
        except S3AccessError as exc:
            logger.exception("S3 client initialisation failed")
            raise S3ListError("Failed to initialise S3 client") from exc
        try:
            paginator = client.get_paginator("list_objects_v2") if hasattr(client, "get_paginator") else None
            if paginator:
                pages = paginator.paginate(Bucket=bucket, Prefix=prefix or "")
                keys: list[str] = []
                for page in pages:
                    keys.extend(obj["Key"] for obj in page.get("Contents", []))
                return keys
            resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix or "")
            return [obj["Key"] for obj in resp.get("Contents", [])]
        except Exception as exc:  # noqa: BLE001
            logger.exception("List objects failed")
            raise S3ListError(f"Failed to list objects in bucket {bucket}") from exc
