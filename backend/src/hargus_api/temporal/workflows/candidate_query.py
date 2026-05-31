"""CandidateQueryWorkflow — lightweight Temporal workflow for ad-hoc candidate Q&A."""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from hargus_api.temporal.activities.query import (
        run_candidate_query_activity,
        store_query_result_activity,
    )
    from hargus_api.temporal.activities.reporting import mark_task_failed_activity
    from hargus_api.temporal.models import (
        CandidateQueryActivityInput,
        CandidateQueryInput,
        MarkTaskFailedInput,
        StoreQueryResultInput,
    )

_RETRY_FAST = RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)
_RETRY_LLM = RetryPolicy(maximum_attempts=2, backoff_coefficient=2.0)

_OPTS_FAST = {
    "start_to_close_timeout": timedelta(minutes=5),
    "retry_policy": _RETRY_FAST,
}
_OPTS_LLM = {
    "start_to_close_timeout": timedelta(minutes=20),
    "heartbeat_timeout": timedelta(minutes=10),
    "retry_policy": _RETRY_LLM,
}


@workflow.defn
class CandidateQueryWorkflow:
    @workflow.run
    async def run(self, inp: CandidateQueryInput) -> str:
        try:
            result = await workflow.execute_activity(
                run_candidate_query_activity,
                CandidateQueryActivityInput(
                    workflow_run_id=inp.workflow_run_id,
                    candidate_id=inp.candidate_id,
                    vacancy_id=inp.vacancy_id,
                    query=inp.query,
                    collection_name=inp.collection_name,
                ),
                **_OPTS_LLM,
            )

            await workflow.execute_activity(
                store_query_result_activity,
                StoreQueryResultInput(
                    workflow_run_id=inp.workflow_run_id,
                    result=result,
                ),
                **_OPTS_FAST,
            )
        except Exception as exc:
            await workflow.execute_activity(
                mark_task_failed_activity,
                MarkTaskFailedInput(
                    workflow_run_id=inp.workflow_run_id,
                    error_message=str(exc),
                ),
                **_OPTS_FAST,
            )
            raise

        return result.answer
