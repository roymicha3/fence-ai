from data.aws.aws_client import S3Client
from config.storage_config_loader import load_storage_config
from botocore.exceptions import BotoCoreError, ClientError

BUCKET_CFG = load_storage_config("configs/bucket.yaml")
client = S3Client()

if __name__ == "__main__":
    
    try:
        client.upload_file("demo.txt", BUCKET_CFG["name"], "demo.txt")
        client.download_file(BUCKET_CFG["name"], "demo.txt", "downloaded_demo.txt")
        client.delete_file(BUCKET_CFG["name"], "demo.txt")
        print("Upload, download, and delete completed successfully.")
    
    except (BotoCoreError, ClientError) as exc:
        print(f"S3 operation failed: {exc}")