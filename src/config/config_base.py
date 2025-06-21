"""Base class for storage configuration loaders."""
from abc import ABC, abstractmethod
from typing import Dict

class BaseConfigLoader(ABC):
    """Abstract loader that parses a source into a configuration dict."""

    @abstractmethod
    def load(self, source) -> Dict:
        """Parse *source* and return a validated configuration mapping."""

    # shared helper
    @staticmethod
    def _require(data: Dict, *keys):
        missing = [k for k in keys if k not in data]
        if missing:
            raise KeyError(f"Missing required keys: {', '.join(missing)}")
