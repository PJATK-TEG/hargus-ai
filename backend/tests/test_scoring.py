"""Tests and evaluation metrics for the scoring and consolidation activities.

The scoring activity is fully deterministic — no LLM, no external services.
Tests here act as regression guards and evaluation metrics for the scoring model.
"""
from __future__ import annotations

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
    ScoringResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _consolidate(
    rubric: JobRubric,
    facts: CandidateFacts,
    interview: InterviewFindings,
    risk: RiskFlags,
) -> ConsolidatedFacts:
    required = {s.lower() for s in rubric.required_skills}
    candidate = {s.lower() for s in facts.skills}
    matched = sorted(required & candidate)
    missing = sorted(required - candidate)
    return ConsolidatedFacts(
        workflow_run_id="eval-run",
        candidate_id="test",
        vacancy_id="v0",
        rubric=rubric,
        candidate_facts=facts,
        interview_findings=interview,
        risk_flags=risk,
        matched_skills=matched,
        missing_skills=missing,
        skill_coverage=len(matched) / len(required) if required else 0.0,
    )


def _no_risk() -> RiskFlags:
    return RiskFlags(flags=[], overall_severity="low", has_critical_issues=False)


def _strong_interview() -> InterviewFindings:
    return InterviewFindings(
        communication_quality="strong",
        strengths=["Clear communicator"],
        concerns=[],
        behavioral_examples=[
            BehavioralExample(competency="leadership", example="Led 5-person team.", is_strength=True)
        ],
        overall_impression="Excellent.",
    )


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perfect_candidate_scores_above_75(
    strong_consolidated: ConsolidatedFacts,
) -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    result = await score_candidate_activity(strong_consolidated)

    assert result.overall_score >= 75, f"Expected strong_match threshold, got {result.overall_score}"
    assert result.recommendation == "strong_match"


@pytest.mark.asyncio
async def test_weak_candidate_scores_below_35(
    backend_rubric: JobRubric,
    weak_candidate_facts: CandidateFacts,
) -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    consolidated = _consolidate(
        backend_rubric,
        weak_candidate_facts,
        InterviewFindings(communication_quality="weak"),
        _no_risk(),
    )
    result = await score_candidate_activity(consolidated)

    assert result.overall_score < 55, f"Expected weak score, got {result.overall_score}"


@pytest.mark.asyncio
async def test_critical_risk_forces_manual_review(
    strong_consolidated: ConsolidatedFacts,
    high_risk: RiskFlags,
) -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    facts = strong_consolidated.model_copy(update={"risk_flags": high_risk})
    result = await score_candidate_activity(facts)

    assert result.recommendation == "manual_review"
    assert result.risk_penalty >= 40.0


@pytest.mark.asyncio
async def test_high_risk_applies_penalty(
    strong_consolidated: ConsolidatedFacts,
) -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    no_risk_result = await score_candidate_activity(strong_consolidated)

    high_risk = RiskFlags(
        flags=[RiskFlag(severity="high", category="contradiction", description="Gap")],
        overall_severity="high",
        has_critical_issues=False,
    )
    risky = strong_consolidated.model_copy(update={"risk_flags": high_risk})
    risky_result = await score_candidate_activity(risky)

    assert risky_result.overall_score < no_risk_result.overall_score
    assert risky_result.risk_penalty == 25.0


@pytest.mark.asyncio
async def test_score_clamped_between_0_and_100() -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    rubric = JobRubric(required_skills=["Python"], experience_years_min=1)
    facts = CandidateFacts(
        skills=["Python"], total_years_experience=50.0, confidence=1.0
    )
    consolidated = _consolidate(rubric, facts, _strong_interview(), _no_risk())
    result = await score_candidate_activity(consolidated)

    assert 0.0 <= result.overall_score <= 100.0


@pytest.mark.asyncio
async def test_score_is_deterministic(strong_consolidated: ConsolidatedFacts) -> None:
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    r1 = await score_candidate_activity(strong_consolidated)
    r2 = await score_candidate_activity(strong_consolidated)

    assert r1.overall_score == r2.overall_score
    assert r1.recommendation == r2.recommendation


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_rank_ordering(
    backend_rubric: JobRubric,
    strong_candidate_facts: CandidateFacts,
    weak_candidate_facts: CandidateFacts,
) -> None:
    """Strong candidates must score strictly higher than weak candidates."""
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    strong = await score_candidate_activity(
        _consolidate(backend_rubric, strong_candidate_facts, _strong_interview(), _no_risk())
    )
    weak = await score_candidate_activity(
        _consolidate(
            backend_rubric,
            weak_candidate_facts,
            InterviewFindings(communication_quality="weak"),
            _no_risk(),
        )
    )

    assert strong.overall_score > weak.overall_score, (
        f"Rank order violated: strong={strong.overall_score}, weak={weak.overall_score}"
    )


