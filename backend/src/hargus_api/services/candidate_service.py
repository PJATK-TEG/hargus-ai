from __future__ import annotations

import logging
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select as sa_select

from hargus_api.db.models import CandidateFile
from hargus_api.db.repositories.candidate_repo import CandidateRepository
from hargus_api.schemas.domain import Candidate
from hargus_api.schemas.domain import CandidateFile as CandidateFileSchema
from hargus_api.storage.factory import get_storage

logger = logging.getLogger(__name__)


async def delete_candidate(session: AsyncSession, candidate_id: str) -> bool:
    return await CandidateRepository(session).delete(candidate_id)


async def list_candidates(session: AsyncSession, vacancy_id: str | None = None) -> list[Candidate]:
    rows = await CandidateRepository(session).list_all(vacancy_id)
    return [Candidate.model_validate(c, from_attributes=True) for c in rows]


async def list_candidates_paginated(
    session: AsyncSession,
    vacancy_id: str | None = None,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    rows, total = await CandidateRepository(session).list_paginated(
        vacancy_id, limit=limit, offset=offset
    )
    return [Candidate.model_validate(c, from_attributes=True) for c in rows], total


async def get_candidate(session: AsyncSession, candidate_id: str) -> Candidate | None:
    row = await CandidateRepository(session).get_by_id(candidate_id)
    return Candidate.model_validate(row, from_attributes=True) if row else None


def _extract_text(data: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        return "\n\n".join(p.extract_text() or "" for p in reader.pages)
    return data.decode("utf-8", errors="replace")


def _format_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


async def upload_candidate_file(
    session: AsyncSession,
    candidate_id: str,
    file_bytes: bytes,
    filename: str,
    file_type: str = "cv",
) -> CandidateFileSchema | None:
    row = await CandidateRepository(session).get_by_id(candidate_id)
    if row is None:
        return None
    text = _extract_text(file_bytes, filename)
    now = datetime.now(UTC).isoformat()
    file_row = CandidateFile(
        id=str(uuid4()),
        candidate_id=candidate_id,
        type=file_type,
        name=filename,
        content=text,
        uploaded_at=now,
        size=_format_size(len(file_bytes)),
    )
    session.add(file_row)
    try:
        await get_storage().upload(
            f"candidates/{candidate_id}/{filename}", file_bytes, content_type="application/octet-stream"
        )
    except Exception:
        logger.warning("Storage upload failed for candidate %s file %s", candidate_id, filename)
    await session.flush()
    return CandidateFileSchema.model_validate(file_row, from_attributes=True)


async def delete_candidate_file(
    session: AsyncSession,
    candidate_id: str,
    file_id: str,
) -> bool:
    stmt = sa_select(CandidateFile).where(
        CandidateFile.id == file_id,
        CandidateFile.candidate_id == candidate_id,
    )
    result = await session.execute(stmt)
    file_row = result.scalars().first()
    if file_row is None:
        return False
    await session.delete(file_row)
    await session.flush()
    return True


async def create_candidate(
    session: AsyncSession,
    vacancy_id: str,
    cv: tuple[bytes, str],
    transcripts: list[tuple[bytes, str]],
) -> Candidate:
    candidate_id = str(uuid4())
    now = datetime.now(UTC).isoformat()

    data = {
        "id": candidate_id,
        "name": "[run Analyze] New Candidate",
        "email": "",
        "phone": "",
        "location": "",
        "avatar_initials": "NC",
        "avatar_color": "#6366F1",
        "vacancy_id": vacancy_id,
        "score": 0,
        "relevancy_score": 0,
        "tags": [],
        "status": "new",
        "parsed_fields": {
            "summary": "",
            "skills": [],
            "skillScores": [],
            "experience": [],
            "education": [],
            "languages": [],
            "certifications": [],
            "totalYearsExp": 0,
        },
        "applied_at": now,
    }

    repo = CandidateRepository(session)
    candidate_row = await repo.create(data)

    all_files: list[tuple[bytes, str, str]] = [
        (cv[0], cv[1], "cv"),
        *((b, fn, "transcript") for b, fn in transcripts),
    ]
    storage = get_storage()
    for file_bytes, filename, source_type in all_files:
        text = _extract_text(file_bytes, filename)
        file_row = CandidateFile(
            id=str(uuid4()),
            candidate_id=candidate_id,
            type=source_type,
            name=filename,
            content=text,
            uploaded_at=now,
            size=_format_size(len(file_bytes)),
        )
        session.add(file_row)
        try:
            key = f"candidates/{candidate_id}/{filename}"
            await storage.upload(key, file_bytes, content_type="application/octet-stream")
        except Exception:
            logger.warning("Storage upload failed for candidate %s file %s", candidate_id, filename)

    await session.commit()
    await session.refresh(candidate_row, ["files"])
    return Candidate.model_validate(candidate_row, from_attributes=True)
