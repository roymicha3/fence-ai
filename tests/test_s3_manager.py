"""Tests for S3DataManager.upload."""
from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

# Ensure project root on path and create stub boto3/botocore as in test_s3_access
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))

if "boto3" not in sys.modules:
    import types
    b3 = types.ModuleType("boto3")
    sys.modules["boto3"] = b3

if "botocore.exceptions" not in sys.modules:
    import types
    exc_mod = types.ModuleType("botocore.exceptions")
    class ClientError(Exception):
        pass
    exc_mod.ClientError = ClientError
    sys.modules["botocore.exceptions"] = exc_mod

import fence_ai.storage.s3_access
import fence_ai.storage.s3_manager
from fence_ai.storage.s3_manager import S3DataManager, S3UploadError, S3DownloadError, S3DeleteError, S3ListError
from fence_ai.storage.s3_access import S3Access


class _DummyClient:  # noqa: D101
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []

    def upload_file(self, path: str, bucket: str, key: str, ExtraArgs=None):  # noqa: D401
        self.calls.append((path, bucket, key, ExtraArgs or {}))


class _DummyAccess(S3Access):  # type: ignore
    def __init__(self, client: _DummyClient):
        self._client = client

    def client(self, **overrides: Any):  # noqa: D401, ANN001
        return self._client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upload_success(tmp_path: Path):
    dummy_file = tmp_path / "data.txt"
    dummy_file.write_text("payload")

    c = _DummyClient()
    dm = S3DataManager(_DummyAccess(c))

    dm.upload("mybucket", "folder/data.txt", dummy_file)

    assert c.calls == [(str(dummy_file), "mybucket", "folder/data.txt", {})]


def test_upload_nonexistent_file(tmp_path: Path):
    c = _DummyClient()
    dm = S3DataManager(_DummyAccess(c))

    with pytest.raises(FileNotFoundError):
        dm.upload("b", "k", tmp_path / "missing.bin")


def test_upload_client_error(tmp_path: Path):
    dummy_file = tmp_path / "f.bin"
    dummy_file.write_bytes(b"x")

    class _ErrClient(_DummyClient):
        def upload_file(self, *a, **kw):  # noqa: D401, ANN001
            raise Exception("boom")

    dm = S3DataManager(_DummyAccess(_ErrClient()))

    with pytest.raises(S3UploadError):
        dm.upload("b", "k", dummy_file)


def test_download_success(tmp_path: Path):
    dst = tmp_path / "out.bin"

    class _DownClient(_DummyClient):
        def download_file(self, bucket, key, filename):  # noqa: ANN001, D401
            Path(filename).write_text("ok")

    dm = S3DataManager(_DummyAccess(_DownClient()))
    ret = dm.download("b", "k", dst)
    assert ret == dst
    assert dst.read_text() == "ok"


def test_download_client_error(tmp_path: Path):
    class _ErrClient(_DummyClient):
        def download_file(self, *a, **kw):  # noqa: D401, ANN001
            raise Exception("fail")

    dm = S3DataManager(_DummyAccess(_ErrClient()))

    with pytest.raises(S3DownloadError):
        dm.download("b", "k", tmp_path / "f")


def test_list_objects_success():
    class _ListClient(_DummyClient):
        def list_objects_v2(self, Bucket, Prefix="", **_kw):  # noqa: N803, ANN001
            return {"Contents": [{"Key": Prefix + "a.txt"}, {"Key": Prefix + "b.txt"}]}

    dm = S3DataManager(_DummyAccess(_ListClient()))
    keys = dm.list_objects("bucket", "folder/")
    assert keys == ["folder/a.txt", "folder/b.txt"]


def test_delete_success():
    class _DelClient(_DummyClient):
        def delete_object(self, Bucket, Key):  # noqa: N803, ANN001
            # record call for assertion
            self.calls.append((Bucket, Key))

    c = _DelClient()
    dm = S3DataManager(_DummyAccess(c))

    dm.delete("mybucket", "folder/file.txt")

    assert c.calls == [("mybucket", "folder/file.txt")]


def test_delete_client_error():
    class _ErrClient(_DummyClient):
        def delete_object(self, *a, **kw):  # noqa: D401, ANN001
            raise Exception("oops")

    dm = S3DataManager(_DummyAccess(_ErrClient()))

    with pytest.raises(S3DeleteError):
        dm.delete("b", "k")


def test_list_objects_error():
    class _ErrClient(_DummyClient):
        def list_objects_v2(self, *a, **kw):  # noqa: D401, ANN001
            raise Exception("bad")

    dm = S3DataManager(_DummyAccess(_ErrClient()))

    with pytest.raises(S3ListError):
        dm.list_objects("b")
