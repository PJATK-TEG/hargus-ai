"""Embedding activity: chunk documents and store vectors in pgvector."""
from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from temporalio import activity

from hargus_api.ai.llm.factory import get_embeddings
from hargus_api.config import get_settings
from hargus_api.temporal.models import ChunkEmbedInput, ChunkEmbedOutput

logger = logging.getLogger(__name__)

_TRANSCRIPT_SEP = "\n" + "-" * 60 + "\n"


async def _clear_collection_embeddings(collection_name: str) -> None:
    """Delete all embeddings for the named collection so re-embedding is idempotent."""
    engine = pgvector_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM langchain_pg_embedding "
                "WHERE collection_id = ("
                "  SELECT uuid FROM langchain_pg_collection WHERE name = :name"
                ")"
            ),
            {"name": collection_name},
        )


@lru_cache(maxsize=1)
def pgvector_engine() -> AsyncEngine:
    """Return a psycopg3 async engine for PGVector.

    langchain_postgres sends multi-statement SQL (advisory lock + CREATE EXTENSION)
    in a single call, which asyncpg rejects. psycopg3 handles it correctly.
    """
    url = get_settings().database_url
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg_async://")
    url = url.replace("postgresql://", "postgresql+psycopg_async://")
    return create_async_engine(url)


@activity.defn
async def chunk_and_embed_activity(inp: ChunkEmbedInput) -> ChunkEmbedOutput:
    """Split documents into chunks, embed them, and upsert into pgvector."""
    activity.heartbeat()

    splitter = RecursiveCharacterTextSplitter(
        separators=[_TRANSCRIPT_SEP],
        chunk_size=inp.chunk_size,
        chunk_overlap=inp.chunk_overlap,
    )

    lc_docs: list[Document] = []
    for doc in inp.documents:
        chunks = splitter.split_text(doc.raw_text)
        for i, chunk in enumerate(chunks):
            lc_docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "candidate_id": inp.candidate_id,
                        "workflow_run_id": inp.workflow_run_id,
                        "source_type": doc.source_type,
                        "chunk_index": i,
                    },
                )
            )
        activity.heartbeat()

    collection_name = f"candidate_{inp.candidate_id}"

    if lc_docs:
        await _clear_collection_embeddings(collection_name)
        store = PGVector(
            embeddings=get_embeddings(),
            collection_name=collection_name,
            connection=pgvector_engine(),
            use_jsonb=True,
        )
        await store.aadd_documents(lc_docs)
        activity.heartbeat()
        logger.info(
            "chunk_and_embed: run=%s collection=%s chunks=%d",
            inp.workflow_run_id,
            collection_name,
            len(lc_docs),
        )

    return ChunkEmbedOutput(
        collection_name=collection_name,
        chunk_count=len(lc_docs),
    )
