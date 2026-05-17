"""Query activities: answer a free-form question about a candidate using RAG + LLM."""
from __future__ import annotations

import logging

from langchain_postgres import PGVector
from temporalio import activity

from hargus_api.ai.agents.query_agent import run_query_agent
from hargus_api.ai.config import get_rag_k
from hargus_api.ai.llm.factory import get_embeddings, get_llm
from hargus_api.config import get_settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.services.message_service import save_message
from hargus_api.services.vacancy_service import get_vacancy
from hargus_api.temporal.activities.embedding import pgvector_engine
from hargus_api.temporal.activities.reporting import _update_ai_task_status
from hargus_api.temporal.activity_utils import heartbeat_while
from hargus_api.temporal.models import (
    CandidateQueryActivityInput,
    CandidateQueryResult,
    StoreQueryResultInput,
)

logger = logging.getLogger(__name__)


async def _retrieve_chunks(collection_name: str, query: str) -> str:
    if not collection_name:
        return ""
    try:
        store = PGVector(
            embeddings=get_embeddings(),
            collection_name=collection_name,
            connection=pgvector_engine(),
            use_jsonb=True,
        )
        docs = await store.asimilarity_search(query, k=get_rag_k())
        if not docs:
            return ""
        chunks = "\n---\n".join(d.page_content for d in docs)
        return f"[Relevant excerpts from candidate documents]\n{chunks}"
    except Exception:
        logger.debug("RAG retrieval failed for collection %s", collection_name)
        return ""


async def _fetch_vacancy_description(vacancy_id: str) -> str:
    if not vacancy_id:
        return ""
    async with AsyncSessionLocal() as session:
        vacancy = await get_vacancy(session, vacancy_id)
    if vacancy is None:
        return f"Vacancy ID: {vacancy_id} (description unavailable)"
    requirements = ", ".join(vacancy.requirements)
    return (
        f"Title: {vacancy.title}\n"
        f"Department: {vacancy.department}\n"
        f"Location: {vacancy.location}\n"
        f"Type: {vacancy.type}\n"
        f"Description: {vacancy.description}\n"
        f"Requirements: {requirements}"
    )


@activity.defn
async def run_candidate_query_activity(
    inp: CandidateQueryActivityInput,
) -> CandidateQueryResult:
    activity.heartbeat()

    collection_name = inp.collection_name or f"candidate_{inp.candidate_id}_analysis"

    context, job_description = await _retrieve_chunks(
        collection_name, inp.query
    ), await _fetch_vacancy_description(inp.vacancy_id)

    settings = get_settings()
    trace_meta = {
        "workflow_run_id": inp.workflow_run_id,
        "candidate_id": inp.candidate_id,
        "vacancy_set": str(bool((inp.vacancy_id or "").strip())),
        "collection_name": collection_name,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }

    raw = await heartbeat_while(
        run_query_agent(
            get_llm(),
            inp.query,
            context,
            job_description,
            trace_metadata=trace_meta,
            session_id=inp.workflow_run_id,
            user_id=inp.candidate_id,
        )
    )

    answer = raw.get("answer") or "No answer generated."
    sources = raw.get("sources") or []
    confidence = raw.get("confidence") or "low"

    if not isinstance(sources, list):
        sources = []

    logger.info(
        "run_candidate_query: candidate=%s confidence=%s",
        inp.candidate_id,
        confidence,
    )
    return CandidateQueryResult(
        workflow_run_id=inp.workflow_run_id,
        candidate_id=inp.candidate_id,
        answer=answer,
        sources=sources,
        confidence=confidence,
    )


@activity.defn
async def store_query_result_activity(inp: StoreQueryResultInput) -> None:
    async with AsyncSessionLocal() as session:
        repo = WorkflowRunRepository(session)
        run = await repo.get_by_workflow_id(inp.workflow_run_id)
        if run is None:
            logger.warning(
                "store_query_result: workflow run not found: %s", inp.workflow_run_id
            )
        else:
            await repo.set_completed(run.id)
            await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            await save_message(session, inp.result.candidate_id, "assistant", inp.result.answer)
            await session.commit()
    except Exception:
        logger.warning("Could not save assistant message for workflow run %s", inp.workflow_run_id)

    await _update_ai_task_status(
        inp.workflow_run_id,
        "completed",
        {
            "answer": inp.result.answer,
            "confidence": inp.result.confidence,
            "sources": ", ".join(inp.result.sources),
        },
    )
    logger.info("store_query_result: completed workflow run %s", inp.workflow_run_id)
