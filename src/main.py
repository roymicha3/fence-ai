from pathlib import Path
import sys
from storage.providers.s3_backend import S3Backend
from botocore.exceptions import BotoCoreError, ClientError

from invoker.config_loader import load_config
from invoker.invoker import invoke_n8n
from invoker.payload_utils import load_json_payload, save_json_response

CFG = {"cred_src": "configs/Server_accessKeys.csv", "cfg_src": "configs/bucket.yaml"}
backend = S3Backend(**CFG)

def run_n8n_flow():
    """Trigger n8n webhook using invoker stack."""
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
    # Run original S3 demo
    try:
        backend.upload_file(Path("demo.txt"), "demo.txt")
        backend.download_file("demo.txt", Path("downloaded_demo.txt"))
        backend.delete_file("demo.txt")
        print("Upload, download, and delete completed successfully.")
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")

    # Additionally run n8n flow
    run_n8n_flow()
    
    try:
        backend.upload_file(Path("demo.txt"), "demo.txt")
        backend.download_file("demo.txt", Path("downloaded_demo.txt"))
        backend.delete_file("demo.txt")
        print("Upload, download, and delete completed successfully.")
    
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")