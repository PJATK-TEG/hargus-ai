import asyncio

from temporalio.worker import Worker

from hargus_api.config import get_settings
from hargus_api.temporal.activities.ai_tasks import store_stub_ai_result
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.workflows.ai_tasks import AiTaskWorkflow


async def main() -> None:
    settings = get_settings()
    client = await create_temporal_client(settings)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AiTaskWorkflow],
        activities=[store_stub_ai_result],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
