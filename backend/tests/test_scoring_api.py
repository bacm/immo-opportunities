from fastapi.testclient import TestClient

from immo.main import app


def summary(opportunity_id: str = "opportunity:test:1") -> dict[str, object]:
    return {
        "id": opportunity_id,
        "property_unit_id": "property-unit:test",
        "strategy": "division_extension",
        "score": 72.5,
        "score_class": "interesting",
        "confidence_score": 81,
        "confidence_level": "high",
        "segment_code": "urban-rennes",
        "snapshot_at": "2026-01-01",
        "calculated_at": "2026-01-02T10:00:00+00:00",
        "baseline_selected": True,
    }


def detail() -> dict[str, object]:
    return {
        **summary(),
        "definition_id": "division-extension-v0.1",
        "definition_version": 1,
        "eligible": True,
        "eligibility_results": [{"code": "VALID_GEOMETRY", "passed": True}],
        "missing_features": ["RISK-004"],
        "publication_blockers": [],
        "release_ids": ["DS-01:release"],
        "financial_scenario": {"central": {"net_margin_eur": 50_000}},
        "components": [{"code": "land_capacity", "score": 75}],
    }


def test_opportunity_list_and_detail_endpoints(monkeypatch) -> None:
    monkeypatch.setattr("immo.api.routes.scoring.list_opportunities", lambda **kwargs: [summary()])
    monkeypatch.setattr("immo.api.routes.scoring.find_opportunity", lambda opportunity_id: detail())
    client = TestClient(app)

    listed = client.get("/api/v1/opportunities", params={"minimum_score": 60})
    opened = client.get("/api/v1/opportunities/opportunity:test:1")

    assert listed.status_code == 200
    assert listed.json()[0]["confidence_level"] == "high"
    assert opened.status_code == 200
    assert opened.json()["components"][0]["code"] == "land_capacity"


def test_history_evidence_comparables_and_sources_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.scoring.list_opportunity_history",
        lambda opportunity_id: [summary(), summary("opportunity:test:old")],
    )
    monkeypatch.setattr(
        "immo.api.routes.scoring.list_opportunity_evidence",
        lambda opportunity_id: [
            {
                "feature_code": "LAND-004",
                "direction": "positive",
                "impact": 8.5,
                "explanation": "Gabarit contrôlé.",
            }
        ],
    )
    monkeypatch.setattr(
        "immo.api.routes.scoring.list_opportunity_comparables",
        lambda opportunity_id: [{"transaction_id": "dvf:1", "included": True}],
    )
    monkeypatch.setattr(
        "immo.api.routes.scoring.list_opportunity_sources",
        lambda opportunity_id: [{"data_source_id": "DS-01", "release_id": "DS-01:release"}],
    )
    client = TestClient(app)

    base = "/api/v1/opportunities/opportunity:test:1"
    assert len(client.get(base + "/history").json()) == 2
    assert client.get(base + "/evidence").json()[0]["direction"] == "positive"
    assert client.get(base + "/comparables").json()[0]["included"] is True
    assert client.get(base + "/sources").json()[0]["data_source_id"] == "DS-01"


def test_score_definition_endpoint_exposes_frozen_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.scoring.find_score_definition",
        lambda definition_id: {
            "id": definition_id,
            "version": 1,
            "strategy": "division_extension",
            "contract_path": "contracts/scoring/division-extension-v1.json",
            "contract_digest": "a" * 64,
            "feature_registry_version": 1,
            "parameters": {"parameter_status": "profiling_required"},
            "publication_eligible": False,
            "meaning": "relative ranking index",
            "active": False,
            "components": [],
            "features": [],
            "eligibility": [],
        },
    )
    response = TestClient(app).get("/api/v1/score-definitions/division-extension-v0.1")
    assert response.status_code == 200
    assert response.json()["publication_eligible"] is False


def test_scoring_endpoints_return_not_found(monkeypatch) -> None:
    monkeypatch.setattr("immo.api.routes.scoring.find_opportunity", lambda opportunity_id: None)
    response = TestClient(app).get("/api/v1/opportunities/missing")
    assert response.status_code == 404


def test_opportunity_list_uses_an_opaque_cursor(monkeypatch) -> None:
    observed_cursors: list[tuple[float | None, str | None]] = []

    def fake_list(**kwargs):
        observed_cursors.append((kwargs["cursor_score"], kwargs["cursor_id"]))
        return [summary("opportunity:test:1"), summary("opportunity:test:2")]

    monkeypatch.setattr("immo.api.routes.scoring.list_opportunities", fake_list)
    client = TestClient(app)
    first = client.get("/api/v1/opportunities", params={"limit": 1})
    second = client.get(
        "/api/v1/opportunities",
        params={"limit": 1, "cursor": first.headers["X-Next-Cursor"]},
    )

    assert observed_cursors == [(None, None), (72.5, "opportunity:test:1")]
    assert len(second.json()) == 1


def test_invalid_opportunity_cursor_is_rejected() -> None:
    response = TestClient(app).get("/api/v1/opportunities", params={"cursor": "not-base64"})
    assert response.status_code == 422
