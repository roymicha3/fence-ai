# Fence-AI Storage PoC

Minimal, extensible Python library for uploading, downloading and deleting files
across multiple storage back-ends.  The current implementation ships with an
AWS S3 provider and a generic interface ready for future providers such as
Google Drive.

## Features
* 🗂  **StorageBackend ABC** – single, simple contract for all providers.
* ☁️  **S3Backend** – reference implementation using per-call boto3 clients.
* 📄  YAML for bucket configuration and .env for credentials.
* 🏃  End-to-end PoC script (`src/main.py`) proving the flow.

## Project Layout
```
src/
  storage/
    base.py            # StorageBackend interface
    providers/
      s3_backend.py    # S3 implementation (uses utils/aws_client.py)
      utils/
        aws_client.py  # Thin wrapper around boto3 with per-call connection
  config/
    yaml_config_loader.py
    storage_config_loader.py
  main.py              # Demo runner
configs/
  bucket.yaml          # Bucket name + region
  .env               # AWS credentials (environment variables) – **not committed**
```

## Quickstart
1.  **Install deps** (Python 3.8+ recommended):
    ```bash
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Prepare configs**:
    * `configs/bucket.yaml` –
      ```yaml
      provider: s3
      name: my-bucket
      region: us-east-1
      ```
    * `.env` file in project root with AWS credentials:
      ```
      AWS_ACCESS_KEY_ID=your_access_key_here
      AWS_SECRET_ACCESS_KEY=your_secret_key_here
      ```
3.  **Run demo**:
    ```bash
    echo "hello" > demo.txt
    python src/main.py
    ```
    Expected output: `Upload, download, and delete completed successfully.`

## Adding a New Provider
1. Create `storage/providers/<name>_backend.py` implementing `StorageBackend`.
2. Update `config/yaml_config_loader.py` to recognise `provider: <name>`.  
   (Add any provider-specific config schema you need.)

## Security Notes
* **Never commit credentials** – keep them in `configs/` or environment vars.
* boto3 clients are created per action; they are closed promptly.

---
© 2025 Fence-AI – MIT licensed
