from __future__ import annotations

import asyncio
from pathlib import Path

import aiofiles

from hargus_api.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, base_path: str | Path) -> None:
        self._base = Path(base_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self._base / key).resolve()
        if not str(path).startswith(str(self._base)):
            raise ValueError(f"Path traversal detected for key: {key!r}")
        return path

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._resolve(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return key

    async def download(self, key: str) -> bytes:
        path = self._resolve(key)
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._resolve(key).exists)

    async def list(self, prefix: str) -> list[str]:
        base = (self._base / prefix).resolve()
        if not base.exists():
            return []
        return [
            str(p.relative_to(self._base))
            for p in base.rglob("*")
            if p.is_file()
        ]

    def public_url(self, key: str) -> str:
        return str(self._resolve(key))
