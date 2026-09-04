from typing import Any

from fastapi.testclient import TestClient

from immo.main import app


def summary() -> dict[str, Any]:
    return {
        "id": "property-unit:parcel:35238000AB0001",
        "cadastral_id": "35238000AB0001",
        "commune_code": "35238",
        "commune_name": "Rennes",
        "area_m2": 518.4,
        "building_count": 1,
        "building_footprint_m2": 104.2,
        "center": [-1.677, 48.111],
    }


def detail(entity_type: str = "parcel") -> dict[str, Any]:
    return {
        "id": "parcel:cadastre:35238000AB0001",
        "entity_type": entity_type,
        "label": "35238000AB0001",
        "commune_code": "35238",
        "commune_name": "Rennes",
        "department_code": "35",
        "area_m2": 518.4,
        "center": [-1.677, 48.111],
        "bbox": [-1.678, 48.110, -1.676, 48.112],
        "geometry": {"type": "MultiPolygon", "coordinates": []},
        "properties": {"section": "AB", "number": "1"},
        "related_entities": [],
        "sources": [{"data_source_id": "DS-01"}],
    }


def test_areas_contract(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_areas",
        lambda department_code, area_type: [
            {
                "id": "area:commune:35238",
                "area_type": "commune",
                "code": "35238",
                "name": "Rennes",
                "department_code": department_code,
                "center": [-1.677, 48.111],
                "bbox": [-1.80, 48.02, -1.55, 48.20],
            }
        ],
    )

    response = TestClient(app).get("/api/v1/areas")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Rennes"


def test_search_supports_real_entity_types(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.explorer.search_entities",
        lambda query, department_code, limit: [
            {
                "entity_type": "parcel",
                "id": "parcel:cadastre:35238000AB0001",
                "label": "35238000AB0001",
                "secondary_label": "Parcelle · 35238",
                "center": [-1.677, 48.111],
                "bbox": [-1.678, 48.110, -1.676, 48.112],
            }
        ],
    )

    response = TestClient(app).get("/api/v1/search?query=35238000AB0001")

    assert response.status_code == 200
    assert response.json()[0]["entity_type"] == "parcel"


def test_viewport_distinguishes_partial_and_outside_coverage(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_property_units_in_viewport",
        lambda **_: {"coverage": "outside_coverage", "partial": False, "items": []},
    )

    response = TestClient(app).get("/api/v1/property-units?west=-2.1&south=48&east=-2&north=48.1")

    assert response.status_code == 200
    assert response.json() == {
        "coverage": "outside_coverage",
        "partial": False,
        "items": [],
    }


def test_viewport_rejects_department_sized_download() -> None:
    response = TestClient(app).get("/api/v1/property-units?west=-2.5&south=47.5&east=-1&north=49")

    assert response.status_code == 422


def test_entity_detail_contract(monkeypatch: Any) -> None:
    monkeypatch.setattr("immo.api.routes.explorer.find_parcel", lambda _: detail())

    response = TestClient(app).get("/api/v1/parcels/parcel:cadastre:35238000AB0001")

    assert response.status_code == 200
    assert response.json()["sources"][0]["data_source_id"] == "DS-01"
