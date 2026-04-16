from hargus_api.repositories.mock_data import CANDIDATES, MESSAGES, VACANCIES
from hargus_api.schemas.domain import Candidate, Message, Vacancy


def list_vacancies() -> list[Vacancy]:
    return VACANCIES


def get_vacancy(vacancy_id: str) -> Vacancy | None:
    return next((vacancy for vacancy in VACANCIES if vacancy.id == vacancy_id), None)


def list_candidates(vacancy_id: str | None = None) -> list[Candidate]:
    if vacancy_id is None:
        return CANDIDATES
    return [candidate for candidate in CANDIDATES if candidate.vacancy_id == vacancy_id]


def get_candidate(candidate_id: str) -> Candidate | None:
    return next((candidate for candidate in CANDIDATES if candidate.id == candidate_id), None)


def get_candidate_messages(candidate_id: str) -> list[Message]:
    return MESSAGES.get(candidate_id, [])
