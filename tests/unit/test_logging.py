"""Tests that logging occurs for S3DataManager operations."""
from __future__ import annotations

import logging
import os
from types import ModuleType
from pathlib import Path
from typing import Any

import pytest

# Stub boto3/botocore modules so import succeeds without deps
import sys
if "boto3" not in sys.modules:
    b3 = ModuleType("boto3")
    setattr(b3, "Session", lambda **_kw: None)
    sys.modules["boto3"] = b3
if "botocore.exceptions" not in sys.modules:
    exc_mod = ModuleType("botocore.exceptions")
    sys.modules["botocore.exceptions"] = exc_mod

# Ensure fence_ai package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fence_ai.storage.s3_manager import S3DataManager  # noqa: E402  pylint: disable=wrong-import-position


class _DummyClient:  # noqa: D101
    def __init__(self):
        self.uploads: list[tuple[str, str, str]] = []
        self.downloads: list[tuple[str, str, str]] = []
        self.deletes: list[tuple[str, str]] = []

    def upload_file(self, path: str, bucket: str, key: str, ExtraArgs=None):  # noqa: ANN001
        self.uploads.append((path, bucket, key))

    def download_file(self, bucket: str, key: str, filename: str):  # noqa: ANN001
        Path(filename).write_text("dummy")
        self.downloads.append((bucket, key, filename))

    def delete_object(self, Bucket, Key):  # noqa: N803, ANN001
        self.deletes.append((Bucket, Key))

    def list_objects_v2(self, Bucket, Prefix="", **_kw):  # noqa: N803, ANN001
        return {"Contents": []}


class _DummyAccess:  # noqa: D101
    def __init__(self, client):
        self._client = client

    def client(self, **_kw):  # noqa: ANN001, D401
        return self._client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("operation", ["upload", "download", "delete", "list_objects"])
def test_logging(caplog: pytest.LogCaptureFixture, tmp_path: Path, operation: str):
    caplog.set_level(logging.INFO)

    client = _DummyClient()
    dm = S3DataManager(_DummyAccess(client))

    if operation == "upload":
        file_path = tmp_path / "file.txt"
        file_path.write_text("x")
        dm.upload("b", "k", file_path)
        expected = "Uploading"
    elif operation == "download":
        dst = tmp_path / "out.txt"
        dm.download("b", "k", dst)
        expected = "Downloading"
    elif operation == "delete":
        dm.delete("b", "k")
        expected = "Deleting"
    else:
        dm.list_objects("b")
        expected = "Listing objects"

    # ensure at least one log record contains the expected substring
    assert any(expected in rec.message for rec in caplog.records), f"No log record for {operation}"
