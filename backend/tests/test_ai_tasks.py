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
    assert all(item["vacancyId"] == "v1" for item in payload["items"])
