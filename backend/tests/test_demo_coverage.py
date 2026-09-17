"""Une commune sans cadastre importé n'est pas couverte, même sous un pointeur actif — A6.

La démo restaure cinq communes sous les pointeurs actifs du département entier. Avant A6, le
pointeur DS-01 suffisait à déclarer une commune couverte, et toute commune bretonne suffisait à
couvrir une fenêtre de carte : hors des cinq communes, l'application aurait présenté une absence
de donnée comme une absence d'objet. Le défaut existait déjà sur la base complète, qui déclarait
couverts les Côtes-d'Armor, le Finistère et le Morbihan.
"""

from typing import Any

import pytest

from immo import explorer, spatial


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]], scalar: Any = None) -> None:
        self.rows = rows
        self.scalar = scalar

    def mappings(self) -> list[dict[str, Any]]:
        return self.rows

    def scalar_one(self) -> Any:
        return self.scalar


class FakeEngine:
    """Rend, dans l'ordre, les résultats prévus, et garde le texte de chaque requête."""

    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.statements: list[str] = []

    def connect(self) -> "FakeEngine":
        return self

    def __enter__(self) -> "FakeEngine":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, statement: Any, _parameters: dict[str, Any]) -> FakeResult:
        self.statements.append(str(statement))
        return self.results.pop(0)


def source_row(source_id: str, *, release: bool, records: int, has_parcels: bool) -> dict[str, Any]:
    return {
        "commune_code": "35001",
        "commune_name": "Acigné",
        "department_code": "35",
        "has_parcels": has_parcels,
        "data_source_id": source_id,
        "source_name": source_id,
        "release_id": f"{source_id}@2026" if release else None,
        "acceptance_status": "accepted" if release else None,
        "record_count": records,
    }


def coverage(monkeypatch: pytest.MonkeyPatch, *, has_parcels: bool, records: int) -> Any:
    rows = [
        source_row(source_id, release=True, records=records, has_parcels=has_parcels)
        for source_id in spatial.SPATIAL_SOURCE_IDS
    ]
    engine = FakeEngine(FakeResult(rows))
    monkeypatch.setattr(spatial, "get_engine", lambda: engine)
    return spatial.commune_coverage("35001"), engine


def test_an_active_cadastre_without_local_parcels_does_not_cover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, engine = coverage(monkeypatch, has_parcels=False, records=0)
    assert record["state"] == "not_covered"
    assert "reference.parcel" in engine.statements[0]


def test_local_parcels_cover_under_the_cadastre_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    record, _ = coverage(monkeypatch, has_parcels=True, records=0)
    assert record["state"] == "partial"
    assert [source["data_source_id"] for source in record["sources"] if source["covered"]] == [
        "DS-01"
    ]


def test_all_sources_with_local_data_cover(monkeypatch: pytest.MonkeyPatch) -> None:
    record, _ = coverage(monkeypatch, has_parcels=True, records=3)
    assert record["state"] == "covered"


def viewport(monkeypatch: pytest.MonkeyPatch, engine: FakeEngine) -> Any:
    monkeypatch.setattr(explorer, "get_engine", lambda: engine)
    return explorer.list_property_units_in_viewport(
        west=-1.7, south=48.1, east=-1.6, north=48.2, limit=10
    )


def parcel_row() -> dict[str, Any]:
    return {
        "id": "parcel:35238000AB0001",
        "cadastral_id": "35238000AB0001",
        "commune_code": "35238",
        "commune_name": "Rennes",
        "area_m2": 518.4,
        "building_count": 1,
        "building_footprint_m2": 104.2,
        "longitude": -1.677,
        "latitude": 48.111,
    }


def test_a_visible_parcel_is_enough_to_cover_the_viewport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine(FakeResult([parcel_row()]))
    result = viewport(monkeypatch, engine)
    assert result["coverage"] == "covered"
    assert len(engine.statements) == 1


def test_an_empty_viewport_is_covered_only_by_a_commune_with_parcels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine(FakeResult([]), FakeResult([], scalar=False))
    result = viewport(monkeypatch, engine)
    assert result == {"coverage": "outside_coverage", "partial": False, "items": []}
    assert "reference.parcel" in engine.statements[1]
