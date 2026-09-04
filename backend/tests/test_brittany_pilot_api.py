from fastapi.testclient import TestClient

from immo.main import create_app


def test_readiness_keeps_uncovered_departments_visible(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.brittany_pilot.get_brittany_readiness",
        lambda principal: {
            "publishable": False,
            "blockers": ["regional_data_not_covered"],
            "territories": {
                code: {"covered": code == "35", "sources": []} for code in ("22", "29", "35", "56")
            },
            "active_score_count": 0,
            "segmentation": {"id": "brittany-market-segments", "version": 1, "status": "draft"},
            "active_bundle": None,
        },
    )

    response = TestClient(create_app()).get("/api/v1/admin/brittany/readiness")

    assert response.status_code == 200
    assert response.json()["publishable"] is False
    assert set(response.json()["territories"]) == {"22", "29", "35", "56"}


def test_regional_publication_requires_a_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        "immo.api.routes.brittany_pilot.publish_brittany",
        lambda principal, reason: {"bundle_id": "brittany:" + "a" * 36, "status": "published"},
    )
    client = TestClient(create_app())

    invalid = client.post("/api/v1/admin/brittany/publications", json={"reason": "x"})
    valid = client.post(
        "/api/v1/admin/brittany/publications", json={"reason": "Validation pilote Bretagne"}
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["status"] == "published"
