from __future__ import annotations

from temporalio import activity

from hargus_api.schemas.domain import AiTaskRequest


@activity.defn
async def store_stub_ai_result(request: AiTaskRequest) -> dict[str, str]:
    return {
        "message": "Temporal stub executed. Replace this activity with your real AI flow later.",
        "taskType": request.type,
    }
