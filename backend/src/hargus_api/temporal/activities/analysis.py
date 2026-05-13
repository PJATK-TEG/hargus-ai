"""Analysis activities: one Temporal activity per LangGraph agent."""
from __future__ import annotations

import logging

from langchain_postgres import PGVector
from temporalio import activity

from hargus_api.ai.agents.base import truncate
from hargus_api.ai.agents.candidate_agent import run_candidate_agent
from hargus_api.ai.agents.consistency_agent import run_consistency_agent
from hargus_api.ai.agents.interview_agent import run_interview_agent
from hargus_api.ai.agents.jd_agent import run_jd_agent
from hargus_api.ai.config import get_rag_k
from hargus_api.ai.llm.factory import get_embeddings, get_llm
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.services.candidate_service import get_vacancy
from hargus_api.temporal.activities.embedding import _pgvector_engine
from hargus_api.temporal.models import (
    AgentActivityInput,
    BehavioralExample,
    CandidateFacts,
    ConsolidatedFacts,
    ConsolidateInput,
    ExperienceEntry,
    InterviewFindings,
    JobRubric,
    RiskFlag,
    RiskFlags,
)

logger = logging.getLogger(__name__)


def _get(d: dict, key: str, default):
    """Like dict.get but also substitutes the default when the value is None."""
    v = d.get(key)
    return v if v is not None else default


def _cv_text(inp: AgentActivityInput) -> str:
    return "\n\n---\n\n".join(
        d.raw_text for d in inp.documents if d.source_type == "cv"
    )


def _transcript_text(inp: AgentActivityInput) -> str:
    return "\n\n---\n\n".join(
        d.raw_text for d in inp.documents if d.source_type == "transcript"
    )


def _all_text(inp: AgentActivityInput) -> str:
    return "\n\n---\n\n".join(d.raw_text for d in inp.documents)


async def _vacancy_description(inp: AgentActivityInput) -> str:
    """Fetch vacancy description from the service layer."""
    if not inp.vacancy_id:
        return ""
    async with AsyncSessionLocal() as session:
        vacancy = await get_vacancy(session, inp.vacancy_id)
    if vacancy is None:
        return f"Vacancy ID: {inp.vacancy_id} (description unavailable)"
    requirements = ", ".join(vacancy.requirements)
    return (
        f"Title: {vacancy.title}\n"
        f"Department: {vacancy.department}\n"
        f"Location: {vacancy.location}\n"
        f"Type: {vacancy.type}\n"
        f"Description: {vacancy.description}\n"
        f"Requirements: {requirements}"
    )


async def _rag_context(collection_name: str, query: str) -> str:
    """Return top-k relevant chunks from pgvector as a single string."""
    if not collection_name:
        return ""
    try:
        store = PGVector(
            embeddings=get_embeddings(),
            collection_name=collection_name,
            connection=_pgvector_engine(),
            use_jsonb=True,
        )
        chunks = await store.asimilarity_search(query, k=get_rag_k())
        return "\n\n---\n\n".join(c.page_content for c in chunks)
    except Exception:
        logger.warning("RAG retrieval failed for collection %s", collection_name)
        return ""


# ── JD Agent activity ─────────────────────────────────────────────────────────


@activity.defn
async def run_jd_analysis_activity(inp: AgentActivityInput) -> JobRubric:
    activity.heartbeat()
    vac_desc = await _vacancy_description(inp)
    raw = await run_jd_agent(get_llm(), vac_desc)
    return JobRubric(
        required_skills=_get(raw, "required_skills", []),
        preferred_skills=_get(raw, "preferred_skills", []),
        experience_years_min=_get(raw, "experience_years_min", 0),
        key_responsibilities=_get(raw, "key_responsibilities", []),
        seniority_level=_get(raw, "seniority_level", ""),
        domain_keywords=_get(raw, "domain_keywords", []),
    )


# ── Candidate Extraction activity ─────────────────────────────────────────────


