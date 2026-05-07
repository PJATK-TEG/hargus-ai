import asyncio
import logging

from temporalio.worker import Worker

from hargus_api.config import get_settings
from hargus_api.temporal.activities.analysis import (
    consolidate_facts_activity,
    run_candidate_extraction_activity,
    run_consistency_check_activity,
    run_interview_insight_activity,
    run_jd_analysis_activity,
)
from hargus_api.temporal.activities.embedding import chunk_and_embed_activity
from hargus_api.temporal.activities.ingestion import (
    load_documents_activity,
    parse_documents_activity,
)
from hargus_api.temporal.activities.reporting import (
    draft_report_activity,
    mark_task_failed_activity,
    render_pdf_activity,
    store_and_notify_activity,
)
from hargus_api.temporal.activities.scoring import score_candidate_activity
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.workflows.ai_tasks import AiTaskWorkflow
from hargus_api.temporal.workflows.candidate_analysis import CandidateAnalysisWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        workflows=[
            CandidateAnalysisWorkflow,
            AiTaskWorkflow,  # kept for backwards compat
        ],
        activities=[
            # Ingestion
            load_documents_activity,
            parse_documents_activity,
            # Embedding
            chunk_and_embed_activity,
            # Analysis
            run_jd_analysis_activity,
            run_candidate_extraction_activity,
            run_interview_insight_activity,
            run_consistency_check_activity,
            consolidate_facts_activity,
            # Scoring
            score_candidate_activity,
            # Reporting
            draft_report_activity,
            render_pdf_activity,
            store_and_notify_activity,
            mark_task_failed_activity,
        ],
    )

    logger.info(
        "Worker started — queue=%s temporal=%s",
        settings.temporal_task_queue,
        settings.temporal_server_url,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
