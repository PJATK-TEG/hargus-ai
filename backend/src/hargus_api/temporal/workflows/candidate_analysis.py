"""CandidateAnalysisWorkflow — main Temporal workflow for candidate analysis."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from hargus_api.ai.config import get_chunk_overlap, get_chunk_size
    from hargus_api.temporal.activities.analysis import (
        consolidate_facts_activity,
        run_candidate_extraction_activity,
        run_consistency_check_activity,
        run_interview_insight_activity,
        run_jd_analysis_activity,
        run_profile_extraction_activity,
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
        update_candidate_activity,
        update_candidate_profile_activity,
    )
    from hargus_api.temporal.activities.scoring import score_candidate_activity
    from hargus_api.temporal.models import (
        AgentActivityInput,
        AnalysisWorkflowInput,
        ChunkEmbedInput,
        ConsolidateInput,
        LoadDocumentsInput,
        MarkTaskFailedInput,
        ParseDocumentsInput,
        ReportDraftInput,
        StoreResultInput,
        UpdateCandidateInput,
        UpdateCandidateProfileInput,
    )

# Retry policies
_RETRY_FAST = RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)
_RETRY_LLM = RetryPolicy(maximum_attempts=2, backoff_coefficient=2.0)

# Activity options
_OPTS_FAST = {
    "start_to_close_timeout": timedelta(minutes=5),
    "retry_policy": _RETRY_FAST,
}
_OPTS_IO = {
    "start_to_close_timeout": timedelta(minutes=10),
    "heartbeat_timeout": timedelta(minutes=2),
    "retry_policy": _RETRY_FAST,
}
_OPTS_LLM = {
    "start_to_close_timeout": timedelta(minutes=20),
    # LLM calls can run many minutes; activities heartbeat periodically while awaiting.
    "heartbeat_timeout": timedelta(minutes=10),
    "retry_policy": _RETRY_LLM,
}


@workflow.defn
class CandidateAnalysisWorkflow:
    @workflow.run
    async def run(self, inp: AnalysisWorkflowInput) -> str:
        try:
            # ── Phase 1: Ingestion (sequential) ──────────────────────────────
            loaded = await workflow.execute_activity(
                load_documents_activity,
                LoadDocumentsInput(
                    workflow_run_id=inp.workflow_run_id,
                    candidate_id=inp.candidate_id,
                ),
                **_OPTS_IO,
            )

            parsed = await workflow.execute_activity(
                parse_documents_activity,
                ParseDocumentsInput(
                    workflow_run_id=inp.workflow_run_id,
                    documents=loaded.documents,
                ),
                **_OPTS_IO,
            )

            # ── Phase 2: Embedding ────────────────────────────────────────────
            embedded = await workflow.execute_activity(
                chunk_and_embed_activity,
                ChunkEmbedInput(
                    workflow_run_id=inp.workflow_run_id,
                    candidate_id=inp.candidate_id,
                    documents=parsed.documents,
                    chunk_size=get_chunk_size(),
                    chunk_overlap=get_chunk_overlap(),
                ),
                **_OPTS_IO,
            )

            agent_input = AgentActivityInput(
                workflow_run_id=inp.workflow_run_id,
                candidate_id=inp.candidate_id,
                vacancy_id=inp.vacancy_id,
                collection_name=embedded.collection_name,
                documents=parsed.documents,
            )

            # ── Phase 3: Parallel agent analysis ─────────────────────────────
            rubric, candidate_facts, interview_findings, risk_flags, profile = await asyncio.gather(
                workflow.execute_activity(
                    run_jd_analysis_activity, agent_input, **_OPTS_LLM
                ),
                workflow.execute_activity(
                    run_candidate_extraction_activity, agent_input, **_OPTS_LLM
                ),
                workflow.execute_activity(
                    run_interview_insight_activity, agent_input, **_OPTS_LLM
                ),
                workflow.execute_activity(
                    run_consistency_check_activity, agent_input, **_OPTS_LLM
                ),
                workflow.execute_activity(
                    run_profile_extraction_activity, agent_input, **_OPTS_LLM
                ),
            )

            # ── Phase 3.5: Back-fill candidate profile from CV ────────────────
            await workflow.execute_activity(
                update_candidate_profile_activity,
                UpdateCandidateProfileInput(
                    candidate_id=inp.candidate_id,
                    profile=profile,
                ),
                **_OPTS_FAST,
            )

            # ── Phase 4: Consolidation (deterministic) ────────────────────────
            consolidated = await workflow.execute_activity(
                consolidate_facts_activity,
                ConsolidateInput(
                    workflow_run_id=inp.workflow_run_id,
                    candidate_id=inp.candidate_id,
                    vacancy_id=inp.vacancy_id,
                    rubric=rubric,
                    candidate_facts=candidate_facts,
                    interview_findings=interview_findings,
                    risk_flags=risk_flags,
                ),
                **_OPTS_FAST,
            )

            # ── Phase 5: Scoring (deterministic) ─────────────────────────────
            score = await workflow.execute_activity(
                score_candidate_activity, consolidated, **_OPTS_FAST
            )

            # ── Phase 6: Report drafting (LLM) ───────────────────────────────
            report = await workflow.execute_activity(
                draft_report_activity,
                ReportDraftInput(
                    consolidated=consolidated,
                    score=score,
                    analysis_prompt=inp.analysis_prompt,
                ),
                **_OPTS_LLM,
            )

            # ── Phase 6.5: Persist candidate facts + summary ──────────────────
            await workflow.execute_activity(
                update_candidate_activity,
                UpdateCandidateInput(
                    candidate_id=inp.candidate_id,
                    consolidated=consolidated,
                    score=score,
                    report=report,
                ),
                **_OPTS_FAST,
            )

            # ── Phase 7: PDF rendering ────────────────────────────────────────
            pdf = await workflow.execute_activity(
                render_pdf_activity, report, **_OPTS_FAST
            )

            # ── Phase 8: Persist & notify ─────────────────────────────────────
            rf = consolidated.risk_flags.flags
            n_high = sum(1 for f in rf if f.severity == "high")
            n_med = sum(1 for f in rf if f.severity == "medium")
            n_low = sum(1 for f in rf if f.severity == "low")

            await workflow.execute_activity(
                store_and_notify_activity,
                StoreResultInput(
                    workflow_run_id=inp.workflow_run_id,
                    candidate_id=inp.candidate_id,
                    vacancy_id=inp.vacancy_id,
                    report=report,
                    score=score,
                    pdf=pdf,
                    skill_coverage=consolidated.skill_coverage,
                    risk_flag_count=len(rf),
                    risk_flags_high=n_high,
                    risk_flags_medium=n_med,
                    risk_flags_low=n_low,
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

        return pdf.storage_key
