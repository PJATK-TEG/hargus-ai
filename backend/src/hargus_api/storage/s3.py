"""S3 storage backend using boto3 wrapped in asyncio.to_thread.

boto3 is already a transitive dependency of langchain-aws, so no extra
package is required. All blocking calls run in a thread pool to keep the
event loop free.
"""
from __future__ import annotations

import asyncio
import functools
from typing import Any

import boto3
from botocore.exceptions import ClientError

from hargus_api.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        endpoint_url: str = "",
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._client: Any = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key_id or None,
            aws_secret_access_key=aws_secret_access_key or None,
            endpoint_url=endpoint_url or None,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                self._client.create_bucket(Bucket=self._bucket)

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}/{key}" if self._prefix else key

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        fn = functools.partial(
            self._client.put_object,
            Bucket=self._bucket,
            Key=self._full_key(key),
            Body=data,
            ContentType=content_type,
        )
        await asyncio.to_thread(fn)
        return key

    async def download(self, key: str) -> bytes:
        fn = functools.partial(
            self._client.get_object,
            Bucket=self._bucket,
            Key=self._full_key(key),
        )
        response = await asyncio.to_thread(fn)
        body = response["Body"]
        return await asyncio.to_thread(body.read)

    async def exists(self, key: str) -> bool:
        fn = functools.partial(
            self._client.head_object,
            Bucket=self._bucket,
            Key=self._full_key(key),
        )
        try:
            await asyncio.to_thread(fn)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    async def list(self, prefix: str) -> list[str]:
        full_prefix = self._full_key(prefix)
        fn = functools.partial(
            self._client.list_objects_v2,
            Bucket=self._bucket,
            Prefix=full_prefix,
        )
        response = await asyncio.to_thread(fn)
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        # Strip the storage prefix so callers get relative keys
        strip = f"{self._prefix}/" if self._prefix else ""
        return [k[len(strip):] if strip and k.startswith(strip) else k for k in keys]

    def public_url(self, key: str) -> str:
        region = self._client.meta.region_name
        return (
            f"https://{self._bucket}.s3.{region}.amazonaws.com/{self._full_key(key)}"
        )
