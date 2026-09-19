"""Reporting activities: draft report, render PDF, store results."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from temporalio import activity

from hargus_api.ai.agents.report_agent import run_report_agent
from hargus_api.ai.config import get_analysis_prompt
from hargus_api.ai.llm.factory import get_llm
from hargus_api.ai.tracing import flush_langfuse, record_score
from hargus_api.config import get_settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.candidate_repo import CandidateRepository
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.repositories.ai_task_repository import normalize_postgres_url
from hargus_api.services.message_service import save_message
from hargus_api.storage.factory import get_storage
from hargus_api.temporal.activity_utils import heartbeat_while
from hargus_api.temporal.models import (
    MarkTaskFailedInput,
    PDFOutput,
    ReportDraft,
    ReportDraftInput,
    ReportSection,
    StoreResultInput,
    UpdateCandidateInput,
    UpdateCandidateProfileInput,
)

logger = logging.getLogger(__name__)
MAX_ERROR_MESSAGE_LENGTH = 2000


def _update_ai_task_status_blocking(
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
            _update_ai_task_status_blocking,
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

    settings = get_settings()
    trace_meta: dict[str, Any] = {
        "workflow_run_id": facts.workflow_run_id,
        "candidate_id": facts.candidate_id,
        "vacancy_set": bool((facts.vacancy_id or "").strip()),
        "skill_coverage": facts.skill_coverage,
        "n_required_skills": len(facts.rubric.required_skills),
        "n_matched_skills": len(facts.matched_skills),
        "comm_quality": facts.interview_findings.communication_quality,
        "n_strengths": len(facts.interview_findings.strengths),
        "n_behavioral_examples": len(facts.interview_findings.behavioral_examples),
        "n_risk_flags": len(facts.risk_flags.flags),
        "risk_severity": facts.risk_flags.overall_severity,
        "overall_score": score.overall_score,
        "recommendation": score.recommendation,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }

    raw = await heartbeat_while(
        run_report_agent(
            get_llm(),
            input_data,
            trace_metadata=trace_meta,
            session_id=facts.workflow_run_id,
            user_id=facts.candidate_id,
        )
    )

    coercions = 0

    def _take(d: dict, key: str, default):
        nonlocal coercions
        v = d.get(key)
        if v is None:
            coercions += 1
            return default
        return v

    sections = [
        ReportSection(
            title=_take(s, "title", ""),
            content=_take(s, "content", ""),
            evidence=_take(s, "evidence", []),
        )
        for s in _take(raw, "sections", [])
    ]

    draft = ReportDraft(
        workflow_run_id=facts.workflow_run_id,
        candidate_id=facts.candidate_id,
        vacancy_id=facts.vacancy_id,
        generated_at=datetime.now(timezone.utc),
        executive_summary=_take(raw, "executive_summary", ""),
        sections=sections,
        recommendation=_take(raw, "recommendation", score.recommendation),
        recommendation_rationale=_take(raw, "recommendation_rationale", score.rationale),
        score=score,
    )
    record_score(
        "schema_coercion_report",
        float(coercions),
        session_id=facts.workflow_run_id,
        comment=f"defaulted {coercions} field(s) on ReportDraft",
    )
    return draft


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


_FALLBACK_SUMMARY = "Report generation failed. Manual review required."


# ── Candidate update ──────────────────────────────────────────────────────────


@activity.defn
async def update_candidate_activity(inp: UpdateCandidateInput) -> None:
    """Persist extracted candidate facts and score to the candidates table."""
    facts = inp.consolidated.candidate_facts
    consolidated = inp.consolidated
    summary = inp.report.executive_summary if inp.report else ""

    skill_score_map: dict[str, int] = {}
    for s in consolidated.matched_skills:
        skill_score_map[s] = 100
    for s in consolidated.preferred_matched:
        if s not in skill_score_map:
            skill_score_map[s] = 75
    for s in consolidated.missing_skills:
        skill_score_map[s] = 0
    skill_scores = [{"skill": s, "score": v} for s, v in skill_score_map.items()]

    parsed_fields = {
        "summary": summary,
        "skills": facts.skills,
        "skillScores": skill_scores,
        "experience": [
            {
                "company": e.company,
                "role": e.role,
                "from": e.from_date or "N/A",
                "to": e.to_date or "N/A",
                "description": e.description,
            }
            for e in facts.experience_entries
        ],
        "education": [
            {
                "institution": e.get("institution", ""),
                "degree": e.get("degree", ""),
                "field": e.get("field", ""),
                "year": e.get("year", ""),
            }
            for e in facts.education
        ],
        "languages": [],
        "certifications": facts.certifications,
        "totalYearsExp": int(facts.total_years_experience),
    }
    async with AsyncSessionLocal() as session:
        await CandidateRepository(session).update_from_analysis(
            inp.candidate_id,
            parsed_fields,
            round(inp.score.overall_score),
            relevancy_score=round(inp.score.skill_match_score),
        )
        await session.commit()
    logger.info("update_candidate: saved facts for candidate %s", inp.candidate_id)


@activity.defn
async def update_candidate_profile_activity(inp: UpdateCandidateProfileInput) -> None:
    p = inp.profile
    async with AsyncSessionLocal() as session:
        await CandidateRepository(session).update_profile(
            inp.candidate_id,
            name=p.name,
            email=p.email,
            phone=p.phone,
            location=p.location,
            linkedin_url=p.linkedin_url,
        )
        await session.commit()
    logger.info("update_candidate_profile: wrote profile for candidate %s", inp.candidate_id)


def _terminal_coercion_count(inp: StoreResultInput) -> int:
    """Heuristic count of coercion-like signals visible in the final report.

    Per-activity ``schema_coercion_*`` scores already give exact upstream counts; this
    terminal signal flags fallback/empty artifacts visible at workflow completion.
    """
    n = 0
    report = inp.report
    if report.executive_summary.strip().startswith(_FALLBACK_SUMMARY):
        n += 1
    if not report.sections:
        n += 1
    if not report.recommendation_rationale.strip():
        n += 1
    if report.recommendation != inp.score.recommendation:
        n += 1
    return n


@activity.defn
async def store_and_notify_activity(inp: StoreResultInput) -> None:
    """Persist the report to the database and mark the workflow run complete."""
    score_val = round(inp.score.overall_score)
    message_content = (
        f"**Analysis complete.** Score: {score_val}/100 · "
        f"Recommendation: {inp.report.recommendation}\n\n"
        f"{inp.report.executive_summary}"
    )

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

    try:
        async with AsyncSessionLocal() as session:
            await save_message(session, inp.candidate_id, "assistant", message_content)
            await session.commit()
    except Exception:
        logger.warning(
            "store_and_notify: could not save assistant message for candidate %s",
            inp.candidate_id,
        )

    await _update_ai_task_status(
        inp.workflow_run_id,
        "completed",
        {
            "pdfStorageKey": inp.pdf.storage_key if inp.pdf else "",
            "summary": message_content,
        },
    )

    logger.info("store_and_notify: completed workflow run %s", inp.workflow_run_id)
    sid = inp.workflow_run_id
    sc = inp.score
    record_score("overall_score", float(sc.overall_score), session_id=sid)
    record_score("skill_coverage", float(inp.skill_coverage), session_id=sid)
    record_score("skill_match_score", float(sc.skill_match_score), session_id=sid)
    record_score("experience_score", float(sc.experience_score), session_id=sid)
    record_score("interview_score", float(sc.interview_score), session_id=sid)
    record_score("risk_penalty", float(sc.risk_penalty), session_id=sid)
    record_score("risk_flag_count", float(inp.risk_flag_count), session_id=sid)
    record_score("risk_flags_high", float(inp.risk_flags_high), session_id=sid)
    record_score("risk_flags_medium", float(inp.risk_flags_medium), session_id=sid)
    record_score("risk_flags_low", float(inp.risk_flags_low), session_id=sid)

    record_score(
        "workflow_completed",
        1.0,
        session_id=sid,
        comment=f"recommendation={sc.recommendation} score={sc.overall_score}",
    )
    record_score(
        "schema_coercion_terminal",
        float(_terminal_coercion_count(inp)),
        session_id=sid,
        comment="empty/fallback signals visible in final ReportDraft",
    )
    flush_langfuse()


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
