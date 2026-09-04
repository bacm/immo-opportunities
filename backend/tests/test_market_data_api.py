from datetime import date

from fastapi.testclient import TestClient

from immo.main import app


def test_market_context_endpoint_exposes_dated_sources(monkeypatch) -> None:
    def fake_context(property_unit_id: str, *, snapshot_at: str):
        return {
            "property_unit_id": property_unit_id,
            "snapshot_at": snapshot_at,
            "comparables": [
                {
                    "included": True,
                    "reason": "included",
                    "transaction_date": "2025-01-01",
                    "release_ids": ["DS-06:release"],
                }
            ],
            "energy_assessment": {
                "assessment_date": "2025-02-01",
                "release_id": "DS-07:release",
            },
            "urban_zone": {"zone_code": "U", "release_id": "DS-08:release"},
            "risks": [{"granularity": "commune", "applies_to_unit": False}],
        }

    monkeypatch.setattr("immo.api.routes.market_data.find_market_context", fake_context)
    response = TestClient(app).get(
        "/api/v1/property-units/property-unit:test/market-context",
        params={"snapshot_at": date(2026, 1, 1).isoformat()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparables"][0]["reason"] == "included"
    assert payload["energy_assessment"]["release_id"] == "DS-07:release"
    assert payload["risks"][0]["applies_to_unit"] is False


def test_market_context_endpoint_returns_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.market_data.find_market_context",
        lambda property_unit_id, snapshot_at: None,
    )
    response = TestClient(app).get(
        "/api/v1/property-units/missing/market-context",
        params={"snapshot_at": "2026-01-01"},
    )
    assert response.status_code == 404


def test_coverage_endpoint_distinguishes_missing_metrics_from_zero(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.market_data.list_market_data_coverage",
        lambda commune_code: [
            {
                "data_source_id": "DS-06",
                "release_id": "DS-06:release",
                "acceptance_status": "accepted",
                "source_published_on": "2026-01-01",
                "record_count": 0,
                "matched_record_count": 0,
                "coverage_ratio": 0,
                "freshest_observation_at": None,
                "measured_at": "2026-01-02T10:00:00+00:00",
            },
            {
                "data_source_id": "DS-07",
                "release_id": None,
                "acceptance_status": None,
                "source_published_on": None,
                "record_count": None,
                "matched_record_count": None,
                "coverage_ratio": None,
                "freshest_observation_at": None,
                "measured_at": None,
            },
        ],
    )
    response = TestClient(app).get("/api/v1/market-data/coverage", params={"commune_code": "35000"})
    assert response.status_code == 200
    assert response.json()[0]["record_count"] == 0
    assert response.json()[1]["record_count"] is None
