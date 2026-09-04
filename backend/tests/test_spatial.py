from typing import Any

from fastapi.testclient import TestClient

from immo.main import app


def match_record(decision: str = "certain") -> dict[str, Any]:
    return {
        "id": 42,
        "candidate_group_key": "address:BAN-A:parcel",
        "left_entity_type": "address",
        "left_entity_id": "address:ban:BAN-A",
        "right_entity_type": "parcel",
        "right_entity_id": "parcel:cadastre:35238000AB0001",
        "method": "source_relation",
        "algorithm_code": "address-parcel",
        "algorithm_version": "1",
        "confidence": 0.97,
        "decision": decision,
        "critical": True,
        "blocks_publication": decision == "ambiguous",
        "rationale": "BAN cad_parcelles relation confirmed by point-in-polygon",
        "evidence": {"ban_relation": True, "point_inside": True},
        "release_ids": ["DS-01@2026-06-01", "DS-05@2026-08-05"],
        "left_source_identifiers": [
            {
                "data_source_id": "DS-05",
                "source_entity_type": "ban_address",
                "source_identifier": "BAN-A",
                "is_preferred": True,
            }
        ],
        "right_source_identifiers": [
            {
                "data_source_id": "DS-01",
                "source_entity_type": "cadastral_parcel",
                "source_identifier": "35238000AB0001",
                "is_preferred": True,
            }
        ],
        "reviews": [],
    }


def test_search_addresses(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.spatial.search_addresses",
        lambda query, commune_code, limit: [
            {
                "id": "address:ban:BAN-A",
                "display_label": "1 rue Exemple 35000 Rennes",
                "commune_code": "35238",
                "department_code": "35",
                "longitude": -1.67,
                "latitude": 48.11,
            }
        ],
    )

    response = TestClient(app).get("/api/v1/spatial/addresses?query=exemple")

    assert response.status_code == 200
    assert response.json()[0]["commune_code"] == "35238"


def test_address_context_exposes_explainable_matches(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.spatial.find_address_context",
        lambda _: {
            "address": {
                "id": "address:ban:BAN-A",
                "display_label": "1 rue Exemple 35000 Rennes",
                "commune_code": "35238",
                "department_code": "35",
                "longitude": -1.67,
                "latitude": 48.11,
            },
            "matches": [match_record()],
        },
    )

    response = TestClient(app).get("/api/v1/spatial/addresses/address:ban:BAN-A")

    assert response.status_code == 200
    assert response.json()["matches"][0]["rationale"].startswith("BAN")
    assert (
        response.json()["matches"][0]["right_source_identifiers"][0]["source_identifier"]
        == "35238000AB0001"
    )


def test_match_inspection_distinguishes_ambiguous_case(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.spatial.find_entity_match", lambda _: match_record("ambiguous")
    )

    response = TestClient(app).get("/api/v1/spatial/matches/42")

    assert response.status_code == 200
    assert response.json()["decision"] == "ambiguous"
    assert response.json()["blocks_publication"] is True


def test_unknown_match(monkeypatch: Any) -> None:
    monkeypatch.setattr("immo.api.routes.spatial.find_entity_match", lambda _: None)

    response = TestClient(app).get("/api/v1/spatial/matches/999")

    assert response.status_code == 404
