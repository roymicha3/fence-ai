from pathlib import Path
from storage.providers.s3_backend import S3Backend
from botocore.exceptions import BotoCoreError, ClientError

CFG = {"cred_src": "configs/Server_accessKeys.csv", "cfg_src": "configs/bucket.yaml"}
backend = S3Backend(**CFG)

if __name__ == "__main__":
    
    try:
        backend.upload_file(Path("demo.txt"), "demo.txt")
        backend.download_file("demo.txt", Path("downloaded_demo.txt"))
        backend.delete_file("demo.txt")
        print("Upload, download, and delete completed successfully.")
    
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")