"""Base abstract class for credential loaders."""
from abc import ABC, abstractmethod
from typing import Dict

class BaseCredentialsLoader(ABC):
    """Abstract contract for credential loaders returning key/value pairs."""

    @abstractmethod
    def load(self, source) -> Dict[str, str]:
        """Parse *source* and return a credential mapping."""
