"""Shared pytest fixtures for the Hargus AI test suite."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from hargus_api.temporal.models import (
    BehavioralExample,
    CandidateFacts,
    ConsolidatedFacts,
    ExperienceEntry,
    InterviewFindings,
    JobRubric,
    RiskFlag,
    RiskFlags,
)


# ---------------------------------------------------------------------------
# Mock LLM helpers
# ---------------------------------------------------------------------------


def make_mock_llm(json_response: dict[str, Any]) -> MagicMock:
    """Return a mock BaseChatModel whose ainvoke returns a JSON-serialisable dict.

    The chain in build_json_chain is: prompt | llm | JsonOutputParser.
    We mock at the LLM level — the chain calls llm.ainvoke and JsonOutputParser
    tries to parse the content. We short-circuit by making ainvoke return the
    dict directly (JsonOutputParser accepts a dict passthrough).
    """
    import json

    from langchain_core.messages import AIMessage

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=json.dumps(json_response)))
    # Required for LangChain chain composition
    llm.bind = MagicMock(return_value=llm)
    return llm


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def strong_candidate_facts() -> CandidateFacts:
    return CandidateFacts(
        skills=["Python", "Go", "PostgreSQL", "Redis", "Kafka", "Distributed Systems"],
        experience_entries=[
            ExperienceEntry(
                company="Stripe",
                role="Senior Software Engineer",
                duration_months=36,
                description="Led payment processing pipeline handling millions of TPS.",
            )
        ],
        total_years_experience=8.0,
        education=[{"institution": "Stanford", "degree": "M.S.", "field": "CS", "year": "2017"}],
        certifications=["AWS Solutions Architect"],
        domain_signals=["fintech", "distributed systems"],
        confidence=0.95,
    )


@pytest.fixture()
def weak_candidate_facts() -> CandidateFacts:
    return CandidateFacts(
        skills=["HTML", "CSS"],
        experience_entries=[
            ExperienceEntry(
                company="Startup X",
                role="Junior Developer",
                duration_months=6,
                description="Built landing pages.",
            )
        ],
        total_years_experience=0.5,
        education=[],
        certifications=[],
        domain_signals=[],
        confidence=0.4,
    )


@pytest.fixture()
def backend_rubric() -> JobRubric:
    return JobRubric(
        required_skills=["Python", "PostgreSQL", "Distributed Systems"],
        preferred_skills=["Go", "Redis"],
        experience_years_min=5,
        key_responsibilities=["Design scalable APIs", "Own database schema"],
        seniority_level="senior",
        domain_keywords=["backend", "microservices"],
    )


@pytest.fixture()
def strong_interview() -> InterviewFindings:
    return InterviewFindings(
        communication_quality="strong",
        strengths=["Clear technical explanations", "Structured thinking"],
        concerns=[],
        behavioral_examples=[
            BehavioralExample(
                competency="leadership",
                example="Led a team of 5 to redesign the payments pipeline.",
                is_strength=True,
            )
        ],
        overall_impression="Exceptional candidate with strong technical depth.",
    )


@pytest.fixture()
def no_risk() -> RiskFlags:
    return RiskFlags(flags=[], overall_severity="low", has_critical_issues=False)


@pytest.fixture()
def high_risk() -> RiskFlags:
    return RiskFlags(
        flags=[
            RiskFlag(severity="high", category="contradiction", description="Employment gap of 2 years unexplained.")
        ],
        overall_severity="high",
        has_critical_issues=True,
    )


@pytest.fixture()
def strong_consolidated(
    backend_rubric: JobRubric,
    strong_candidate_facts: CandidateFacts,
    strong_interview: InterviewFindings,
    no_risk: RiskFlags,
) -> ConsolidatedFacts:
    required = set(s.lower() for s in backend_rubric.required_skills)
    candidate_skills = set(s.lower() for s in strong_candidate_facts.skills)
    matched = sorted(required & candidate_skills)
    missing = sorted(required - candidate_skills)
    return ConsolidatedFacts(
        workflow_run_id="test-run-001",
        candidate_id="c1",
        vacancy_id="v1",
        rubric=backend_rubric,
        candidate_facts=strong_candidate_facts,
        interview_findings=strong_interview,
        risk_flags=no_risk,
        matched_skills=matched,
        missing_skills=missing,
        skill_coverage=len(matched) / len(required),
    )
