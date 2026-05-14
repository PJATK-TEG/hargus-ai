"""Analysis activities: one Temporal activity per LangGraph agent."""
from __future__ import annotations

import logging
from typing import Any

from langchain_postgres import PGVector
from temporalio import activity

from hargus_api.ai.agents.base import truncate
from hargus_api.ai.agents.candidate_agent import run_candidate_agent
from hargus_api.ai.agents.consistency_agent import run_consistency_agent
from hargus_api.ai.agents.interview_agent import run_interview_agent
from hargus_api.ai.agents.jd_agent import run_jd_agent
from hargus_api.ai.config import get_rag_k
from hargus_api.ai.llm.factory import get_embeddings, get_llm
from hargus_api.ai.tracing import record_score
from hargus_api.config import get_settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.services.candidate_service import get_vacancy
from hargus_api.temporal.activities.embedding import _pgvector_engine
from hargus_api.temporal.activity_utils import heartbeat_while
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


def _analysis_trace_metadata(inp: AgentActivityInput) -> dict[str, Any]:
    """Compact Langfuse metadata: pipeline context without document bodies."""
    types = [d.source_type for d in inp.documents]
    vid = (inp.vacancy_id or "").strip()
    settings = get_settings()
    return {
        "workflow_run_id": inp.workflow_run_id,
        "candidate_id": inp.candidate_id,
        # Langfuse propagated metadata prefers string values.
        "vacancy_set": str(bool(vid)),
        "rag_collection": str(bool((inp.collection_name or "").strip())),
        "doc_count": str(len(inp.documents)),
        "has_cv": str("cv" in types),
        "has_transcript": str("transcript" in types),
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


def _get(d: dict, key: str, default):
    """Like dict.get but also substitutes the default when the value is None."""
    v = d.get(key)
    return v if v is not None else default


class _CoercionCounter:
    """Lightweight counter for tracking how often a field was defaulted/coerced.

    A coercion is any time strict Pydantic-bound output had to be substituted
    because the LLM returned missing/invalid data.
    """

    __slots__ = ("count",)

    def __init__(self) -> None:
        self.count = 0

    def get(self, d: dict, key: str, default: Any) -> Any:
        v = d.get(key)
        if v is None:
            self.count += 1
            return default
        return v

    def bump(self, n: int = 1) -> None:
        self.count += n


def _normalize_education_entries(raw: Any, c: _CoercionCounter) -> list[dict[str, str]]:
    """Coerce LLM JSON to ``list[dict[str, str]]`` for ``CandidateFacts.education``.

    Models often return ``year`` as a number; Pydantic expects strings for all values.
    """
    if not isinstance(raw, list):
        c.bump()
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            c.bump()
            continue
        row: dict[str, str] = {}
        for key, val in item.items():
            sk = str(key)
            if val is None:
                c.bump()
                row[sk] = ""
            elif isinstance(val, (dict, list)):
                c.bump()
                row[sk] = ""
            elif isinstance(val, str):
                row[sk] = val.strip()
            else:
                c.bump()
                row[sk] = str(val).strip()
        out.append(row)
    return out


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
    raw = await heartbeat_while(
        run_jd_agent(
            get_llm(),
            vac_desc,
            trace_metadata=_analysis_trace_metadata(inp),
            session_id=inp.workflow_run_id,
            user_id=inp.candidate_id,
        )
    )
    c = _CoercionCounter()
    rubric = JobRubric(
        required_skills=c.get(raw, "required_skills", []),
        preferred_skills=c.get(raw, "preferred_skills", []),
        experience_years_min=c.get(raw, "experience_years_min", 0),
        key_responsibilities=c.get(raw, "key_responsibilities", []),
        seniority_level=c.get(raw, "seniority_level", ""),
        domain_keywords=c.get(raw, "domain_keywords", []),
    )
    record_score(
        "schema_coercion_jd",
        float(c.count),
        session_id=inp.workflow_run_id,
        comment=f"defaulted {c.count} field(s) on JobRubric",
    )
    return rubric


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
    raw = await heartbeat_while(
        run_candidate_agent(
            get_llm(),
            base,
            trace_metadata=_analysis_trace_metadata(inp),
            session_id=inp.workflow_run_id,
            user_id=inp.candidate_id,
        )
    )
    c = _CoercionCounter()
    entries = [
        ExperienceEntry(
            company=c.get(e, "company", ""),
            role=c.get(e, "role", ""),
            duration_months=int(c.get(e, "duration_months", 0)),
            description=c.get(e, "description", ""),
        )
        for e in c.get(raw, "experience_entries", [])
    ]
    facts = CandidateFacts(
        skills=c.get(raw, "skills", []),
        experience_entries=entries,
        total_years_experience=float(c.get(raw, "total_years_experience", 0.0)),
        education=_normalize_education_entries(c.get(raw, "education", []), c),
        certifications=c.get(raw, "certifications", []),
        domain_signals=c.get(raw, "domain_signals", []),
        confidence=float(c.get(raw, "confidence", 0.0)),
    )
    record_score(
        "schema_coercion_candidate",
        float(c.count),
        session_id=inp.workflow_run_id,
        comment=f"defaulted {c.count} field(s) on CandidateFacts",
    )
    return facts


# ── Interview Insight activity ────────────────────────────────────────────────


@activity.defn
async def run_interview_insight_activity(inp: AgentActivityInput) -> InterviewFindings:
    activity.heartbeat()
    raw = await heartbeat_while(
        run_interview_agent(
            get_llm(),
            _transcript_text(inp),
            trace_metadata=_analysis_trace_metadata(inp),
            session_id=inp.workflow_run_id,
            user_id=inp.candidate_id,
        )
    )
    c = _CoercionCounter()
    examples = [
        BehavioralExample(
            competency=c.get(e, "competency", ""),
            example=c.get(e, "example", ""),
            is_strength=bool(c.get(e, "is_strength", c.get(e, "strength", True))),
        )
        for e in c.get(raw, "behavioral_examples", [])
    ]
    quality = c.get(raw, "communication_quality", "unknown")
    if quality not in ("strong", "adequate", "weak", "unknown"):
        c.bump()
        quality = "unknown"
    findings = InterviewFindings(
        communication_quality=quality,  # type: ignore[arg-type]
        strengths=c.get(raw, "strengths", []),
        concerns=c.get(raw, "concerns", []),
        behavioral_examples=examples,
        overall_impression=c.get(raw, "overall_impression", ""),
    )
    record_score(
        "schema_coercion_interview",
        float(c.count),
        session_id=inp.workflow_run_id,
        comment=f"defaulted {c.count} field(s) on InterviewFindings",
    )
    return findings


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
    raw = await heartbeat_while(
        run_consistency_agent(
            get_llm(),
            base,
            trace_metadata=_analysis_trace_metadata(inp),
            session_id=inp.workflow_run_id,
            user_id=inp.candidate_id,
        )
    )
    allowed_severities = {"low", "medium", "high"}
    allowed_categories = {"gap", "contradiction", "inconsistency", "other"}
    c = _CoercionCounter()

    def _coerce_flag(d: dict) -> RiskFlag:
        sev = str(c.get(d, "severity", "low")).strip().lower()
        cat = str(c.get(d, "category", "other")).strip().lower()
        desc = str(c.get(d, "description", "")).strip()

        # Common LLM mistake: swap/misplace category into severity (e.g. "inconsistency")
        if sev in allowed_categories and cat not in allowed_categories:
            cat = sev
            sev = "low"
            c.bump()

        if sev not in allowed_severities:
            sev = "low"
            c.bump()
        if cat not in allowed_categories:
            cat = "other"
            c.bump()

        return RiskFlag(
            severity=sev,  # type: ignore[arg-type]
            category=cat,  # type: ignore[arg-type]
            description=desc,
        )

    flags = [_coerce_flag(f) for f in c.get(raw, "flags", [])]
    severity = c.get(raw, "overall_severity", "low")
    if severity not in ("low", "medium", "high"):
        c.bump()
        severity = "low"
    risk_flags = RiskFlags(
        flags=flags,
        overall_severity=severity,  # type: ignore[arg-type]
        has_critical_issues=bool(c.get(raw, "has_critical_issues", False)),
    )
    record_score(
        "schema_coercion_consistency",
        float(c.count),
        session_id=inp.workflow_run_id,
        comment=f"defaulted/swapped {c.count} field(s) on RiskFlags",
    )
    return risk_flags


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
