"""Transport layer for triggering pipelines (currently n8n only)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests


def invoke_n8n(
    payload: Dict[str, Any],
    method: str,
    url: str,
    auth: Optional[str] = None,
) -> requests.Response:  # <= 20 lines
    """Send *payload* to *url* using *method* (GET/POST)."""
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth

    method = method.upper()
    if method == "GET":
        return requests.get(url, params=payload, headers=headers, timeout=10)
    if method == "POST":
        return requests.post(url, json=payload, headers=headers, timeout=10)
    raise ValueError(f"Unsupported HTTP method: {method}")


class PipelineInvoker(ABC):
    """Abstraction point for future orchestrators."""

    @abstractmethod
    def invoke(self, payload: Dict[str, Any]) -> Any: ...


class N8NInvoker(PipelineInvoker):
    """Concrete invoker for n8n webhooks."""

    def __init__(self, url: str, method: str = "POST", auth: Optional[str] = None) -> None:
        self.url, self.method, self.auth = url, method, auth

    def invoke(self, payload: Dict[str, Any]) -> requests.Response:  # noqa: D401
        return invoke_n8n(payload, self.method, self.url, self.auth)
