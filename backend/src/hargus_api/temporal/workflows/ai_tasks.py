from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from hargus_api.schemas.domain import AiTaskRequest
    from hargus_api.temporal.activities.ai_tasks import store_stub_ai_result


@workflow.defn
class AiTaskWorkflow:
    @workflow.run
    async def run(self, request: AiTaskRequest) -> dict[str, str]:
        return await workflow.execute_activity(
            store_stub_ai_result,
            request,
            start_to_close_timeout=timedelta(seconds=30),
        )
