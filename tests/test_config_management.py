"""Tests for configuration precedence in S3Access."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

import pytest

# Ensure stubs so boto3/botocore imports inside the module succeed
import sys
if "botocore.exceptions" not in sys.modules:
    exc_mod = ModuleType("botocore.exceptions")
    class _DummyError(Exception):
        pass
    class BotoCoreError(_DummyError):
        pass
    class NoCredentialsError(_DummyError):
        pass
    class ClientError(_DummyError):
        pass
    exc_mod.BotoCoreError = BotoCoreError
    exc_mod.NoCredentialsError = NoCredentialsError
    exc_mod.ClientError = ClientError
    sys.modules["botocore.exceptions"] = exc_mod

if "boto3" not in sys.modules:
    b3 = ModuleType("boto3")
    setattr(b3, "Session", lambda **_kw: None)
    sys.modules["boto3"] = b3

# Add project root so we can import fence_ai
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import fence_ai.storage.s3_access
from fence_ai.storage.s3_access import S3Access
from fence_ai.core.config import Config


class _DummySession:  # noqa: D101
    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs

    def client(self, *_a, **_kw):  # noqa: D401, ANN001
        return self.kwargs


def _patch_session(monkeypatch):  # noqa: D401
    stub = type("_Boto3Stub", (), {"Session": staticmethod(lambda **kw: _DummySession(**kw))})
    monkeypatch.setattr(fence_ai.storage.s3_access, "boto3", stub, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_file_credentials(monkeypatch, tmp_path: Path):
    _patch_session(monkeypatch)

    file_cfg = tmp_path / "creds.json"
    file_cfg.write_text(json.dumps({"aws_access_key_id": "AKIAFILE", "aws_secret_access_key": "FILESECRET"}))

    access = S3Access(config_file=file_cfg)
    creds = access.client()
    assert creds["aws_access_key_id"] == "AKIAFILE"


def test_env_prefix(monkeypatch):
    _patch_session(monkeypatch)

    monkeypatch.setenv("CUSTOM_KEY", "VALUE")
    cfg = Config(files=[], env_prefix="CUSTOM_")
    assert cfg.as_dict()["key"] == "VALUE"


def test_runtime_merge():
    cfg = Config(defaults={"a": 1})
    cfg.merge({"b": 2})
    cfg.merge(c=3)
    assert cfg.as_dict() == {"a": 1, "b": 2, "c": 3}



def test_precedence(monkeypatch, tmp_path: Path):
    _patch_session(monkeypatch)

    # file-level creds (lowest)
    file_cfg = tmp_path / "creds.json"
    file_cfg.write_text(json.dumps({"aws_access_key_id": "AKIAFILE"}))

    # env vars (higher than file)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")

    # dict passed to constructor (higher than env)
    access = S3Access({"aws_access_key_id": "AKIADICT"}, config_file=file_cfg)

    # overrides (highest precedence)
    res1 = access.client()
    assert res1["aws_access_key_id"] == "AKIADICT"

    res2 = access.client(aws_access_key_id="AKIAOVR")
    assert res2["aws_access_key_id"] == "AKIAOVR"
