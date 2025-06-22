from pathlib import Path
from typing import Dict

from storage.config.yaml_config_loader import YAMLConfigLoader


def load_storage_config(source) -> Dict:
    """Dispatch to the correct loader based on file suffix."""
    path = Path(source)
    suffix = path.suffix.lower()

    if suffix in {".yml", ".yaml"}:
        return YAMLConfigLoader().load(path)
    if suffix == ".json":
        raise NotImplementedError("JSON config support not yet implemented")
    raise ValueError(f"Unsupported config format: {suffix}")
