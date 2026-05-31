"""Profile Agent — extracts personal contact information from CV text."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are a CV parser specialized in extracting personal contact information.

Return ONLY valid JSON:
{
  "name": "Full Name or empty string",
  "email": "email@example.com or empty string",
  "phone": "+1-555-0100 or empty string",
  "location": "City, Country or empty string",
  "linkedin_url": "https://linkedin.com/in/... or empty string"
}

Extract exactly what appears in the document. Use empty strings for missing fields."""

_HUMAN = "CV Text:\n{documents}\n\nExtract contact information as JSON."

_FALLBACK: dict[str, Any] = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin_url": "",
}


class _State(TypedDict):
    documents: str
    parsed_result: dict[str, Any]
    error: str | None


def build_profile_agent(
    llm: BaseChatModel,
    trace_metadata: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)
    invoke_cfg = traced_config(
        "profile_extraction",
        trace_metadata,
        session_id=session_id,
        user_id=user_id,
    )

    async def extract(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {"documents": truncate(state["documents"], 8000)},
                config=invoke_cfg,
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Profile agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "extraction_failed"}

    g = StateGraph(_State)
    g.add_node("extract", extract)
    g.set_entry_point("extract")
    g.add_edge("extract", END)
    return g.compile()


async def run_profile_agent(
    llm: BaseChatModel,
    cv_text: str,
    *,
    trace_metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    graph = build_profile_agent(
        llm, trace_metadata, session_id=session_id, user_id=user_id
    )
    result = await graph.ainvoke(
        {"documents": cv_text, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
