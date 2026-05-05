"""Ingestion activities: load candidate documents and parse them to plain text."""
from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader
from temporalio import activity

from hargus_api.db.base import AsyncSessionLocal
from hargus_api.services.candidate_service import get_candidate
from hargus_api.storage.factory import get_storage
from hargus_api.temporal.models import (
    LoadDocumentsInput,
    LoadDocumentsOutput,
    ParseDocumentsInput,
    ParseDocumentsOutput,
    ParsedDocument,
    RawDocument,
)

logger = logging.getLogger(__name__)


async def _candidate_structured_text(candidate_id: str) -> str | None:
    """Serialise a candidate's parsed fields as a plain-text document.

    Used when no storage files exist (e.g. mock/DB-only candidates).
    Returns None when the candidate is not found.
    """
    async with AsyncSessionLocal() as session:
        candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        return None

    pf = candidate.parsed_fields
    lines = [
        f"CANDIDATE: {candidate.name}",
        f"Email: {candidate.email}   Phone: {candidate.phone}   Location: {candidate.location}",
        "",
        "SUMMARY",
        pf.summary,
        "",
        f"SKILLS: {', '.join(pf.skills)}",
        "",
        f"EXPERIENCE  ({pf.total_years_exp} years total)",
    ]
    for exp in pf.experience:
        lines += [
            f"  {exp.from_} – {exp.to}  |  {exp.role} at {exp.company}",
            f"  {exp.description}",
        ]
    lines += ["", "EDUCATION"]
    for edu in pf.education:
        lines.append(
            f"  {edu.degree} in {edu.field}, {edu.institution} ({edu.year})"
        )
    if pf.certifications:
        lines += ["", f"CERTIFICATIONS: {', '.join(pf.certifications)}"]
    if pf.languages:
        lines += [f"LANGUAGES: {', '.join(pf.languages)}"]

    # Include file content snippets if they have real text (not placeholder)
    for f in candidate.files:
        if f.content and f.content not in ("Full CV content...",):
            lines += ["", f"--- {f.type.upper()}: {f.name} ---", f.content]

    return "\n".join(lines)


@activity.defn
async def load_documents_activity(inp: LoadDocumentsInput) -> LoadDocumentsOutput:
    """Load raw document metadata for a candidate from object storage.

    Falls back to serialised structured data when no storage files exist.
    """
    activity.heartbeat()
    storage = get_storage()
    docs: list[RawDocument] = []

    # Attempt to load real files stored under the candidate's prefix
    cv_prefix = f"candidates/{inp.candidate_id}/"
    try:
        keys = await storage.list(cv_prefix)
        for key in keys:
            if key.endswith("/"):
                continue
            source_type = "cv"
            if "/transcript/" in key or key.split("/")[-1].startswith("transcript"):
                source_type = "transcript"
            elif "/notes/" in key or key.split("/")[-1].startswith("note"):
                source_type = "notes"
            elif "/background/" in key:
                source_type = "background"
            data = await storage.download(key)
            docs.append(
                RawDocument(
                    source_type=source_type,  # type: ignore[arg-type]
                    storage_key=key,
                    filename=key.split("/")[-1],
                    size_bytes=len(data),
                )
            )
    except Exception:
        logger.debug("Storage listing failed for candidate %s — using structured data", inp.candidate_id)

    # When no storage files found, synthesise a text document from structured data
    if not docs:
        text = await _candidate_structured_text(inp.candidate_id)
        if text:
            synthetic_key = f"_synthetic/{inp.candidate_id}/profile.txt"
            docs.append(
                RawDocument(
                    source_type="cv",
                    storage_key=synthetic_key,
                    filename="profile.txt",
                    size_bytes=len(text.encode()),
                )
            )
            # Stash text so parse_activity can find it without a real storage call
            _SYNTHETIC_TEXTS[synthetic_key] = text
            logger.info(
                "load_documents: candidate=%s using synthetic profile (%d chars)",
                inp.candidate_id,
                len(text),
            )

    logger.info(
        "load_documents: candidate=%s loaded=%d docs", inp.candidate_id, len(docs)
    )
    return LoadDocumentsOutput(documents=docs)


# In-process cache for synthetic text documents so parse_activity can access them
# without a real storage round-trip.
_SYNTHETIC_TEXTS: dict[str, str] = {}


def _extract_text(data: bytes, filename: str) -> tuple[str, int]:
    """Return (raw_text, page_count) from raw file bytes."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n\n".join(pages), len(pages)
    return data.decode("utf-8", errors="replace"), 1


@activity.defn
async def parse_documents_activity(inp: ParseDocumentsInput) -> ParseDocumentsOutput:
    """Download each raw document and extract plain text."""
    activity.heartbeat()
    storage = get_storage()
    parsed: list[ParsedDocument] = []

    for raw in inp.documents:
        try:
            # Check the in-process synthetic cache first
            if raw.storage_key in _SYNTHETIC_TEXTS:
                text = _SYNTHETIC_TEXTS[raw.storage_key]
                page_count = 1
            else:
                data = await storage.download(raw.storage_key)
                text, page_count = _extract_text(data, raw.filename)

            parsed.append(
                ParsedDocument(
                    source_type=raw.source_type,
                    storage_key=raw.storage_key,
                    raw_text=text,
                    page_count=page_count,
                    metadata={"filename": raw.filename, "size_bytes": raw.size_bytes},
                )
            )
        except Exception:
            logger.exception("Failed to parse document %s", raw.storage_key)

    logger.info(
        "parse_documents: run=%s parsed=%d/%d",
        inp.workflow_run_id,
        len(parsed),
        len(inp.documents),
    )
    return ParseDocumentsOutput(documents=parsed)
