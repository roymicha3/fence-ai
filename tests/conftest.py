"""Global pytest configuration and utilities.

This file stubs external AWS libraries (boto3, botocore) so that the codebase
can be tested in environments where those packages are not installed (e.g.
CI containers, minimal dev setups). Individual tests can still monkeypatch as
needed, but this ensures basic import-time availability for the core package.
"""
from __future__ import annotations

import sys
from types import ModuleType

# ---------------------------------------------------------------------------
# Stub boto3
# ---------------------------------------------------------------------------

if "boto3" not in sys.modules:
    boto3_stub = ModuleType("boto3")

    # minimal Session replacement that returns an object with client/resource
    class _DummySession:  # noqa: D401
        def client(self, *_a, **_kw):  # noqa: ANN001, D401
            return object()

        def resource(self, *_a, **_kw):  # noqa: ANN001, D401
            return object()

    boto3_stub.Session = _DummySession  # type: ignore[attr-defined]
    sys.modules["boto3"] = boto3_stub

# ---------------------------------------------------------------------------
# Stub botocore.exceptions
# ---------------------------------------------------------------------------

if "botocore.exceptions" not in sys.modules:
    exc_mod = ModuleType("botocore.exceptions")

    class _DummyExc(Exception):
        """Placeholder for botocore exception types."""

    # Common exception names used in code/tests
    for name in ("BotoCoreError", "NoCredentialsError", "ClientError"):
        setattr(exc_mod, name, _DummyExc)

    sys.modules["botocore.exceptions"] = exc_mod
