from __future__ import annotations

from functools import lru_cache

from hargus_api.config import get_settings
from hargus_api.storage.base import StorageBackend
from hargus_api.storage.local import LocalStorage
from hargus_api.storage.s3 import S3Storage


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            region=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
        )
    return LocalStorage(base_path=settings.local_storage_path)
