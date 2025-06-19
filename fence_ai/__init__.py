"""Fence AI core package.

Convenience re-exports so that callers can simply do::

    from fence_ai import S3Access, S3AccessError
"""

from fence_ai.storage.s3_access import S3Access, S3AccessError
from fence_ai.core.config import Config  # noqa: F401, E402

__all__ = [
    "S3Access",
    "S3AccessError",
    "Config",
]
