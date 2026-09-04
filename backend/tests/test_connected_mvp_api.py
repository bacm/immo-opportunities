from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jwt import ExpiredSignatureError

from immo.config import get_settings
from immo.connected_mvp import Actor, PermissionDeniedError, calculate_scenario, require_role
from immo.main import create_app


def test_session_requires_oidc_bearer_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("IMMO_OIDC_ENABLED", "true")
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.get_session",
        lambda principal: {
            "user_id": "user:00000000-0000-0000-0000-000000000001",
            "display_name": principal.display_name,
            "email": principal.email,
            "organization_id": "org:test",
            "organization_name": "Test",
            "role": "analyst",
        },
    )
    monkeypatch.setattr(
        "immo.auth._decode_access_token",
        lambda token: {"sub": "oidc-user", "name": "Ada", "email": "ada@example.test"},
    )
    get_settings.cache_clear()
    client = TestClient(create_app())

    assert client.get("/api/v1/session").status_code == 401
    response = client.get("/api/v1/session", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 200
    assert response.json()["organization_id"] == "org:test"
    get_settings.cache_clear()


def test_expired_oidc_session_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("IMMO_OIDC_ENABLED", "true")

    def expired(token: str):
        raise ExpiredSignatureError(token)

    monkeypatch.setattr("immo.auth._decode_access_token", expired)
    get_settings.cache_clear()
    response = TestClient(create_app()).get(
        "/api/v1/session", headers={"Authorization": "Bearer expired"}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    get_settings.cache_clear()


def test_roles_refuse_viewer_writes_and_scenario_does_not_mutate_inputs() -> None:
    actor = Actor("user:test", "org:test", "Test", "viewer", "Ada", None)
    with pytest.raises(PermissionDeniedError):
        require_role(actor, "analyst")

    assumptions = {
        "purchase_price_eur": Decimal(200_000),
        "works_cost_eur": Decimal(50_000),
        "resale_price_eur": Decimal(340_000),
        "fees_eur": Decimal(20_000),
        "finance_cost_eur": Decimal(0),
        "holding_cost_eur": Decimal(0),
    }
    original = assumptions.copy()
    result = calculate_scenario(assumptions)
    assert assumptions == original
    assert result["net_margin_eur"] == 70_000


def test_status_rejection_is_validated_and_persisted(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.change_status",
        lambda principal, opportunity_id, **payload: {
            **payload,
            "favorite": payload["favorite"] or False,
            "updated_at": "2026-08-07T12:00:00+00:00",
        },
    )
    client = TestClient(create_app())
    url = "/api/v1/opportunities/opportunity:test:1/status"

    invalid = client.patch(url, json={"status": "rejected"})
    valid = client.patch(
        url,
        json={
            "status": "rejected",
            "rejection_reasons": ["other"],
            "rejection_comment": "Analyse terrain défavorable",
        },
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["rejection_reasons"] == ["other"]


def test_notes_reviews_scenarios_and_saved_searches(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.add_note",
        lambda principal, opportunity_id, body: {
            "id": "note:00000000-0000-0000-0000-000000000001",
            "body": body,
            "author": "Ada",
            "created_at": "2026-08-07T12:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.add_review",
        lambda principal, opportunity_id, **payload: {
            "id": "review:00000000-0000-0000-0000-000000000001",
            **payload,
            "author": "Ada",
            "reviewed_at": "2026-08-07T12:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.add_scenario",
        lambda principal, opportunity_id, payload: {
            "id": "scenario:user:00000000-0000-0000-0000-000000000001",
            "assumptions": {key: float(value) for key, value in payload.items()},
            "results": {"net_margin_eur": 50000.0},
            "created_at": "2026-08-07T12:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.add_saved_search",
        lambda principal, **payload: {
            "id": "search:00000000-0000-0000-0000-000000000001",
            **payload,
            "created_at": "2026-08-07T12:00:00+00:00",
        },
    )
    client = TestClient(create_app())
    base = "/api/v1/opportunities/opportunity:test:1"

    assert client.post(base + "/notes", json={"body": "À visiter"}).status_code == 201
    assert (
        client.post(
            base + "/reviews",
            json={"decision": "worth_deeper_analysis", "confidence": 4},
        ).status_code
        == 201
    )
    scenario = client.post(
        base + "/scenarios",
        json={
            "purchase_price_eur": 200000,
            "works_cost_eur": 50000,
            "resale_price_eur": 340000,
        },
    )
    assert scenario.status_code == 201
    assert scenario.json()["results"]["net_margin_eur"] == 50000
    assert (
        client.post(
            "/api/v1/saved-searches",
            json={"name": "Rennes retenus", "filters": {"strategy": "division_extension"}},
        ).status_code
        == 201
    )


def test_review_outcome_preserves_successive_business_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.connected_mvp.add_review_outcome",
        lambda principal, review_id, **payload: {
            "id": "outcome:00000000-0000-0000-0000-000000000001",
            "candidate_review_id": review_id,
            **payload,
            "created_at": "2026-08-10T12:00:00+00:00",
        },
    )
    response = TestClient(create_app()).post(
        "/api/v1/reviews/review:00000000-0000-0000-0000-000000000001/outcomes",
        json={
            "stage": "visit",
            "result": "positive",
            "details": {"comment": "Cas réel"},
            "observed_at": "2026-08-10T11:00:00+00:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["stage"] == "visit"


def test_admin_requires_repository_role_check_and_carries_request_id(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_list(principal, request_id: str, limit: int):
        captured["request_id"] = request_id
        return []

    monkeypatch.setattr("immo.api.routes.connected_mvp.list_import_runs", fake_list)
    response = TestClient(create_app()).get(
        "/api/v1/admin/import-runs", headers={"X-Request-ID": "e2e-admin-1"}
    )
    assert response.status_code == 200
    assert captured["request_id"] == "e2e-admin-1"
