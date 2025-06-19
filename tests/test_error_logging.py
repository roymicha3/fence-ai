"""Error handling & logging tests."""
from __future__ import annotations

import logging
from pathlib import Path
from types import ModuleType

import pytest

from fence_ai.storage.s3_manager import S3DataManager, S3UploadError, S3DownloadError, S3DeleteError, S3ListError
from fence_ai.storage.s3_access import S3AccessError


class _FailAccess:  # noqa: D101
    def client(self, **_kw):  # noqa: ANN001, D401
        raise S3AccessError("boom")


@pytest.mark.parametrize(
    "method, args, exc_cls, log_sub",
    [
        ("upload", ("b", "k", Path("/tmp/f.txt")), S3UploadError, "S3 client initialisation failed"),
        ("download", ("b", "k", Path("out")), S3DownloadError, "S3 client initialisation failed"),
        ("delete", ("b", "k"), S3DeleteError, "S3 client initialisation failed"),
        ("list_objects", ("b",), S3ListError, "S3 client initialisation failed"),
    ],
)
def test_error_logging(caplog: pytest.LogCaptureFixture, tmp_path: Path, method: str, args, exc_cls, log_sub: str):
    caplog.set_level(logging.ERROR)
    dm = S3DataManager(_FailAccess())

    # For upload ensure path exists to reach client call
    if method == "upload":
        (tmp_path / "f.txt").write_text("x")
        args = (args[0], args[1], tmp_path / "f.txt")

    with pytest.raises(exc_cls):
        getattr(dm, method)(*args)

    assert any(log_sub in rec.message for rec in caplog.records), f"No error log for {method}"
