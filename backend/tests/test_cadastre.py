from typing import Any

from fastapi.testclient import TestClient

from immo.main import app


def parcel_record() -> dict[str, Any]:
    checksum = "a" * 64
    return {
        "cadastral_id": "35238000AB0001",
        "department_code": "35",
        "commune_code": "35238",
        "prefix": "000",
        "section": "AB",
        "number": "0001",
        "stated_area_m2": 420,
        "geometry": {"type": "MultiPolygon", "coordinates": []},
        "provenance": {
            "data_source_id": "DS-01",
            "release_id": "DS-01@2026-06-01",
            "release_key": "2026-06-01",
            "source_published_on": "2026-06-01",
            "raw_asset_id": 1,
            "layer": "parcelles",
            "source_url": "https://cadastre.data.gouv.fr/source.json.gz",
            "object_key": "DS-01/2026-06-01/35/parcelles.json.gz",
            "sha256": checksum,
            "source_row_number": 1,
            "record_checksum": checksum,
            "transformation_version": "cadastre-normalize@1",
            "was_repaired": False,
            "repair_method": None,
        },
    }


def test_get_active_parcel_with_complete_provenance(monkeypatch: Any) -> None:
    monkeypatch.setattr("immo.api.routes.cadastre.find_active_parcel", lambda _: parcel_record())

    response = TestClient(app).get("/api/v1/cadastre/parcels/35238000AB0001")

    assert response.status_code == 200
    assert response.json()["provenance"]["raw_asset_id"] == 1
    assert response.json()["geometry"]["type"] == "MultiPolygon"


def test_get_unknown_active_parcel(monkeypatch: Any) -> None:
    monkeypatch.setattr("immo.api.routes.cadastre.find_active_parcel", lambda _: None)

    response = TestClient(app).get("/api/v1/cadastre/parcels/unknown")

    assert response.status_code == 404
