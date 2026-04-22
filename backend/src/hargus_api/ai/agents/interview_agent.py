"""Interview Insight Agent — extracts behavioral signals from interview transcripts."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are an expert interview evaluator. Analyse the interview transcript and extract behavioural insights.

Return ONLY valid JSON matching this exact structure:
{
  "communication_quality": "strong|adequate|weak|unknown",
  "strengths": ["Demonstrated clear problem-solving approach"],
  "concerns": ["Vague answers about leadership experience"],
  "behavioral_examples": [
    {"competency": "Leadership", "example": "Led a team of 5 to deliver product in 3 months", "is_strength": true}
  ],
  "overall_impression": "2-3 sentence summary of interview performance"
}

Focus on observable behaviours and specific examples. Avoid personality judgements."""

_HUMAN = "Interview Transcript:\n{transcript}\n\nExtract interview insights as JSON."

_NO_TRANSCRIPT: dict[str, Any] = {
    "communication_quality": "unknown",
    "strengths": [],
    "concerns": [],
    "behavioral_examples": [],
    "overall_impression": "No interview transcript available.",
}

_FALLBACK: dict[str, Any] = {
    "communication_quality": "unknown",
    "strengths": [],
    "concerns": [],
    "behavioral_examples": [],
    "overall_impression": "Analysis unavailable due to error.",
}


class _State(TypedDict):
    transcript: str
    parsed_result: dict[str, Any]
    error: str | None


def build_interview_agent(llm: BaseChatModel):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)

    async def extract(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {"transcript": truncate(state["transcript"], 8000)},
                config=traced_config("interview_insight"),
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Interview agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "extraction_failed"}

    g = StateGraph(_State)
    g.add_node("extract", extract)
    g.set_entry_point("extract")
    g.add_edge("extract", END)
    return g.compile()


async def run_interview_agent(llm: BaseChatModel, transcript_text: str) -> dict[str, Any]:
    if not transcript_text.strip():
        return _NO_TRANSCRIPT.copy()
    graph = build_interview_agent(llm)
    result = await graph.ainvoke(
        {"transcript": transcript_text, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
