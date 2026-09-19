"""Unit tests for LangGraph agents using mock LLMs.

These tests verify that each agent correctly:
  - Invokes the LLM with the right context
  - Parses a valid JSON response into the expected structure
  - Returns a safe fallback on LLM failure
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class _FixedResponseLLM(BaseChatModel):
    """Minimal BaseChatModel that always returns a fixed JSON payload."""

    response_json: str = "{}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.response_json))]
        )

    @property
    def _llm_type(self) -> str:
        return "fixed-response-mock"


class _FailingLLM(BaseChatModel):
    """Minimal BaseChatModel that always raises."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise RuntimeError("LLM unavailable")

    @property
    def _llm_type(self) -> str:
        return "failing-mock"


def _mock_llm(response: dict) -> BaseChatModel:
    return _FixedResponseLLM(response_json=json.dumps(response))


def _failing_llm() -> BaseChatModel:
    return _FailingLLM()


# ---------------------------------------------------------------------------
# Candidate Extraction Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_agent_parses_skills() -> None:
    from hargus_api.ai.agents.candidate_agent import run_candidate_agent

    response = {
        "skills": ["Python", "PostgreSQL", "Redis"],
        "experience_entries": [
            {"company": "Acme", "role": "Backend Engineer", "duration_months": 24, "description": "API work"}
        ],
        "total_years_experience": 4.0,
        "education": [{"institution": "MIT", "degree": "B.S.", "field": "CS", "year": "2020"}],
        "certifications": ["AWS"],
        "domain_signals": ["fintech"],
        "confidence": 0.85,
    }
    llm = _mock_llm(response)
    result = await run_candidate_agent(llm, "Experienced Python backend developer with 4 years...")

    assert result["skills"] == ["Python", "PostgreSQL", "Redis"]
    assert result["total_years_experience"] == 4.0
    assert result["confidence"] == 0.85
    assert len(result["experience_entries"]) == 1


@pytest.mark.asyncio
async def test_candidate_agent_returns_fallback_on_failure() -> None:
    from hargus_api.ai.agents.candidate_agent import run_candidate_agent

    result = await run_candidate_agent(_failing_llm(), "Some CV text")

    assert result["skills"] == []
    assert result["total_years_experience"] == 0.0
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_candidate_agent_parses_json_after_preamble() -> None:
    """Models often prefix prose; LenientJsonOutputParser must still extract the object."""
    from hargus_api.ai.agents.candidate_agent import run_candidate_agent

    payload = {
        "skills": ["Python"],
        "experience_entries": [],
        "total_years_experience": 8.0,
        "education": [],
        "certifications": [],
        "domain_signals": [],
        "confidence": 0.9,
    }
    wrapped = (
        "Here is the extracted candidate information in JSON format:\n\n"
        + json.dumps(payload)
        + "\n\nNote: confidence reflects CV completeness."
    )
    llm = _FixedResponseLLM(response_json=wrapped)
    result = await run_candidate_agent(llm, "CV text")

    assert result["skills"] == ["Python"]
    assert result["total_years_experience"] == 8.0
    assert result["confidence"] == 0.9


def test_parse_llm_json_fenced_block() -> None:
    from hargus_api.ai.agents.base import parse_llm_json

    text = 'Sure:\n```json\n{"x": 1}\n```\nHope this helps.'
    assert parse_llm_json(text) == {"x": 1}


def test_parse_llm_json_trailing_commas() -> None:
    from hargus_api.ai.agents.base import parse_llm_json

    text = 'Here:\n{"a": 1, "b": [2, ], }\n'
    assert parse_llm_json(text) == {"a": 1, "b": [2]}


# ---------------------------------------------------------------------------
# JD Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jd_agent_extracts_required_skills() -> None:
    from hargus_api.ai.agents.jd_agent import run_jd_agent

    response = {
        "required_skills": ["Python", "PostgreSQL", "Docker"],
        "preferred_skills": ["Go", "Kubernetes"],
        "experience_years_min": 5,
        "key_responsibilities": ["Design APIs", "Own data models"],
        "seniority_level": "senior",
        "domain_keywords": ["backend", "cloud"],
    }
    llm = _mock_llm(response)
    result = await run_jd_agent(llm, "Senior Backend Engineer — 5+ years Python required...")

    assert "Python" in result["required_skills"]
    assert result["experience_years_min"] == 5
    assert result["seniority_level"] == "senior"


