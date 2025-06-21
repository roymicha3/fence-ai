"""S3 implementation of the generic StorageBackend interface."""
from __future__ import annotations

from pathlib import Path

from storage.providers.utils.aws_client import S3Client
from storage.base import StorageBackend


class S3Backend(StorageBackend):
    """StorageBackend backed by our existing :class:`S3Client`."""

    def __init__(
        self,
        cred_src: str | Path = "configs/Server_accessKeys.csv",
        cfg_src: str | Path = "configs/bucket.yaml",
    ) -> None:
        self._client = S3Client(cred_src=cred_src, cfg_src=cfg_src)
        # default bucket from the YAML config (private attr but acceptable for PoC)
        self._bucket = self._client._bucket_default  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    def upload_file(self, local_path: Path, remote_key: str) -> None:
        self._client.upload_file(local_path, self._bucket, remote_key)

    def download_file(self, remote_key: str, dest_path: Path) -> None:
        self._client.download_file(self._bucket, remote_key, dest_path)

    def delete_file(self, remote_key: str) -> None:
        self._client.delete_file(self._bucket, remote_key)
