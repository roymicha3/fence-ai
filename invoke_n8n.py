#!/usr/bin/env python3
"""Trigger an n8n webhook.

Requires env N8N_WEBHOOK_URL, optional N8N_AUTH_HEADER.
Run: python invoke_n8n.py
"""
import os, requests, json
from pathlib import Path
from typing import Any
URL = "http://localhost:5678/webhook-test/4816b59c-b4c3-4f90-b6e3-2144083bd9d0" # os.getenv("N8N_WEBHOOK_URL")
AUTH = "" # os.getenv("N8N_AUTH_HEADER")


def load_json_payload(path: str | Path = "n8n_payload.json") -> dict:
    """Read a JSON file and return its contents as a dict.

    Parameters
    ----------
    path : str | Path
        Location of the JSON file. Defaults to 'n8n_payload.json' in CWD.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
            return json.load(f)

def save_json_response(data: Any, path: str | Path = "n8n_response.json") -> None:
    """Write *data* to *path* as JSON with UTF-8 encoding."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

METHOD = "GET" # os.getenv("N8N_METHOD", "GET")

def invoke_n8n(payload: dict | None = None, method: str = METHOD):
    """Trigger the n8n webhook using `method` (GET or POST).

    Parameters
    ----------
    payload : dict | None
        Data to send. For POST it is sent as JSON body; for GET it is sent as
        query parameters. Defaults to empty dict.
    method : str
        HTTP verb to use; defaults to "GET".

    Returns
    -------
    requests.Response
    """
    if not URL:
        raise EnvironmentError("N8N_WEBHOOK_URL not set")

    payload = payload or {}
    method = method.upper()

    headers = {"Content-Type": "application/json"}
    if AUTH:
        headers["Authorization"] = AUTH

    if method == "GET":
        return requests.get(URL, params=payload, headers=headers, timeout=10)
    elif method == "POST":
        return requests.post(URL, json=payload, headers=headers, timeout=10)
    else:
        raise ValueError("Unsupported HTTP method: %s" % method)

if __name__ == "__main__":
    try:
        payload = load_json_payload()
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {}

    response = invoke_n8n(payload)
    print(response.status_code)
    try:
        body = response.json()
    except ValueError:
        body = response.text
    print(body)
    save_json_response(body)
