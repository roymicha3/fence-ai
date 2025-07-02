from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from client.http_client import HttpClient
from invoker.invoke_config import InvokeConfig
from invoker.response_parser import parse_workflow_response, WorkflowResponse


class PipelineInvoker(ABC):
    """Abstraction point for future orchestrators."""

    @abstractmethod
    def invoke(self, payload: Dict[str, Any]) -> Any: ...


class N8NInvoker(PipelineInvoker):
    """Concrete invoker for n8n webhooks."""

    def __init__(self, config: InvokeConfig) -> None:
        self.url = config.url
        self.method = config.method.upper()
        self.auth = config.auth

        self.client = HttpClient()

    def invoke(self, payload: Dict[str, Any]) -> WorkflowResponse:
        headers = {"Content-Type": "application/json"}
        if self.auth:
            headers["Authorization"] = self.auth
        
        if self.method == "GET":
            resp = self.client.get(self.url, params=payload, headers=headers, timeout=240)
        
        elif self.method == "POST":
            resp = self.client.post(self.url, json=payload, headers=headers, timeout=240)
        else:
            raise ValueError(f"Unsupported HTTP method: {self.method}")

        if isinstance(resp, list):
            resp = resp[0]

        return parse_workflow_response(resp)
