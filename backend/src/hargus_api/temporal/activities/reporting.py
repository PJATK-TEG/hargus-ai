"""Reporting activities: draft report, render PDF, store results."""
from __future__ import annotations

import json
import logging
import asyncio
from datetime import datetime, timezone

import psycopg
from temporalio import activity

from hargus_api.ai.agents.report_agent import run_report_agent
from hargus_api.ai.config import get_analysis_prompt
from hargus_api.ai.llm.factory import get_llm
from hargus_api.config import get_settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.repositories.ai_task_repository import normalize_postgres_url
from hargus_api.storage.factory import get_storage
from hargus_api.temporal.models import (
    MarkTaskFailedInput,
    PDFOutput,
    ReportDraft,
    ReportDraftInput,
    ReportSection,
    StoreResultInput,
)

logger = logging.getLogger(__name__)
MAX_ERROR_MESSAGE_LENGTH = 2000


def _update_ai_task_status_sync(
    workflow_run_id: str,
    status: str,
    result: dict[str, str] | None = None,
) -> None:
    url = normalize_postgres_url(get_settings().database_url)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_tasks
                SET status = %s, updated_at = NOW(), result = %s::jsonb
                WHERE workflow_id = %s
                """,
                (
                    status,
                    json.dumps(result) if result is not None else None,
                    workflow_run_id,
                ),
            )
        conn.commit()


async def _update_ai_task_status(
    workflow_run_id: str,
    status: str,
    result: dict[str, str] | None = None,
) -> None:
    try:
        await asyncio.to_thread(
            _update_ai_task_status_sync,
            workflow_run_id,
            status,
            result,
        )
    except Exception:
        logger.exception(
            "Failed to update ai_tasks row for workflow=%s status=%s",
            workflow_run_id,
            status,
        )


# ── Report drafting ───────────────────────────────────────────────────────────


@activity.defn
async def draft_report_activity(inp: ReportDraftInput) -> ReportDraft:
    activity.heartbeat()
    facts = inp.consolidated
    score = inp.score

    coordinator_prompt = inp.analysis_prompt.strip() or get_analysis_prompt()

    input_data = {
        "coordinator_prompt": coordinator_prompt,
        "job_rubric": json.dumps(facts.rubric.model_dump(), indent=2),
        "candidate_facts": json.dumps(facts.candidate_facts.model_dump(), indent=2),
        "interview_findings": json.dumps(facts.interview_findings.model_dump(), indent=2),
        "risk_flags": json.dumps(facts.risk_flags.model_dump(), indent=2),
        "overall_score": score.overall_score,
        "recommendation": score.recommendation,
        "matched_skills": ", ".join(facts.matched_skills) or "none",
        "missing_skills": ", ".join(facts.missing_skills) or "none",
    }

    raw = await run_report_agent(get_llm(), input_data)

    def _get(d: dict, key: str, default):
        v = d.get(key)
        return v if v is not None else default

    sections = [
        ReportSection(
            title=_get(s, "title", ""),
            content=_get(s, "content", ""),
            evidence=_get(s, "evidence", []),
        )
        for s in _get(raw, "sections", [])
    ]

    return ReportDraft(
        workflow_run_id=facts.workflow_run_id,
        candidate_id=facts.candidate_id,
        vacancy_id=facts.vacancy_id,
        generated_at=datetime.now(timezone.utc),
        executive_summary=_get(raw, "executive_summary", ""),
        sections=sections,
        recommendation=_get(raw, "recommendation", score.recommendation),
        recommendation_rationale=_get(raw, "recommendation_rationale", score.rationale),
        score=score,
    )


# ── PDF rendering ─────────────────────────────────────────────────────────────


@activity.defn
async def render_pdf_activity(report: ReportDraft) -> PDFOutput:
    activity.heartbeat()
    from hargus_api.pdf.renderer import render_report_pdf

    pdf_bytes = await render_report_pdf(report)
    storage = get_storage()
    key = f"reports/{report.candidate_id}/{report.workflow_run_id}.pdf"
    await storage.upload(key, pdf_bytes, content_type="application/pdf")

    logger.info(
        "render_pdf: candidate=%s key=%s size=%d",
        report.candidate_id,
        key,
        len(pdf_bytes),
    )
    return PDFOutput(storage_key=key, size_bytes=len(pdf_bytes))


# ── Store & notify ────────────────────────────────────────────────────────────


@activity.defn
async def store_and_notify_activity(inp: StoreResultInput) -> None:
    """Persist the report to the database and mark the workflow run complete."""
    async with AsyncSessionLocal() as session:
        repo = WorkflowRunRepository(session)
        run = await repo.get_by_workflow_id(inp.workflow_run_id)
        if run is None:
            logger.warning("store_and_notify: workflow run not found: %s", inp.workflow_run_id)
        else:
            await repo.save_report(
                workflow_run_id=run.id,
                candidate_id=inp.candidate_id,
                vacancy_id=inp.vacancy_id,
                score_data=inp.score.model_dump(),
                report_snapshot=inp.report.model_dump(mode="json"),
                pdf_storage_key=inp.pdf.storage_key if inp.pdf else None,
            )
            await repo.set_completed(run.id)
            await session.commit()

    await _update_ai_task_status(
        inp.workflow_run_id,
        "completed",
        {"pdfStorageKey": inp.pdf.storage_key if inp.pdf else ""},
    )

    logger.info("store_and_notify: completed workflow run %s", inp.workflow_run_id)


@activity.defn
async def mark_task_failed_activity(inp: MarkTaskFailedInput) -> None:
    async with AsyncSessionLocal() as session:
        repo = WorkflowRunRepository(session)
        run = await repo.get_by_workflow_id(inp.workflow_run_id)
        if run is not None:
            await repo.set_failed(run.id, inp.error_message[:MAX_ERROR_MESSAGE_LENGTH])
            await session.commit()
    await _update_ai_task_status(
        inp.workflow_run_id,
        "failed",
        {"error": inp.error_message[:MAX_ERROR_MESSAGE_LENGTH]},
    )
