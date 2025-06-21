"""Storage provider implementations package."""
from importlib import import_module

# auto-import S3 provider so it registers itself via factory
import_module("storage.providers.s3_backend")
