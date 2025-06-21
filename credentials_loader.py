"""Generic credential loading utilities.

Currently supports:
- CSV files with varying header names for AWS-style access/secret keys.
- Environment variables (when *source* is the string ``"env"``) – expects
  ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY``.

The public helper ``load_credentials(source)`` returns a flat ``dict`` suitable
for passing directly to SDK client builders (e.g. ``boto3.client``).
"""
from __future__ import annotations

import abc
import csv
import os
from pathlib import Path
from typing import Dict, Protocol


class BaseCredentialsLoader(abc.ABC):
    """Abstract base class for credential loaders."""

    @abc.abstractmethod
    def load(self, source) -> Dict[str, str]:
        """Return a mapping with at least *access_key* and *secret_key* entries."""


class CSVCredentialsLoader(BaseCredentialsLoader):
    """Loads credentials from a CSV file with flexible header names."""

    HEADER_ALIASES = {
        "aws_access_key_id": {"aws_access_key_id", "access_key_id", "access key id"},
        "aws_secret_access_key": {
            "aws_secret_access_key",
            "secret_access_key",
            "secret access key",
        },
    }

    def load(self, source: Path) -> Dict[str, str]:
        with Path(source).expanduser().open(newline="") as fh:
            row = next(csv.DictReader(fh))
        norm = {k.strip().lstrip("\ufeff").lower(): v.strip() for k, v in row.items()}
        try:
            return {
                "aws_access_key_id": self._find(norm, "aws_access_key_id"),
                "aws_secret_access_key": self._find(norm, "aws_secret_access_key"),
            }
        except KeyError as err:
            raise KeyError("Required credential field not found in CSV") from err

    @classmethod
    def _find(cls, mapping: Dict[str, str], canonical: str) -> str:
        for alias in cls.HEADER_ALIASES[canonical]:
            if alias in mapping and mapping[alias]:
                return mapping[alias]
        raise KeyError(canonical)


class EnvCredentialsLoader(BaseCredentialsLoader):
    """Loads credentials from environment variables."""

    def load(self, source: str) -> Dict[str, str]:
        return {
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        }


def load_credentials(source) -> Dict[str, str]:
    """Dispatch to the appropriate loader based on *source* type or suffix."""
    if source == "env":
        return EnvCredentialsLoader().load(source)

    path = Path(source)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return CSVCredentialsLoader().load(path)
    raise ValueError(f"No loader for source: {source}")
