"""Loader for storage-service configuration files.

Currently supports YAML files. The returned dict always contains a mandatory key
`provider`, whose value determines which other keys must be present.

Example YAML for S3::
    provider: s3
    name: fence-ai
    region: us-east-1

Example YAML for Google Drive::
    provider: gdrive
    folder_id: 1AbCdEF...
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Dict

import yaml  # PyYAML ─ external dependency


class BaseConfigLoader(abc.ABC):
    """Abstract base for config loaders."""

    @abc.abstractmethod
    def load(self, source) -> Dict:
        """Parse *source* and return a validated configuration mapping."""

    # Shared validation helpers -------------------------------------------------
    @staticmethod
    def _require(data: Dict, *keys):
        missing = [k for k in keys if k not in data]
        if missing:
            raise KeyError(f"Missing required keys: {', '.join(missing)}")


class YAMLConfigLoader(BaseConfigLoader):
    """Parses .yml/.yaml files for storage configuration."""

    def load(self, source: Path) -> Dict:
        data = yaml.safe_load(Path(source).expanduser().read_text())
        if not isinstance(data, dict):
            raise TypeError("YAML config must be a mapping at top level")

        provider = data.get("provider")
        if provider == "s3":
            self._require(data, "name", "region")
        elif provider == "gdrive":
            self._require(data, "folder_id")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        return data


def load_storage_config(source) -> Dict:
    """Dispatch to the correct loader based on file suffix."""
    path = Path(source)
    suffix = path.suffix.lower()

    if suffix in {".yml", ".yaml"}:
        return YAMLConfigLoader().load(path)
    elif suffix == ".json":  # placeholder for future extension
        raise NotImplementedError("JSON config support not yet implemented")
    raise ValueError(f"Unsupported config format: {suffix}")
