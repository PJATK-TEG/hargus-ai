"""Scoring activity — fully deterministic, no LLM."""
from __future__ import annotations

import logging

from temporalio import activity

from hargus_api.temporal.models import ConsolidatedFacts, ScoringResult

logger = logging.getLogger(__name__)

_SEVERITY_PENALTY = {"low": 0.0, "medium": 10.0, "high": 25.0}
_COMMUNICATION_SCORE = {"strong": 100.0, "adequate": 65.0, "weak": 30.0, "unknown": 50.0}


@activity.defn
async def score_candidate_activity(facts: ConsolidatedFacts) -> ScoringResult:
    """Compute a deterministic score from consolidated facts."""
    # Skill match (0–100); preferred skills add up to 10 bonus points
    skill_score = round(facts.skill_coverage * 100, 1)
    preferred_bonus = round(facts.preferred_coverage * 10.0, 1)
    skill_score = min(skill_score + preferred_bonus, 100.0)

    # Experience score (0–100) — linear up to required years, capped at 100
    # Cap self-reported years at the sum-of-entries derived value to prevent inflation
    required_years = facts.rubric.experience_years_min or 1
    entries = facts.candidate_facts.experience_entries
    if entries:
        derived_years = sum(e.duration_months for e in entries) / 12.0
        actual_years = min(facts.candidate_facts.total_years_experience, derived_years)
    else:
        actual_years = facts.candidate_facts.total_years_experience
    exp_score = round(min(actual_years / required_years, 1.0) * 100, 1)

    # Interview score (0–100)
    quality = facts.interview_findings.communication_quality
    interview_score = _COMMUNICATION_SCORE.get(quality, 50.0)
    # Bonus for behavioral examples
    if facts.interview_findings.behavioral_examples:
        interview_score = min(interview_score + 5.0, 100.0)

    # Risk penalty
    severity = facts.risk_flags.overall_severity
    penalty = _SEVERITY_PENALTY.get(severity, 0.0)
    if facts.risk_flags.has_critical_issues:
        penalty = max(penalty, 40.0)

    # Weighted overall (skill 40%, experience 35%, interview 25%, minus penalty)
    overall = (skill_score * 0.40 + exp_score * 0.35 + interview_score * 0.25) - penalty
    overall = round(max(0.0, min(overall, 100.0)), 1)

    if overall >= 75:
        recommendation = "strong_match"
    elif overall >= 55:
        recommendation = "possible"
    elif overall >= 35:
        recommendation = "weak"
    else:
        recommendation = "manual_review"

    if facts.risk_flags.has_critical_issues:
        recommendation = "manual_review"

    rationale = (
        f"Skill coverage {skill_score:.0f}%, experience {exp_score:.0f}%, "
        f"interview {interview_score:.0f}%, risk penalty -{penalty:.0f}pts."
    )

    logger.info(
        "score: candidate=%s overall=%.1f recommendation=%s",
        facts.candidate_id,
        overall,
        recommendation,
    )

    return ScoringResult(
        overall_score=overall,
        skill_match_score=skill_score,
        experience_score=exp_score,
        interview_score=interview_score,
        risk_penalty=penalty,
        recommendation=recommendation,  # type: ignore[arg-type]
        score_breakdown={
            "skill": skill_score,
            "preferred_bonus": preferred_bonus,
            "experience": exp_score,
            "interview": interview_score,
            "penalty": -penalty,
        },
        rationale=rationale,
    )
