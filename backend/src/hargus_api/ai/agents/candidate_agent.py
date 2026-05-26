"""Candidate Extraction Agent — extracts skills, experience, education from CV text."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are an expert CV and interview parser. Extract structured candidate information from all provided documents.

Return ONLY valid JSON matching this exact structure:
{
  "skills": ["list of individual technical skills"],
  "experience_entries": [
    {"company": "Name", "role": "Title", "from": "Jan 2020", "to": "Mar 2022", "duration_months": 26, "description": "brief summary"}
  ],
  "total_years_experience": 5.5,
  "education": [
    {"institution": "University", "degree": "Bachelor", "field": "Computer Science", "year": "2018"}
  ],
  "certifications": ["AWS Certified Solutions Architect"],
  "domain_signals": ["fintech", "distributed systems"],
  "confidence": 0.9
}

Rules for the "skills" field:
- List each skill as a single, atomic, canonical term (e.g. "Python", "Docker", "PostgreSQL")
- Split compound forms: "Python/Django" -> ["Python", "Django"]; "Docker & Kubernetes" -> ["Docker", "Kubernetes"]
- Omit version numbers: write "Python" not "Python 3.9"; "React" not "React 18"
- Use industry-standard names, not prose: "Docker" not "Docker containers"; "React" not "React framework"
- Extract skills from ALL documents provided (CV, transcripts, notes), not just the CV
- Do NOT include generic soft skills like "communication" or "teamwork" in skills -- those belong in domain_signals

Set confidence 0.0 (very uncertain) to 1.0 (very confident) based on data quality and completeness."""

_HUMAN = "Candidate Documents:\n{documents}\n\nExtract candidate information as JSON."

_FALLBACK: dict[str, Any] = {
    "skills": [],
    "experience_entries": [],
    "total_years_experience": 0.0,
    "education": [],
    "certifications": [],
    "domain_signals": [],
    "confidence": 0.0,
}


class _State(TypedDict):
    documents: str
    parsed_result: dict[str, Any]
    error: str | None


def build_candidate_agent(
    llm: BaseChatModel,
    trace_metadata: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)
    invoke_cfg = traced_config(
        "candidate_extraction",
        trace_metadata,
        session_id=session_id,
        user_id=user_id,
    )

    async def extract(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {"documents": truncate(state["documents"], 40000)},
                config=invoke_cfg,
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Candidate agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "extraction_failed"}

    g = StateGraph(_State)
    g.add_node("extract", extract)
    g.set_entry_point("extract")
    g.add_edge("extract", END)
    return g.compile()


async def run_candidate_agent(
    llm: BaseChatModel,
    documents_text: str,
    *,
    trace_metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    graph = build_candidate_agent(
        llm, trace_metadata, session_id=session_id, user_id=user_id
    )
    result = await graph.ainvoke(
        {"documents": documents_text, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
