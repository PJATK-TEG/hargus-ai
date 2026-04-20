from hargus_api.repositories.mock_data import CANDIDATES, MESSAGES, VACANCIES
from hargus_api.schemas.domain import Candidate, Message, Vacancy

_VACANCIES_BY_ID: dict[str, Vacancy] = {vacancy.id: vacancy for vacancy in VACANCIES}
_CANDIDATES_BY_ID: dict[str, Candidate] = {candidate.id: candidate for candidate in CANDIDATES}
_CANDIDATES_BY_VACANCY_ID: dict[str, list[Candidate]] = {}
for candidate in CANDIDATES:
    _CANDIDATES_BY_VACANCY_ID.setdefault(candidate.vacancy_id, []).append(candidate)


def list_vacancies() -> list[Vacancy]:
    return VACANCIES


def get_vacancy(vacancy_id: str) -> Vacancy | None:
    return _VACANCIES_BY_ID.get(vacancy_id)


def list_candidates(vacancy_id: str | None = None) -> list[Candidate]:
    if vacancy_id is None:
        return CANDIDATES
    return _CANDIDATES_BY_VACANCY_ID.get(vacancy_id, [])


def list_candidates_paginated(
    vacancy_id: str | None = None,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    candidates = list_candidates(vacancy_id=vacancy_id)
    return candidates[offset : offset + limit], len(candidates)


def get_candidate(candidate_id: str) -> Candidate | None:
    return _CANDIDATES_BY_ID.get(candidate_id)


def get_candidate_messages(candidate_id: str) -> list[Message]:
    return MESSAGES.get(candidate_id, [])
