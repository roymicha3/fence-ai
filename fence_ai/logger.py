"""Project-wide logging helper for Fence-AI.

Goals
-----
1. Single point of configuration so every package component produces
   consistent, well-formatted logs.
2. No mandatory third-party dependencies – optional extras (colorlog or
   python-json-logger) are auto-detected and used if present.
3. Runtime configurability via environment variables so Docker users can tweak
   verbosity/format without rebuilding the image.
4. Provide a tiny public API: ``configure`` (idempotent) and ``get_logger``.

Environment variables
.....................
FENCE_LOG_LEVEL   – DEBUG, INFO, WARNING (default INFO)
FENCE_LOG_FORMAT  – plain | color | json  (default plain)
"""
from __future__ import annotations

import logging
import logging.config
import os
from types import ModuleType
from typing import Any, Dict, Optional

_LOGGERS: Dict[str, logging.Logger] = {}
_CONFIGURED = False

__all__ = ["configure", "get_logger"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_json_formatter() -> Optional[str]:
    """Return import path of a JSON formatter if available, else *None*."""

    try:
        import pythonjsonlogger  # noqa: F401

        return "pythonjsonlogger.jsonlogger.JsonFormatter"
    except ModuleNotFoundError:
        return None


def _detect_color_formatter() -> Optional[str]:
    """Return import path of a color formatter if available, else *None*."""

    try:
        import colorlog  # noqa: F401

        return "colorlog.ColoredFormatter"
    except ModuleNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(force: bool = False) -> None:  # noqa: D401
    """Configure root logger. Safe to call multiple times.

    Parameters
    ----------
    force : bool, default False
        If *True*, apply configuration even if it was already configured.
    """

    global _CONFIGURED  # noqa: PLW0603

    if _CONFIGURED and not force:
        return

    level_name = os.getenv("FENCE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt_choice = os.getenv("FENCE_LOG_FORMAT", "plain").lower()
    fmt: str
    fmt_config: Dict[str, Any] = {}

    if fmt_choice == "json":
        json_path = _detect_json_formatter()
        if json_path:
            fmt_config = {
                "()": json_path,
                "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        else:
            fmt_choice = "plain"  # fallback

    if fmt_choice == "color":
        color_path = _detect_color_formatter()
        if color_path:
            fmt_config = {
                "()": color_path,
                "format": "%(log_color)s%(levelname)s %(name)s:%(reset)s %(message)s",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            }
        else:
            fmt_choice = "plain"

    if fmt_choice == "plain":
        fmt_config = {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": fmt_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
            }
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:  # noqa: D401
    """Return a project logger, configuring root on first call."""

    if not _CONFIGURED:
        configure()

    if name is None:
        name = "fence_ai"

    if name not in _LOGGERS:
        _LOGGERS[name] = logging.getLogger(name)
    return _LOGGERS[name]
