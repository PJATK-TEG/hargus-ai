from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload data and return the storage key."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data by key."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""

    @abstractmethod
    async def list(self, prefix: str) -> list[str]:
        """Return all keys under the given prefix."""

    @abstractmethod
    def public_url(self, key: str) -> str:
        """Return a URL or filesystem path for the given key."""
