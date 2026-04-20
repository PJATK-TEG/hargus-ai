from fastapi.testclient import TestClient

from hargus_api.main import app


def test_submit_ai_task_returns_stub_record() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/ai/tasks",
        json={
            "type": "candidate_summary",
            "candidateId": "c1",
            "prompt": "Summarize Elena for the backend role.",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["type"] == "candidate_summary"
    assert payload["status"] == "queued"
    assert payload["provider"] == "temporal_stub"


def test_list_candidates_can_filter_by_vacancy() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/candidates", params={"vacancyId": "v1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] >= 1
    assert payload["meta"]["limit"] == 50
    assert payload["meta"]["offset"] == 0
    assert payload["meta"]["returned"] == len(payload["items"])
    assert all(item["vacancyId"] == "v1" for item in payload["items"])


def test_list_candidates_supports_pagination() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/candidates", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["limit"] == 1
    assert payload["meta"]["offset"] == 1
    assert payload["meta"]["returned"] <= 1


def test_submit_ai_task_requires_candidate_reference() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/ai/tasks",
        json={
            "type": "candidate_summary",
            "prompt": "No candidate provided",
        },
    )

    assert response.status_code == 422


def test_submit_background_check_queues_stub_task() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/background/checks",
        json={
            "candidateId": "c1",
            "sources": ["courtlistener", "openalex"],
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["type"] == "candidate_background_check"
    assert payload["status"] == "queued"


def test_background_source_search_queues_stub_task() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/background/sources/openalex/search",
        json={
            "candidateId": "c3",
            "query": "authorship verification",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["type"] == "candidate_background_check"


def test_get_vacancy_candidates_returns_404_for_missing_vacancy() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/vacancies/unknown/candidates")

    assert response.status_code == 404
    assert response.json()["detail"] == "Vacancy not found"
