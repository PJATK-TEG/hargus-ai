from fastapi.testclient import TestClient

from hargus_api.main import app


def test_healthcheck_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "Hargus AI API"
