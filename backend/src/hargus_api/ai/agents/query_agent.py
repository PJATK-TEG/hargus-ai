"""Query Agent — answers free-form HR questions about a candidate using RAG context."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from hargus_api.ai.agents.base import build_json_chain, truncate
from hargus_api.ai.tracing import traced_config

logger = logging.getLogger(__name__)

_SYSTEM = """You are an expert HR analyst answering specific questions about a job candidate.
You have access to excerpts from the candidate's documents (CV, interview transcripts, notes)
and the job description. Answer the question accurately and concisely based only on the
provided context. If the context does not contain enough information to answer confidently,
say so clearly. If the question is not relevant to the candidate's suitability for the job, say that as well.
If the user asks a question like "What can you do?", respond with a brief description of how you can analyze candidate information to answer HR-related questions.

Return ONLY valid JSON matching this exact structure:
{
  "answer": "Your detailed answer to the question",
  "sources": ["Brief quote or reference from context that supports the answer"],
  "confidence": "high|medium|low"
}

Set confidence based on how well the context supports your answer:
- high: context directly addresses the question
- medium: context partially addresses the question or requires inference
- low: context is insufficient or the question cannot be answered from available information"""

_HUMAN = (
    "Question: {query}\n\n"
    "Candidate Context:\n{context}\n\n"
    "Job Description:\n{job_description}\n\n"
    "Answer the question based on the provided context."
)

_FALLBACK: dict[str, Any] = {
    "answer": "Could not generate an answer from the available candidate information.",
    "sources": [],
    "confidence": "low",
}


class _State(TypedDict):
    query: str
    context: str
    job_description: str
    parsed_result: dict[str, Any]
    error: str | None


def build_query_agent(
    llm: BaseChatModel,
    trace_metadata: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
):
    chain = build_json_chain(llm, _SYSTEM, _HUMAN)
    invoke_cfg = traced_config(
        "candidate_query",
        trace_metadata,
        session_id=session_id,
        user_id=user_id,
    )

    async def answer(state: _State) -> _State:
        try:
            result = await chain.ainvoke(
                {
                    "query": truncate(state["query"], 2000),
                    "context": truncate(state["context"], 8000),
                    "job_description": truncate(state["job_description"], 4000),
                },
                config=invoke_cfg,
            )
            return {"parsed_result": result, "error": None}
        except Exception:
            logger.exception("Query agent failed")
            return {"parsed_result": _FALLBACK.copy(), "error": "query_failed"}

    g = StateGraph(_State)
    g.add_node("answer", answer)
    g.set_entry_point("answer")
    g.add_edge("answer", END)
    return g.compile()


async def run_query_agent(
    llm: BaseChatModel,
    query: str,
    context: str,
    job_description: str,
    *,
    trace_metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    graph = build_query_agent(
        llm, trace_metadata, session_id=session_id, user_id=user_id
    )
    result = await graph.ainvoke(
        {
            "query": query,
            "context": context,
            "job_description": job_description,
            "parsed_result": {},
            "error": None,
        }
    )
    return result["parsed_result"]
