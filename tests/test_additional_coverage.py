"""Additional tests to raise overall coverage for critical components."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import ModuleType
import sys

# add project root to path so that 'fence_ai' is importable when tests run standalone
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Stub boto3 and botocore so core package imports without external deps
boto_stub = ModuleType("boto3")
setattr(boto_stub, "Session", lambda **_kw: None)
sys.modules.setdefault("boto3", boto_stub)

botocore_exc = ModuleType("botocore.exceptions")
class _DummyExc(Exception):
    pass
setattr(botocore_exc, "BotoCoreError", _DummyExc)
setattr(botocore_exc, "NoCredentialsError", _DummyExc)
setattr(botocore_exc, "ClientError", _DummyExc)
sys.modules.setdefault("botocore.exceptions", botocore_exc)
from typing import Any
from unittest import mock

import pytest

import importlib

from fence_ai.config_core import Config
from fence_ai.core.logger import configure as configure_logger, get_logger
from fence_ai.storage.s3_access import S3Access, S3AccessError
from fence_ai.storage.s3_manager import S3DataManager

# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_precedence_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """YAML file should be lowest precedence; env vars override; runtime highest."""
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        pytest.skip("pyyaml not installed in env")

    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text("""
aws_access_key_id: file_id
aws_secret_access_key: file_secret
region_name: eu-west-1
""")

    # env overrides file
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env_id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "env_secret")

    cfg = Config(files=[yaml_path])
    # runtime merge overrides env
    cfg.merge({"aws_access_key_id": "runtime_id"})

    data = cfg.as_dict()
    assert data["aws_access_key_id"] == "runtime_id"
    assert data["aws_secret_access_key"] == "env_secret"
    assert data["region_name"] == "eu-west-1"

# ---------------------------------------------------------------------------
# S3Access credential resolution precedence
# ---------------------------------------------------------------------------

def _dummy_boto_session(**_kw):  # noqa: D401
    class _Sess:  # noqa: D401
        def client(self, *_a, **_kw):  # noqa: D401, ANN001
            return "client"

        def resource(self, *_a, **_kw):  # noqa: D401, ANN001
            return "resource"

    return _Sess()


def test_s3_access_resolved_precedence(monkeypatch: pytest.MonkeyPatch):
    # Stub boto3 Session
    dummy_boto = ModuleType("boto3")
    dummy_boto.Session = _dummy_boto_session  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "boto3", dummy_boto)

    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    # file config via temp JSON
    file_cfg = {"aws_access_key_id": "file", "aws_secret_access_key": "file_s"}
    cfg_path = Path("cfg.json")
    cfg_path.write_text(json.dumps(file_cfg))

    s3 = S3Access(config={"aws_access_key_id": "ctor"}, config_file=str(cfg_path))

    # monkeypatch env
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env")

    # overrides when calling client
    creds = s3._resolved_credentials({"aws_access_key_id": "call"})
    assert creds["aws_access_key_id"] == "call"
    # secret key should come from env (env override over file and ctor)
    assert creds["aws_secret_access_key"] == "file_s"  # env not set, stays file

# ---------------------------------------------------------------------------
# S3DataManager list_objects paginator path
# ---------------------------------------------------------------------------

class _Paginator:  # noqa: D101
    def __init__(self):
        self._pages = [
            {"Contents": [{"Key": "a"}, {"Key": "b"}]},
            {"Contents": [{"Key": "c"}]},
        ]

    def paginate(self, **_kw):  # noqa: D401, ANN001
        return self._pages


class _ClientWithPaginator:  # noqa: D101
    def get_paginator(self, _name):  # noqa: ANN001
        return _Paginator()


class _AccessPaginator:  # noqa: D101
    def client(self, **_kw):  # noqa: ANN001, D401
        return _ClientWithPaginator()


def test_s3_manager_list_objects_paginator():
    dm = S3DataManager(_AccessPaginator())
    keys = dm.list_objects("bucket")
    assert keys == ["a", "b", "c"]

# ---------------------------------------------------------------------------
# Logger env var configuration
# ---------------------------------------------------------------------------

def test_logger_env_var_configuration(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FENCE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("FENCE_LOG_FORMAT", "plain")

    configure_logger(force=True)
    log = get_logger("foo")
    import logging
    assert log.getEffectiveLevel() == logging.DEBUG
