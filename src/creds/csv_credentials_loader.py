"""CSV implementation of credential loader."""
from pathlib import Path
from typing import Dict
import csv

from creds.credentials_base import BaseCredentialsLoader

class CSVCredentialsLoader(BaseCredentialsLoader):
    """Loads AWS-style credentials from a CSV file allowing header variants."""

    HEADER_ALIASES = {
        "aws_access_key_id": {"aws_access_key_id", "access_key_id", "access key id"},
        "aws_secret_access_key": {
            "aws_secret_access_key",
            "secret_access_key",
            "secret access key",
        },
    }

    def load(self, source: Path | str) -> Dict[str, str]:
        with Path(source).expanduser().open(newline="") as fh:
            row = next(csv.DictReader(fh))
        norm = {k.strip().lstrip("\ufeff").lower(): v.strip() for k, v in row.items()}
        return {
            "aws_access_key_id": self._find(norm, "aws_access_key_id"),
            "aws_secret_access_key": self._find(norm, "aws_secret_access_key"),
        }

    @classmethod
    def _find(cls, mapping: Dict[str, str], canonical: str) -> str:
        for alias in cls.HEADER_ALIASES[canonical]:
            if alias in mapping and mapping[alias]:
                return mapping[alias]
        raise KeyError(f"Missing {canonical} in CSV")
