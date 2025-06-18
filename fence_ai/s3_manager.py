"""High-level helpers for S3 data operations.

Currently provides *upload* functionality built on top of :class:`fence_ai.S3Access`.
Designed so that the low-level authentication/initialisation remains encapsulated
in ``S3Access`` while this module focuses on business-level operations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

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
class S3DataManager:
    """Convenience wrapper that exposes higher-level S3 operations.

    Parameters
    ----------
    s3_access : Optional[S3Access]
        If *None*, a default :class:`S3Access` instance is created with its
        default environment-based credential resolution.
    """

    def __init__(self, s3_access: Optional[S3Access] = None) -> None:
        self._access = s3_access or S3Access()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upload(self, bucket: str, key: str, file_path: str | Path, **extra_args: Any) -> None:
        """Upload *file_path* to *bucket*/*key*.

        Parameters
        ----------
        bucket : str
            Destination S3 bucket name.
        key : str
            Destination object key inside the bucket.
        file_path : str | pathlib.Path
            Local filesystem path to the file to upload.
        **extra_args
            Forwarded to ``boto3.S3.Client.upload_file`` (e.g. ``ExtraArgs`` for
            ACL, content-type, etc.).

        Raises
        ------
        S3UploadError
            If the upload fails for any reason including credential or client
            errors.
        FileNotFoundError
            If *file_path* does not exist.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(file_path)

        # Lazily acquire client on every call to make life easier for tests and
        # to ensure credentials are always fresh (e.g. when using STS tokens).
        try:
            client = self._access.client()
        except S3AccessError as exc:  # re-wrap for clearer context
            raise S3UploadError("Failed to initialise S3 client") from exc

        try:
            client.upload_file(str(path), bucket, key, ExtraArgs=extra_args or None)
        except Exception as exc:  # noqa: BLE001 – we re-raise as our domain error
            raise S3UploadError(f"Failed to upload {path} to s3://{bucket}/{key}") from exc

    def download(self, bucket: str, key: str, local_path: str | Path) -> Path:
        """Download *bucket*/*key* to *local_path*.

        Returns the pathlib.Path to the downloaded file.
        """
        dst = Path(local_path)
        # Ensure destination directory exists
        if not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            client = self._access.client()
        except S3AccessError as exc:
            raise S3DownloadError("Failed to initialise S3 client") from exc

        try:
            client.download_file(bucket, key, str(dst))
            return dst
        except Exception as exc:  # noqa: BLE001
            raise S3DownloadError(f"Failed to download s3://{bucket}/{key} to {dst}") from exc

    def delete(self, bucket: str, key: str) -> None:
        """Delete the object at *bucket*/*key*.

        Parameters
        ----------
        bucket : str
            S3 bucket name.
        key : str
            Object key to delete.

        Raises
        ------
        S3DeleteError
            If the delete operation fails for any reason including credential
            or client errors.
        """
        try:
            client = self._access.client()
        except S3AccessError as exc:
            raise S3DeleteError("Failed to initialise S3 client") from exc

        try:
            client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            raise S3DeleteError(f"Failed to delete s3://{bucket}/{key}") from exc

    def list_objects(self, bucket: str, prefix: str | None = None) -> list[str]:
        """Return a list of object keys in *bucket* starting with *prefix* (if given)."""
        try:
            client = self._access.client()
        except S3AccessError as exc:
            raise S3ListError("Failed to initialise S3 client") from exc

        try:
            paginator = client.get_paginator("list_objects_v2") if hasattr(client, "get_paginator") else None
            if paginator:
                pages = paginator.paginate(Bucket=bucket, Prefix=prefix or "")
                keys: list[str] = []
                for page in pages:
                    keys.extend(obj["Key"] for obj in page.get("Contents", []))
                return keys
            # fallback single call
            resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix or "")
            return [obj["Key"] for obj in resp.get("Contents", [])]
        except Exception as exc:  # noqa: BLE001
            raise S3ListError(f"Failed to list objects in bucket {bucket}") from exc
