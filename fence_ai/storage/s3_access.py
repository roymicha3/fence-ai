"""S3 Access component (moved to `fence_ai.storage`)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
from fence_ai.core.logger import get_logger
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError

logger = get_logger(__name__)


class S3AccessError(RuntimeError):
    """Raised when S3 client/resource cannot be created due to credential issues."""


class S3Access:
    """Factory/helper for boto3 S3 clients & resources.

    Parameters
    ----------
    config : Optional[dict]
        Optional configuration containing credential information. Example::

            {
                "aws_access_key_id": "...",
                "aws_secret_access_key": "...",
                "aws_session_token": "...",  # optional
                "region_name": "us-east-1"    # optional
            }
    """

    _CREDS_KEYS = {
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "region_name",
    }

    def __init__(self, config: Optional[Dict[str, Any]] | None = None, *, config_file: str | Path | None = None):
        # Load lowest-precedence configuration from a JSON file if provided
        self._file_config: Dict[str, Any] = {}
        if config_file is not None:
            try:
                data = json.loads(Path(config_file).read_text())
                if isinstance(data, dict):
                    self._file_config = {k: v for k, v in data.items() if k in self._CREDS_KEYS and v}
            except (OSError, json.JSONDecodeError):
                # Malformed or unreadable file – treat as empty config
                pass

        # Credentials supplied directly to the constructor (medium precedence)
        self._config: Dict[str, Any] = config or {}
        self._config = {k: v for k, v in self._config.items() if k in self._CREDS_KEYS and v}

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def client(self, **overrides: Any):
        """Return a boto3 S3 *client*."""
        logger.debug("Creating S3 client with overrides=%s", {k: '***' if 'secret' in k else v for k, v in overrides.items()})
        return self._create("client", **overrides)

    def resource(self, **overrides: Any):
        """Return a boto3 S3 *resource*."""
        logger.debug("Creating S3 resource with overrides=%s", {k: '***' if 'secret' in k else v for k, v in overrides.items()})
        return self._create("resource", **overrides)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolved_credentials(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        creds: Dict[str, Any] = {}
        creds.update(self._file_config)
        env_map = {
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
            "region_name": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
        }
        creds.update({k: v for k, v in env_map.items() if v})
        creds.update(self._config)
        creds.update({k: v for k, v in overrides.items() if k in self._CREDS_KEYS and v})
        return creds

    def _create(self, kind: str, **overrides: Any):  # noqa: D401
        creds = self._resolved_credentials(overrides)
        try:
            session = boto3.Session(**{k: v for k, v in creds.items() if k != "region_name"})
            if kind == "client":
                return session.client("s3", region_name=creds.get("region_name"))
            if kind == "resource":
                return session.resource("s3", region_name=creds.get("region_name"))
            raise ValueError(f"Unsupported kind: {kind}")
        except (NoCredentialsError, BotoCoreError, ClientError) as exc:
            logger.exception("Failed to create S3 %s: %s", kind, exc)
            raise S3AccessError("Failed to create S3 access: check credentials") from exc
