"""Consistency/Risk Agent — detects contradictions and gaps across all documents."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are a risk analyst reviewing a job candidate's application. Identify inconsistencies, red flags, and gaps across all provided documents.

Return ONLY valid JSON matching this exact structure:
{
  "flags": [
    {
      "severity": "low|medium|high",
      "category": "gap|contradiction|inconsistency|other",
      "description": "Clear description of the issue"
    }
  ],
  "overall_severity": "low|medium|high",
  "has_critical_issues": false
}

Categories:
- gap: Missing expected information (e.g., unexplained employment gap)
- contradiction: Information explicitly contradicts itself across documents
- inconsistency: Slight differences that raise questions
- other: Other notable concerns

Set has_critical_issues=true only for serious issues like fabricated credentials or major contradictions.
Return an empty flags array if no issues are found."""

_HUMAN = (
    "Candidate Documents (all sources combined):\n{all_documents}\n\n"
    "Identify red flags, contradictions, and gaps as JSON."
)

_FALLBACK: dict[str, Any] = {
    "flags": [],
    "overall_severity": "low",
    "has_critical_issues": False,
}


class _State(TypedDict):
    all_documents: str
    parsed_result: dict[str, Any]
    error: str | None


def build_consistency_agent(
    llm: BaseChatModel,
    trace_metadata: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)
    invoke_cfg = traced_config(
        "consistency_check",
        trace_metadata,
        session_id=session_id,
        user_id=user_id,
    )

    async def detect(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {"all_documents": truncate(state["all_documents"], 10000)},
                config=invoke_cfg,
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Consistency agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "detection_failed"}

    g = StateGraph(_State)
    g.add_node("detect", detect)
    g.set_entry_point("detect")
    g.add_edge("detect", END)
    return g.compile()


async def run_consistency_agent(
    llm: BaseChatModel,
    all_documents_text: str,
    *,
    trace_metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    graph = build_consistency_agent(
        llm, trace_metadata, session_id=session_id, user_id=user_id
    )
    result = await graph.ainvoke(
        {"all_documents": all_documents_text, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
