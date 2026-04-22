"""Report Drafting Agent — synthesises all analysis into a structured report."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are a senior HR analyst writing a candidate evaluation report.
Based on the provided analysis data, write a professional, evidence-based report.

Guiding mission for this analysis:
{coordinator_prompt}

Return ONLY valid JSON matching this exact structure:
{{
  "executive_summary": "2-3 paragraph executive summary",
  "sections": [
    {{
      "title": "Technical Skills Assessment",
      "content": "Detailed assessment paragraph",
      "evidence": ["Specific evidence point 1", "Specific evidence point 2"]
    }},
    {{"title": "Experience & Background", "content": "...", "evidence": ["..."]}},
    {{"title": "Interview Performance", "content": "...", "evidence": ["..."]}},
    {{"title": "Risk Assessment", "content": "...", "evidence": ["..."]}}
  ],
  "recommendation": "strong_match|possible|weak|manual_review",
  "recommendation_rationale": "Clear 2-3 sentence explanation of the recommendation"
}}

Write professionally, objectively, and cite specific evidence. Avoid bias."""

_HUMAN = """Analysis Data:

Job Requirements: {job_rubric}
Candidate Facts: {candidate_facts}
Interview Findings: {interview_findings}
Risk Flags: {risk_flags}
Score: {overall_score}/100 ({recommendation})
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}

Write the candidate evaluation report as JSON."""

_FALLBACK: dict[str, Any] = {
    "executive_summary": "Report generation failed. Manual review required.",
    "sections": [],
    "recommendation": "manual_review",
    "recommendation_rationale": "Automated report generation encountered an error.",
}


class _State(TypedDict):
    input_data: dict[str, Any]
    parsed_result: dict[str, Any]
    error: str | None


def build_report_agent(llm: BaseChatModel):
    async def draft(state: _State) -> _State:
        try:
            data = state["input_data"]
            coordinator_prompt = data.get("coordinator_prompt", "")
            system = _SYSTEM.format(coordinator_prompt=coordinator_prompt)
            chain = build_json_chain(llm, system, _HUMAN)
            # Pass all fields except coordinator_prompt to the human template
            human_data = {k: v for k, v in data.items() if k != "coordinator_prompt"}
            result = await chain.ainvoke(
                human_data,
                config=traced_config("report_drafting"),
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Report agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "drafting_failed"}

    g = StateGraph(_State)
    g.add_node("draft", draft)
    g.set_entry_point("draft")
    g.add_edge("draft", END)
    return g.compile()


async def run_report_agent(
    llm: BaseChatModel, input_data: dict[str, Any]
) -> dict[str, Any]:
    graph = build_report_agent(llm)
    result = await graph.ainvoke(
        {"input_data": input_data, "parsed_result": {}, "error": None}
    )
    return result["parsed_result"]
