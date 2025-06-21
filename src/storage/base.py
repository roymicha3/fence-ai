"""Abstract interface for storage backends.

All concrete providers (S3, Google-Drive, local filesystem, etc.) must inherit
from :class:`StorageBackend` and implement its abstract methods. The interface
is intentionally minimal to remain easy to implement while covering the common
object-storage use-cases.
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Iterable


class StorageBackend(abc.ABC):
    """Uniform API for object-storage providers."""

    # ---------------------------- core object ops -------------------------
    @abc.abstractmethod
    def upload_file(self, local_path: Path, remote_key: str) -> None:
        """Upload *local_path* into the backend at *remote_key*."""

    @abc.abstractmethod
    def download_file(self, remote_key: str, dest_path: Path) -> None:
        """Download *remote_key* into *dest_path* (overwrite if exists)."""

    @abc.abstractmethod
    def delete_file(self, remote_key: str) -> None:
        """Remove *remote_key* from the backend (no error if absent)."""

    # ---------------------------- optional helpers ------------------------
    def list_files(self, prefix: str = "") -> Iterable[str]:
        """Yield remote keys under *prefix* (default: all).

        Default implementation raises *NotImplementedError*. Providers that can
        list objects cheaply should override.
        """
        raise NotImplementedError

    def get_uri(self, remote_key: str) -> str:  # pragma: no cover
        """Return a public/internal URI for *remote_key* if meaningful."""
        raise NotImplementedError
