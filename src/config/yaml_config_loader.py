"""YAML implementation of storage configuration loader."""
from pathlib import Path
from typing import Dict
import yaml

from config.config_base import BaseConfigLoader

class YAMLConfigLoader(BaseConfigLoader):
    """Parses .yml/.yaml storage configuration files."""

    def load(self, source: Path | str) -> Dict:
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
