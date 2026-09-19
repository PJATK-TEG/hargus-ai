from fastapi.testclient import TestClient

from hargus_api.main import app


def test_healthcheck_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "Hargus AI API"


def test_request_id_header_is_returned() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"
