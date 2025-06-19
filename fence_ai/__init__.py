"""Fence AI core package.

Convenience re-exports so that callers can simply do::

    from fence_ai import S3Access, S3AccessError
"""

from .s3_access import S3Access, S3AccessError
from .config_core import Config  # noqa: F401, E402

__all__ = [
    "S3Access",
    "S3AccessError",
    "Config",
]
