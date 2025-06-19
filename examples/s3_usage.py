"""Example script showing how to use fence-ai S3 helpers.

Run with your AWS credentials set as environment variables or via a config
file.  Requires `boto3` installed in the current environment.  If you are using
the provided Docker setup, these dependencies are already available.
"""
from __future__ import annotations

from pathlib import Path

from fence_ai.s3_access import S3Access
from fence_ai.s3_manager import S3DataManager
from fence_ai.logger import get_logger

logger = get_logger(__name__)

BUCKET = "my-bucket"
KEY = "example/data.txt"
LOCAL = Path("data.txt")


def main() -> None:  # noqa: D401
    # Initialise access with default env var creds
    access = S3Access()
    manager = S3DataManager(access)

    # upload
    manager.upload(BUCKET, KEY, LOCAL)
    logger.info("Uploaded %s to s3://%s/%s", LOCAL, BUCKET, KEY)

    # list
    keys = manager.list_objects(BUCKET, prefix="example/")
    logger.info("Objects with prefix: %s", keys)

    # download
    download_path = Path("downloaded.txt")
    manager.download(BUCKET, KEY, download_path)
    logger.info("Downloaded to %s", download_path)

    # delete
    manager.delete(BUCKET, KEY)
    logger.info("Deleted object")


if __name__ == "__main__":  # pragma: no cover
    main()
