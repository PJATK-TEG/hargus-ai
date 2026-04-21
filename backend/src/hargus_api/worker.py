import asyncio
import logging

from temporalio.worker import Worker

from hargus_api.config import get_settings
from hargus_api.temporal.activities.ai_tasks import store_stub_ai_result
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.workflows.ai_tasks import AiTaskWorkflow

logger = logging.getLogger("hargus_api.worker")


async def connect_temporal_with_retry(
    max_attempts: int = 5,
    retry_delay_seconds: float = 3.0,
):
    settings = get_settings()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            client = await create_temporal_client(settings)
            logger.info(
                "Connected to Temporal server %s on attempt %s",
                settings.temporal_server_url,
                attempt,
            )
            return client, settings
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "Temporal connection failed (attempt %s/%s) to %s: %s",
                attempt,
                max_attempts,
                settings.temporal_server_url,
                exc,
            )
            if attempt < max_attempts:
                await asyncio.sleep(retry_delay_seconds)

    logger.error(
        "Could not connect to Temporal server %s after %s attempts. "
        "Worker is exiting. Ensure Temporal is reachable before starting the worker.",
        settings.temporal_server_url,
        max_attempts,
    )
    raise RuntimeError("Failed to connect to Temporal server") from last_error


async def main() -> None:
    client, settings = await connect_temporal_with_retry()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AiTaskWorkflow],
        activities=[store_stub_ai_result],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
