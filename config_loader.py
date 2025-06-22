"""Configuration loading utilities for n8n invoker.

Currently supports environment variables only but is designed so that
additional sources (files, CLI flags, secret managers) can be layered in
later without touching the consumer code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
import yaml
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class Config:
    """Normalized configuration values for the invoker."""

    url: str
    method: str = "POST"
    auth: Optional[str] = None
    payload_file: Path = Path("n8n_payload.json")


def load_config(path: str | Path | None = None) -> Config:
    """Return a :class:`Config` built from environment variables.

    Env vars recognised:
    - ``N8N_WEBHOOK_URL``  (required)
    - ``N8N_METHOD``       (GET/POST, default POST)
    - ``N8N_AUTH_HEADER``  (optional auth header value)
    - ``N8N_PAYLOAD_FILE`` (path to payload JSON)
    """
    # If YAML path provided try to load it first
    if path is not None:
        with Path(path).expanduser().open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        # yaml keys override env
        url = data.get("url")
        method = data.get("method", "POST").upper()
        auth = data.get("auth")
        payload_path = Path(data.get("payload_file", "n8n_payload.json"))
        return Config(url=url, method=method, auth=auth, payload_file=payload_path)

    # fallback to env vars only
    url = os.getenv("N8N_WEBHOOK_URL")
    if not url:
        raise EnvironmentError("N8N_WEBHOOK_URL env var is required when config file not provided")
    method = os.getenv("N8N_METHOD", "POST").upper()
    auth = os.getenv("N8N_AUTH_HEADER") or None
    payload_path = Path(os.getenv("N8N_PAYLOAD_FILE", "n8n_payload.json"))
    return Config(url=url, method=method, auth=auth, payload_file=payload_path)
