"""CLI entry-point for triggering an n8n workflow."""
from __future__ import annotations

import sys

from config_loader import load_config
from invoker import invoke_n8n
from payload_utils import load_json_payload, save_json_response


def main() -> None:  # <= 20 lines
    cfg = load_config("n8n_config.yaml")

    try:
        payload = load_json_payload(cfg.payload_file)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Unable to read payload: {exc}", file=sys.stderr)
        payload = {}

    body = invoke_n8n(payload, cfg.method, cfg.url, cfg.auth)
    print(body)
    save_json_response(body)

    print("Done")


if __name__ == "__main__":
    main()