@pytest.mark.asyncio
async def test_jd_agent_returns_fallback_on_failure() -> None:
    from hargus_api.ai.agents.jd_agent import run_jd_agent

    result = await run_jd_agent(_failing_llm(), "Job description text")

    assert result["required_skills"] == []
    assert result["experience_years_min"] == 0


# ---------------------------------------------------------------------------
# Interview Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interview_agent_parses_findings() -> None:
    from hargus_api.ai.agents.interview_agent import run_interview_agent

    response = {
        "communication_quality": "strong",
        "strengths": ["Clear explanations", "Structured problem-solving"],
        "concerns": [],
        "behavioral_examples": [
            {"competency": "leadership", "example": "Led redesign of auth system.", "is_strength": True}
        ],
        "overall_impression": "Excellent candidate with strong communication.",
    }
    llm = _mock_llm(response)
    result = await run_interview_agent(llm, "Interviewer: Tell me about a leadership experience...")

    assert result["communication_quality"] == "strong"
    assert len(result["strengths"]) == 2
    assert result["behavioral_examples"][0]["competency"] == "leadership"


@pytest.mark.asyncio
async def test_interview_agent_returns_fallback_on_failure() -> None:
    from hargus_api.ai.agents.interview_agent import run_interview_agent

    result = await run_interview_agent(_failing_llm(), "Transcript text")

    assert result["communication_quality"] == "unknown"
    assert result["strengths"] == []


# ---------------------------------------------------------------------------
# Consistency / Risk Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consistency_agent_detects_risk() -> None:
    from hargus_api.ai.agents.consistency_agent import run_consistency_agent

    response = {
        "flags": [
            {"severity": "medium", "category": "gap", "description": "18-month gap in employment 2021-2022."}
        ],
        "overall_severity": "medium",
        "has_critical_issues": False,
    }
    llm = _mock_llm(response)
    result = await run_consistency_agent(llm, "CV and transcript text with inconsistency...")

    assert len(result["flags"]) == 1
    assert result["flags"][0]["severity"] == "medium"
    assert result["overall_severity"] == "medium"
    assert result["has_critical_issues"] is False


@pytest.mark.asyncio
async def test_consistency_agent_returns_fallback_on_failure() -> None:
    from hargus_api.ai.agents.consistency_agent import run_consistency_agent

    result = await run_consistency_agent(_failing_llm(), "Documents")

    assert result["flags"] == []
    assert result["has_critical_issues"] is False


# ---------------------------------------------------------------------------
# Report Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_agent_includes_recommendation() -> None:
    from hargus_api.ai.agents.report_agent import run_report_agent

    response = {
        "executive_summary": "Strong candidate with excellent Python skills.",
        "sections": [
            {
                "title": "Technical Skills Assessment",
                "content": "Candidate matches all required skills.",
                "evidence": ["Python listed in CV", "PostgreSQL confirmed in interview"],
            }
        ],
        "recommendation": "strong_match",
        "recommendation_rationale": "All required skills present, 8 years experience, no risk flags.",
    }
    llm = _mock_llm(response)
    input_data = {
        "coordinator_prompt": "Evaluate for senior backend role.",
        "job_rubric": '{"required_skills": ["Python"]}',
        "candidate_facts": '{"skills": ["Python"], "total_years_experience": 8}',
        "interview_findings": '{"communication_quality": "strong"}',
        "risk_flags": '{"flags": [], "overall_severity": "low"}',
        "overall_score": 88,
        "recommendation": "strong_match",
        "matched_skills": "Python",
        "missing_skills": "none",
    }
    result = await run_report_agent(llm, input_data)

    assert result["recommendation"] == "strong_match"
    assert len(result["sections"]) == 1
    assert "executive_summary" in result


@pytest.mark.asyncio
async def test_report_agent_returns_fallback_on_failure() -> None:
    from hargus_api.ai.agents.report_agent import run_report_agent

    result = await run_report_agent(_failing_llm(), {"coordinator_prompt": "", "job_rubric": ""})

    assert result["recommendation"] == "manual_review"


