"""Context-managed S3 connection.

Opens a boto3 client on entry and ensures it is properly closed on exit.
Keeping this in one place centralises credential and region handling.
"""
from __future__ import annotations

from contextlib import AbstractContextManager

from typing import Optional, Dict

import boto3




class S3Connection(AbstractContextManager):
    """Context manager that yields an S3 *client* attribute."""

    def __init__(self, creds: Dict[str, str], region: str) -> None:
        self._creds = creds
        self._region = region
        self.client: Optional[boto3.client] = None  # will be initialised in __enter__

    # ------------------------------------------------------------------
    def __enter__(self):
        self.client = boto3.client("s3", region_name=self._region, **self._creds)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.client is not None:
            # botocore client implements close() as of 1.26+; guard for older versions
            close = getattr(self.client, "close", None)
            if callable(close):
                close()
        self.client = None
        # Propagate exceptions (returning False)
        return False
