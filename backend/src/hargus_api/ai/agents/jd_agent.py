"""Job Description Agent — extracts a structured job rubric."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are a technical recruiter assistant. Extract a structured job rubric from the provided job description.

Return ONLY valid JSON matching this exact structure:
{
  "required_skills": ["list of required technical skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience_years_min": 3,
  "key_responsibilities": ["main job duties"],
  "seniority_level": "junior|mid|senior|lead|principal",
  "domain_keywords": ["domain-specific terms and technologies"]
}

Extract only what is explicitly stated or strongly implied. Do not invent details."""

_HUMAN = "Job Description:\n{job_description}\n\nExtract the job rubric as JSON."

_FALLBACK: dict[str, Any] = {
    "required_skills": [],
    "preferred_skills": [],
    "experience_years_min": 0,
    "key_responsibilities": [],
    "seniority_level": "",
    "domain_keywords": [],
}


class _State(TypedDict):
    job_description: str
    parsed_result: dict[str, Any]
    error: str | None


def build_jd_agent(llm: BaseChatModel):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)

    async def extract(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {"job_description": truncate(state["job_description"], 6000)},
                config=traced_config("jd_extraction"),
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("JD agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "extraction_failed"}

    g = StateGraph(_State)
    g.add_node("extract", extract)
    g.set_entry_point("extract")
    g.add_edge("extract", END)
    return g.compile()


async def run_jd_agent(llm: BaseChatModel, job_description: str) -> dict[str, Any]:
    graph = build_jd_agent(llm)
    result = await graph.ainvoke(
        {"job_description": job_description, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
