from unittest.mock import patch

from fastapi.testclient import TestClient


def test_liveness_returns_request_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request-1"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "invalid request id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid request id"


def test_readiness_checks_database(client: TestClient) -> None:
    metadata = {
        "status": "connected",
        "postgres_version": "15.0",
        "postgis_version": "3.5",
    }
    with patch("immo.api.routes.health.check_database", return_value=metadata):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_structured_error(client: TestClient) -> None:
    with patch("immo.api.routes.health.check_database", side_effect=OSError("offline")):
        response = client.get("/health/ready", headers={"X-Request-ID": "readiness-test"})

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "http_error",
        "message": "Database is not ready",
        "request_id": "readiness-test",
        "details": "Database is not ready",
    }
