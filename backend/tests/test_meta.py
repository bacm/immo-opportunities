from unittest.mock import patch

from fastapi.testclient import TestClient


def test_version_exposes_build_and_database_metadata(client: TestClient) -> None:
    metadata = {
        "status": "connected",
        "postgres_version": "15.10",
        "postgis_version": "3.5.2",
    }
    with patch("immo.api.routes.meta.check_database", return_value=metadata):
        response = client.get("/api/v1/meta/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "immo-api",
        "version": "0.1.0",
        "git_sha": "development",
        "environment": "development",
        "database": metadata,
    }


def test_unknown_route_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/v1/missing", headers={"X-Request-ID": "missing-route"})

    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == "missing-route"
