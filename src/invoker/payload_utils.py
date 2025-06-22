"""Payload I/O helpers for n8n invoker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json_payload(path: str | Path) -> Dict[str, Any]:  # <=20 lines
    """Read *path* as JSON and return a dict.

    Raises ``FileNotFoundError`` if the file is missing and
    ``json.JSONDecodeError`` if the contents are not valid JSON.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def save_json_response(data: Any, path: str | Path = "n8n_response.json") -> None:  # <=20 lines
    """Write *data* to *path* in pretty-printed JSON (UTF-8)."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
