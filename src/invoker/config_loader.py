"""Configuration loading utilities for n8n invoker.

Currently supports environment variables only but is designed so that
additional sources (files, CLI flags, secret managers) can be layered in
later without touching the consumer code.
"""
from __future__ import annotations

from dataclasses import dataclass
import yaml
from pathlib import Path
from typing import Optional
from omegaconf import OmegaConf, DictConfig


@dataclass(slots=True)
class Config:
    """Normalized configuration values for the invoker."""

    url: str
    method: str = "POST"
    auth: Optional[str] = None
    payload_path: Path | None = None


def load_config(path: str | Path | None = None) -> Config:
    """Return a :class:`Config` built from environment variables.

    Env vars recognised:
    - ``WEBHOOK_URL``  (required)
    - ``METHOD``       (GET/POST, default POST)
    - ``AUTH_HEADER``  (optional auth header value)
    - ``PAYLOAD_FILE`` (path to payload JSON)
    """
    conf = OmegaConf.load(path)
    
    return Config(
        url=conf.url, 
        method=conf.method, 
        auth=conf.auth, 
        payload_path=Path(conf.payload_path))