@pytest.mark.asyncio
async def test_report_agent_parses_json_after_preamble() -> None:
    from hargus_api.ai.agents.report_agent import run_report_agent

    response = {
        "executive_summary": "Summary text.",
        "sections": [
            {"title": "Technical Skills Assessment", "content": "Good.", "evidence": ["e1"]}
        ],
        "recommendation": "possible",
        "recommendation_rationale": "Because.",
    }
    wrapped = "Below is the evaluation JSON:\n" + json.dumps(response) + "\nLet me know if you need edits."
    llm = _FixedResponseLLM(response_json=wrapped)
    input_data = {
        "coordinator_prompt": "Test",
        "job_rubric": "{}",
        "candidate_facts": "{}",
        "interview_findings": "{}",
        "risk_flags": "{}",
        "overall_score": 50,
        "recommendation": "manual_review",
        "matched_skills": "",
        "missing_skills": "",
    }
    result = await run_report_agent(llm, input_data)

    assert result["executive_summary"] == "Summary text."
    assert len(result["sections"]) == 1
    assert result["recommendation"] == "possible"


@pytest.mark.asyncio
async def test_report_agent_coordinator_prompt_may_contain_braces() -> None:
    """User/YAML prompts must not break _SYSTEM.format."""
    from hargus_api.ai.agents.report_agent import run_report_agent

    response = {
        "executive_summary": "OK.",
        "sections": [],
        "recommendation": "weak",
        "recommendation_rationale": "Because.",
    }
    llm = _FixedResponseLLM(response_json=json.dumps(response))
    input_data = {
        "coordinator_prompt": "Evaluate {candidate_name} for role {role_id}.",
        "job_rubric": "{}",
        "candidate_facts": "{}",
        "interview_findings": "{}",
        "risk_flags": "{}",
        "overall_score": 10,
        "recommendation": "manual_review",
        "matched_skills": "",
        "missing_skills": "",
    }
    result = await run_report_agent(llm, input_data)

    assert result["executive_summary"] == "OK."
    assert result["recommendation"] == "weak"


# ---------------------------------------------------------------------------
# traced_config: Langfuse session/user_id injection
# ---------------------------------------------------------------------------


def test_traced_config_injects_session_and_user_id() -> None:
    """`session_id`/`user_id` map to the documented Langfuse-langchain shortcut keys."""
    from hargus_api.ai.tracing import traced_config

    cfg = traced_config(
        "jd_extraction",
        {"workflow_run_id": "wf-1", "candidate_id": "c-1"},
        session_id="wf-1",
        user_id="c-1",
    )

    assert cfg["run_name"] == "jd_extraction"
    md = cfg["metadata"]
    assert md["langfuse_session_id"] == "wf-1"
    assert md["langfuse_user_id"] == "c-1"
    assert md["workflow_run_id"] == "wf-1"


def test_traced_config_omits_when_session_user_missing() -> None:
    """No keys are added when callers don't provide session_id/user_id."""
    from hargus_api.ai.tracing import traced_config

    cfg = traced_config("interview_insight", {"foo": "bar"})

    md = cfg.get("metadata", {})
    assert "langfuse_session_id" not in md
    assert "langfuse_user_id" not in md
    assert md.get("foo") == "bar"


def test_traced_config_drops_none_metadata_values() -> None:
    """None-valued metadata is filtered out so Langfuse traces stay tidy."""
    from hargus_api.ai.tracing import traced_config

    cfg = traced_config(
        "consistency_check",
        {"workflow_run_id": "wf-2", "vacancy_id": None},
        session_id="wf-2",
    )

    md = cfg["metadata"]
    assert md["langfuse_session_id"] == "wf-2"
    assert "vacancy_id" not in md


def test_record_score_no_op_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disabled Langfuse must not call get_client; helper is a safe no-op."""
    import hargus_api.ai.tracing as tracing

    settings = tracing.get_settings()
    monkeypatch.setattr(settings, "langfuse_enabled", False)

    called: dict[str, Any] = {"count": 0}

    def _fake_get_client(*args: Any, **kwargs: Any) -> Any:
        called["count"] += 1
        raise AssertionError("get_client should not be called when disabled")

    monkeypatch.setattr("langfuse.get_client", _fake_get_client, raising=False)

    tracing.record_score("schema_coercion_jd", 3.0, session_id="wf-3")
    assert called["count"] == 0
