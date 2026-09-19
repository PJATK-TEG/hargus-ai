from __future__ import annotations

from temporalio.client import Client

from hargus_api.config import Settings


async def create_temporal_client(settings: Settings) -> Client:
    return await Client.connect(
        settings.temporal_server_url,
        namespace=settings.temporal_namespace,
    )
