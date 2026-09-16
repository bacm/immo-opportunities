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


def assessment(relation_status: str = "certain", **overrides: Any) -> dict[str, Any]:
    record = {
        "dpe_number": "2435E2759411R",
        "assessment_date": "2024-07-31",
        "energy_label": "C",
        "energy_consumption_kwh_m2_year": 165.8,
        "surface_habitable_m2": 60.0,
        "building_type": "appartement",
        "building_id": "building:rnb:VVBARFKE1VCT",
        "relation_status": relation_status,
        "identifier_provenance": "Reprise RNB",
        "address_label": "21 Rue Parmentier 35700 Rennes",
        "release_id": "DS-07@2026-09-14-extract",
        "data_source_id": "DS-07",
    }
    return record | overrides


def test_parcel_energy_assessments_contract(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_parcel_energy_assessments",
        lambda _: [assessment()],
    )

    response = TestClient(app).get(
        "/api/v1/parcels/parcel:cadastre:35238000AX0341/energy-assessments"
    )

    assert response.status_code == 200
    assert response.json()[0]["identifier_provenance"] == "Reprise RNB"


def test_parcel_energy_assessments_keep_ambiguous_attachment_visible(monkeypatch: Any) -> None:
    """Un rattachement ambigu doit traverser l'API, pas être filtré — D6b.

    Un bâtiment chevauche 2,24 parcelles en moyenne. Si la route ne laissait passer que le
    certain, l'écran de vérification cacherait précisément la population qu'il doit montrer ;
    s'il la laissait passer sans la distinguer, il attribuerait le diagnostic à la mauvaise
    parcelle. Les deux sont des défauts, et seul le second est visible à l'œil.
    """
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_parcel_energy_assessments",
        lambda _: [assessment(relation_status="ambiguous")],
    )

    response = TestClient(app).get(
        "/api/v1/parcels/parcel:cadastre:35238000AX0341/energy-assessments"
    )

    assert response.status_code == 200
    assert response.json()[0]["relation_status"] == "ambiguous"


def test_parcel_energy_assessments_keep_missing_values_missing(monkeypatch: Any) -> None:
    """Une surface non déclarée reste nulle, jamais convertie en zéro.

    5 761 diagnostics n'ont aucune surface habitable côté source, et les DPE « immeuble
    collectif » n'en portent pas par construction. Un zéro laisserait croire à une surface
    mesurée à zéro.
    """
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_parcel_energy_assessments",
        lambda _: [assessment(surface_habitable_m2=None, building_type="immeuble")],
    )

    response = TestClient(app).get(
        "/api/v1/parcels/parcel:cadastre:35238000AX0341/energy-assessments"
    )

    assert response.status_code == 200
    assert response.json()[0]["surface_habitable_m2"] is None


def test_parcel_energy_assessments_name_their_source(monkeypatch: Any) -> None:
    """Un DPE neuf (DS-13) traverse l'API avec sa source, pour que l'écran le distingue — D9."""
    monkeypatch.setattr(
        "immo.api.routes.explorer.list_parcel_energy_assessments",
        lambda _: [
            assessment(),
            assessment(
                dpe_number="2235N0000001X",
                release_id="DS-13@2026-09-16-extract",
                data_source_id="DS-13",
            ),
        ],
    )

    response = TestClient(app).get(
        "/api/v1/parcels/parcel:cadastre:35024000AP0209/energy-assessments"
    )

    assert response.status_code == 200
    assert [row["data_source_id"] for row in response.json()] == ["DS-07", "DS-13"]


def test_energy_assessment_lookup_shows_a_rejected_dpe_with_its_reason(monkeypatch: Any) -> None:
    """Un DPE écarté à l'import se retrouve par son numéro, avec son motif — C7."""
    monkeypatch.setattr(
        "immo.api.routes.explorer.find_energy_assessment",
        lambda number: {
            "dpe_number": number,
            "stored": [],
            "rejected": [
                {
                    "release_id": "DS-13@2026-09-16-extract",
                    "data_source_id": "DS-13",
                    "attribute": "target",
                    "reason_code": "unresolved_source_identifier",
                    "reason_detail": "aucun identifiant déclaré ne se résout dans le référentiel",
                    "declared": {"id_rnb": None, "identifiant_ban": "35095_0001"},
                }
            ],
        },
    )

    response = TestClient(app).get("/api/v1/energy-assessments/2135N0105211H")

    assert response.status_code == 200
    rejected = response.json()["rejected"][0]
    assert rejected["reason_code"] == "unresolved_source_identifier"
    # Un identifiant absent reste absent, il ne devient pas une chaîne vide.
    assert rejected["declared"]["id_rnb"] is None


def test_energy_assessment_lookup_says_unknown(monkeypatch: Any) -> None:
    monkeypatch.setattr("immo.api.routes.explorer.find_energy_assessment", lambda _: None)
    assert TestClient(app).get("/api/v1/energy-assessments/2135N0000000X").status_code == 404


def test_energy_assessment_lookup_rejects_a_malformed_number() -> None:
    assert TestClient(app).get("/api/v1/energy-assessments/abc").status_code == 422