@activity.defn
async def run_candidate_extraction_activity(inp: AgentActivityInput) -> CandidateFacts:
    activity.heartbeat()
    base = truncate(_cv_text(inp) or _all_text(inp), 6000)
    extra = await _rag_context(
        inp.collection_name,
        "technical skills work experience projects achievements certifications",
    )
    if extra:
        base += f"\n\n## Retrieved Context\n\n{extra}"
    raw = await run_candidate_agent(get_llm(), base)
    entries = [
        ExperienceEntry(
            company=_get(e, "company", ""),
            role=_get(e, "role", ""),
            duration_months=int(_get(e, "duration_months", 0)),
            description=_get(e, "description", ""),
        )
        for e in _get(raw, "experience_entries", [])
    ]
    return CandidateFacts(
        skills=_get(raw, "skills", []),
        experience_entries=entries,
        total_years_experience=float(_get(raw, "total_years_experience", 0.0)),
        education=_get(raw, "education", []),
        certifications=_get(raw, "certifications", []),
        domain_signals=_get(raw, "domain_signals", []),
        confidence=float(_get(raw, "confidence", 0.0)),
    )


# ── Interview Insight activity ────────────────────────────────────────────────


@activity.defn
async def run_interview_insight_activity(inp: AgentActivityInput) -> InterviewFindings:
    activity.heartbeat()
    raw = await run_interview_agent(get_llm(), _transcript_text(inp))
    examples = [
        BehavioralExample(
            competency=_get(e, "competency", ""),
            example=_get(e, "example", ""),
            is_strength=bool(_get(e, "is_strength", _get(e, "strength", True))),
        )
        for e in _get(raw, "behavioral_examples", [])
    ]
    quality = _get(raw, "communication_quality", "unknown")
    if quality not in ("strong", "adequate", "weak", "unknown"):
        quality = "unknown"
    return InterviewFindings(
        communication_quality=quality,  # type: ignore[arg-type]
        strengths=_get(raw, "strengths", []),
        concerns=_get(raw, "concerns", []),
        behavioral_examples=examples,
        overall_impression=_get(raw, "overall_impression", ""),
    )


# ── Consistency / Risk activity ───────────────────────────────────────────────


@activity.defn
async def run_consistency_check_activity(inp: AgentActivityInput) -> RiskFlags:
    activity.heartbeat()
    base = truncate(_all_text(inp), 6000)
    extra = await _rag_context(
        inp.collection_name,
        "employment gap dates inconsistency contradiction timeline discrepancy",
    )
    if extra:
        base += f"\n\n## Retrieved Context\n\n{extra}"
    raw = await run_consistency_agent(get_llm(), base)
    flags = [
        RiskFlag(
            severity=_get(f, "severity", "low"),  # type: ignore[arg-type]
            category=_get(f, "category", "other"),  # type: ignore[arg-type]
            description=_get(f, "description", ""),
        )
        for f in _get(raw, "flags", [])
    ]
    severity = _get(raw, "overall_severity", "low")
    if severity not in ("low", "medium", "high"):
        severity = "low"
    return RiskFlags(
        flags=flags,
        overall_severity=severity,  # type: ignore[arg-type]
        has_critical_issues=bool(_get(raw, "has_critical_issues", False)),
    )


# ── Consolidation activity ────────────────────────────────────────────────────


@activity.defn
async def consolidate_facts_activity(inp: ConsolidateInput) -> ConsolidatedFacts:
    """Merge agent outputs and compute skill coverage — no LLM needed."""
    required = set(s.lower() for s in inp.rubric.required_skills)
    candidate_skills = set(s.lower() for s in inp.candidate_facts.skills)

    matched = sorted(required & candidate_skills)
    missing = sorted(required - candidate_skills)
    coverage = len(matched) / len(required) if required else 0.0

    return ConsolidatedFacts(
        workflow_run_id=inp.workflow_run_id,
        candidate_id=inp.candidate_id,
        vacancy_id=inp.vacancy_id,
        rubric=inp.rubric,
        candidate_facts=inp.candidate_facts,
        interview_findings=inp.interview_findings,
        risk_flags=inp.risk_flags,
        matched_skills=matched,
        missing_skills=missing,
        skill_coverage=round(coverage, 3),
    )
