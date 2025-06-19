"""Extensible configuration manager for Fence AI (new location).

Moved from ``fence_ai.config_core`` to ``fence_ai.core.config`` for clearer
package organisation. Original module remains as a thin shim importing this one
so external callers keep working.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Protocol, runtime_checkable

try:
    import yaml  # type: ignore

    _HAS_YAML = True
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    _HAS_YAML = False

__all__ = ["Config", "register_loader"]


@runtime_checkable
class LoaderProtocol(Protocol):
    """Protocol all loaders must follow."""

    extensions: List[str]

    @staticmethod
    def load(path: Path) -> Dict[str, Any]:  # noqa: D401
        """Return dict contents loaded from *path*."""
        raise NotImplementedError


_REGISTRY: List[LoaderProtocol] = []


def register_loader(cls):  # noqa: D401
    """Class decorator to register a *Loader* implementation."""

    _REGISTRY.append(cls)
    return cls


@register_loader
class JsonLoader:  # noqa: D101
    extensions = [".json"]

    @staticmethod
    def load(path: Path) -> Dict[str, Any]:  # noqa: D401
        return json.loads(path.read_text())


if _HAS_YAML:

    @register_loader
    class YamlLoader:  # noqa: D101
        extensions = [".yaml", ".yml"]

        @staticmethod
        def load(path: Path) -> Dict[str, Any]:  # noqa: D401
            return yaml.safe_load(path.read_text()) or {}


class Config:  # noqa: D101
    def __init__(
        self,
        *,
        defaults: Dict[str, Any] | None = None,
        files: List[str | Path] | None = None,
        env_prefix: str = "AWS_",
    ) -> None:
        self._env_prefix = env_prefix
        self._data: Dict[str, Any] = {}
        self._merge(defaults or {})
        for f in files or []:
            self._merge(self._load_file(Path(f)))
        self._merge(self._env_vars())

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        """Return *shallow* copy of current configuration dictionary."""

        return dict(self._data)

    def merge(self, overrides: Dict[str, Any] | None = None, **kwargs: Any):  # noqa: D401
        """Merge additional *overrides* or keyword arguments (highest precedence)."""

        self._merge(overrides or {})
        self._merge(kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _merge(self, new: Dict[str, Any]) -> None:
        for k, v in new.items():
            if v is not None:
                self._data[k] = v

    def _load_file(self, path: Path) -> Dict[str, Any]:
        for loader in _REGISTRY:
            if path.suffix.lower() in loader.extensions:
                try:
                    return loader.load(path)
                except Exception as exc:  # pragma: no cover
                    raise RuntimeError(f"Failed to load configuration from {path}") from exc
        raise ValueError(f"Unsupported configuration file type: {path}")

    def _env_vars(self) -> Dict[str, Any]:
        prefix_len = len(self._env_prefix)
        return {
            k[prefix_len:].lower(): v
            for k, v in os.environ.items()
            if k.startswith(self._env_prefix)
        }
