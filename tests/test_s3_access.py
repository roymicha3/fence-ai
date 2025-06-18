"""Unit tests for the S3Access helper.

These tests run without hitting AWS. We monkey-patch ``boto3.Session`` so that
no real network/credential chain is used. The same logic as earlier but placed
in the project-root ``tests/`` folder so pytest picks it up by default.
"""

from __future__ import annotations

# Ensure project root is on sys.path for "fence_ai" imports when running via venv
import sys, types
from types import ModuleType
from pathlib import Path

# --- Lightweight stubs so imports succeed when deps are absent ---
if "botocore.exceptions" not in sys.modules:
    bc = ModuleType("botocore")
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
    bc.exceptions = exc_mod
    sys.modules["botocore"] = bc
    sys.modules["botocore.exceptions"] = exc_mod

if "boto3" not in sys.modules:
    b3 = ModuleType("boto3")
    setattr(b3, "Session", lambda **_kw: None)
    sys.modules["boto3"] = b3

# -----------------------------------------------------------------
# Add project root to import path for local packages
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Any, Dict

import pytest

try:
    from botocore.exceptions import NoCredentialsError  # type: ignore
except ModuleNotFoundError:  # fallback if botocore isn't installed in local venv
    class NoCredentialsError(Exception):
        """Local stub when botocore is absent."""

import fence_ai.s3_access as s3_module
from fence_ai import S3Access, S3AccessError


class _DummySession:  # helper – emulates minimal boto3.Session API
    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs

    def client(self, service_name: str, region_name: str | None = None):
        return {
            "kind": "client",
            "service": service_name,
            "region": region_name,
            "creds": self.kwargs,
        }

    def resource(self, service_name: str, region_name: str | None = None):
        return {
            "kind": "resource",
            "service": service_name,
            "region": region_name,
            "creds": self.kwargs,
        }


def _patch_session(monkeypatch, error: Exception | None = None):
    """Monkey-patch ``boto3.Session`` inside the module under test."""

    def _factory(**kwargs):  # noqa: D401
        if error is not None:
            raise error
        return _DummySession(**kwargs)

    stub = type("_Boto3Stub", (), {"Session": staticmethod(_factory)})
    monkeypatch.setattr(s3_module, "boto3", stub, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_explicit_credentials(monkeypatch):
    _patch_session(monkeypatch)

    access = S3Access()
    res = access.client(
        aws_access_key_id="AKIAEXPLICIT",
        aws_secret_access_key="SECRET",
        region_name="us-west-2",
    )

    assert res["kind"] == "client"
    assert res["service"] == "s3"
    assert res["region"] == "us-west-2"
    assert res["creds"]["aws_access_key_id"] == "AKIAEXPLICIT"


def test_config_credentials(monkeypatch):
    _patch_session(monkeypatch)

    cfg: Dict[str, str] = {
        "aws_access_key_id": "AKIACONFIG",
        "aws_secret_access_key": "CFGSECRET",
        "region_name": "eu-central-1",
    }
    res = S3Access(cfg).resource()
    assert res["kind"] == "resource"
    assert res["region"] == "eu-central-1"
    assert res["creds"]["aws_access_key_id"] == "AKIACONFIG"


def test_env_credentials(monkeypatch):
    _patch_session(monkeypatch)

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ENVSECRET")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")

    res = S3Access().client()
    assert res["region"] == "ap-southeast-1"
    assert res["creds"]["aws_access_key_id"] == "AKIAENV"


def test_error_propagation(monkeypatch):
    _patch_session(monkeypatch, error=NoCredentialsError())

    with pytest.raises(S3AccessError):
        S3Access().client()
