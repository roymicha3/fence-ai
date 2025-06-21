"""Environment-variable credential loader."""
import os
from typing import Dict

from creds.credentials_base import BaseCredentialsLoader

class EnvCredentialsLoader(BaseCredentialsLoader):
    """Loads credentials from AWS-related environment variables."""

    def load(self, source: str = "env") -> Dict[str, str]:
        return {
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        }