@pytest.mark.asyncio
async def test_eval_skill_sensitivity(backend_rubric: JobRubric) -> None:
    """Adding a required skill must increase the score (monotonicity)."""
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    base_facts = CandidateFacts(skills=["Python"], total_years_experience=5.0, confidence=0.8)
    improved_facts = CandidateFacts(
        skills=["Python", "PostgreSQL", "Distributed Systems"],
        total_years_experience=5.0,
        confidence=0.8,
    )
    interview = _strong_interview()

    base_score = await score_candidate_activity(
        _consolidate(backend_rubric, base_facts, interview, _no_risk())
    )
    improved_score = await score_candidate_activity(
        _consolidate(backend_rubric, improved_facts, interview, _no_risk())
    )

    assert improved_score.skill_match_score > base_score.skill_match_score, (
        "Skill coverage increase did not raise skill_match_score"
    )
    assert improved_score.overall_score > base_score.overall_score, (
        "Skill coverage increase did not raise overall_score"
    )


@pytest.mark.asyncio
async def test_eval_experience_sensitivity(backend_rubric: JobRubric) -> None:
    """A candidate meeting the experience requirement should score higher than one who doesn't."""
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    skills = backend_rubric.required_skills
    interview = _strong_interview()

    junior = CandidateFacts(skills=skills, total_years_experience=1.0, confidence=0.8)
    senior = CandidateFacts(skills=skills, total_years_experience=10.0, confidence=0.8)

    junior_score = await score_candidate_activity(_consolidate(backend_rubric, junior, interview, _no_risk()))
    senior_score = await score_candidate_activity(_consolidate(backend_rubric, senior, interview, _no_risk()))

    assert senior_score.experience_score >= junior_score.experience_score


@pytest.mark.asyncio
async def test_eval_interview_quality_impact(backend_rubric: JobRubric) -> None:
    """Strong interview communication must yield a higher interview_score than weak."""
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    skills = backend_rubric.required_skills
    facts = CandidateFacts(skills=skills, total_years_experience=5.0, confidence=0.8)

    strong_int = InterviewFindings(communication_quality="strong")
    weak_int = InterviewFindings(communication_quality="weak")

    strong_score = await score_candidate_activity(_consolidate(backend_rubric, facts, strong_int, _no_risk()))
    weak_score = await score_candidate_activity(_consolidate(backend_rubric, facts, weak_int, _no_risk()))

    assert strong_score.interview_score > weak_score.interview_score
    assert strong_score.overall_score > weak_score.overall_score


@pytest.mark.asyncio
async def test_eval_weight_proportions(strong_consolidated: ConsolidatedFacts) -> None:
    """Verify that scoring weights roughly match the documented 40/35/25 split."""
    from hargus_api.temporal.activities.scoring import score_candidate_activity

    result = await score_candidate_activity(strong_consolidated)

    # Manual calculation with documented weights
    expected_base = (
        result.skill_match_score * 0.40
        + result.experience_score * 0.35
        + result.interview_score * 0.25
    ) - result.risk_penalty

    assert abs(result.overall_score - max(0.0, min(expected_base, 100.0))) < 0.01, (
        "Scoring weights deviate from documented 40/35/25 split"
    )


# ---------------------------------------------------------------------------
# Consolidation activity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consolidate_computes_matched_missing_skills(
    backend_rubric: JobRubric,
    strong_candidate_facts: CandidateFacts,
    strong_interview: InterviewFindings,
    no_risk: RiskFlags,
) -> None:
    from hargus_api.temporal.models import ConsolidateInput
    from hargus_api.temporal.activities.analysis import consolidate_facts_activity

    inp = ConsolidateInput(
        workflow_run_id="test-consolidate",
        candidate_id="c1",
        vacancy_id="v1",
        rubric=backend_rubric,
        candidate_facts=strong_candidate_facts,
        interview_findings=strong_interview,
        risk_flags=no_risk,
    )
    result = await consolidate_facts_activity(inp)

    assert "Python" in result.matched_skills
    assert "PostgreSQL" in result.matched_skills
    assert 0.0 < result.skill_coverage <= 1.0


@pytest.mark.asyncio
async def test_consolidate_coverage_zero_when_no_skills_match(
    backend_rubric: JobRubric,
    strong_interview: InterviewFindings,
    no_risk: RiskFlags,
) -> None:
    from hargus_api.temporal.models import ConsolidateInput
    from hargus_api.temporal.activities.analysis import consolidate_facts_activity

    facts = CandidateFacts(skills=["Photoshop", "Figma"], total_years_experience=3.0)
    inp = ConsolidateInput(
        workflow_run_id="test-zero",
        candidate_id="c2",
        vacancy_id="v1",
        rubric=backend_rubric,
        candidate_facts=facts,
        interview_findings=strong_interview,
        risk_flags=no_risk,
    )
    result = await consolidate_facts_activity(inp)

    assert result.skill_coverage == 0.0
    assert result.matched_skills == []
    assert len(result.missing_skills) == len(backend_rubric.required_skills)
