from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from client.http_client import HttpClient
from invoker.config_loader import Config


class PipelineInvoker(ABC):
    """Abstraction point for future orchestrators."""

    @abstractmethod
    def invoke(self, payload: Dict[str, Any]) -> Any: ...


class N8NInvoker(PipelineInvoker):
    """Concrete invoker for n8n webhooks."""

    def __init__(self, config: Config) -> None:
        self.url = config.url
        self.method = config.method.upper()
        self.auth = config.auth

        self.client = HttpClient()

    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.auth:
            headers["Authorization"] = self.auth
        
        if self.method == "GET":
            resp = self.client.get(self.url, params=payload, headers=headers, timeout=10)
        
        elif self.method == "POST":
            resp = self.client.post(self.url, json=payload, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {self.method}")

        return resp
