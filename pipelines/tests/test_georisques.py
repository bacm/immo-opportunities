"""Granularité conservée, filtre vérifié, absence motivée — D3, DS-09.

Les règles de normalisation sont pures et se testent sans base. Les invariants qui portent sur le
SQL de l'import sont vérifiés sur son texte, faute de banc PostgreSQL dans `make check` — même
convention que `test_dpe.py`.
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from shapely.geometry import Point, box

from immo_pipelines.market_data.features import RiskObservation, compute_risk_features
from immo_pipelines.market_data.georisques import (
    FAMILIES,
    SourceFilterIgnored,
    _geojson_wkt,
    family,
)

REPO = Path(__file__).resolve().parents[2]
IMPORTER = REPO / "pipelines" / "scripts" / "import_georisques_release.py"
SNAPSHOT = date(2026, 9, 14)


def test_every_family_declares_its_source_srid() -> None:
    """La couche argiles est en Lambert 93, l'API répond en WGS84.

    Supposer un SRID déplacerait des géométries de plusieurs centaines de kilomètres sans
    qu'aucune contrainte ne s'en aperçoive : elles resteraient des polygones valides.
    """
    for item in FAMILIES:
        assert item.source_srid in {2154, 4326}
    assert family("clay").source_srid == 2154
    assert family("sup").source_srid == 2154
    assert family("cavity").source_srid == 4326


def test_gaspar_observations_are_always_commune_grained() -> None:
    """« La commune est concernée par un PPRI » n'est pas « la parcelle est en zone inondable »."""
    record = {
        "code_insee": "35238",
        "risques_detail": [
            {"num_risque": "11", "libelle_risque_long": "Inondation"},
            {"num_risque": "16", "libelle_risque_long": "Séisme"},
        ],
    }
    observations = list(family("gaspar-risks").normalize(record))
    assert [item.granularity for item in observations] == ["commune", "commune"]
    assert [item.risk_type for item in observations] == ["flood", "earthquake"]
    # Une observation communale n'a pas de geometrie, et le schema le fait respecter.
    assert all(item.geometry_wkt is None for item in observations)


def test_an_instruction_without_perimeter_stays_commune_grained() -> None:
    """La granularité suit la source : sans emprise, pas de zone inventée."""
    with_zone = list(
        family("soil-pollution").normalize(
            {
                "code_insee": "35238",
                "identifiant_ssp": "SSP1",
                "geom": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
                },
            }
        )
    )
    assert with_zone[0].granularity == "zone"

    without = list(
        family("soil-pollution").normalize(
            {"code_insee": "35238", "identifiant_ssp": "SSP2", "geom": None}
        )
    )
    assert without[0].granularity == "commune"
    assert without[0].geometry_wkt is None


def test_a_single_polygon_is_not_lost() -> None:
    """Ne traiter que `MultiPolygon` a coûté 1 131 observations sur 1 428, sans une erreur.

    Le découpage d'une zone par commune produit un `Polygon` dès que l'intersection est d'un seul
    tenant. L'import se terminait en succès, avec un cinquième des données.
    """
    polygon = _geojson_wkt(
        {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
    )
    assert polygon is not None and polygon.startswith("MULTIPOLYGON(((")
    multi = _geojson_wkt(
        {"type": "MultiPolygon", "coordinates": [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]]}
    )
    assert multi is not None and multi.startswith("MULTIPOLYGON(((")
    # Un type non polygonal reste refuse : l'appelant le compte plutot que de le deviner.
    assert _geojson_wkt({"type": "LineString", "coordinates": [[0, 0], [1, 1]]}) is None


def test_a_response_outside_the_department_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un paramètre territorial inconnu n'est pas rejeté par la source : il est ignoré.

    `installations_classees?code_departement=35` répond 200 avec la France entière. Importer cela
    peuplerait la base de 134 000 lignes sans qu'aucune erreur ne soit levée.
    """
    import immo_pipelines.market_data.georisques as module

    def national(url: str) -> dict[str, Any]:
        return {
            "total_pages": 1,
            "data": [{"codeInsee": "29019", "codeAIOT": "x", "latitude": 48.4, "longitude": -4.5}],
        }

    monkeypatch.setattr(module, "request", national)
    with pytest.raises(SourceFilterIgnored):
        module.fetch(family("industrial-installation"), "35", department="35")


def test_commune_context_never_becomes_a_parcel_exposure() -> None:
    """La garantie centrale du ticket, vérifiée sur le moteur.

    Une commune déclarée inondable par GASPAR ne produit aucune exposition : `RISK-002` reste
    absente avec son motif, et le périmètre n'apparaît que comme contexte communal.
    """
    unit = box(0, 0, 10, 10)
    features = compute_risk_features(
        unit,
        [
            RiskObservation(
                source_id="gaspar:35238:11",
                risk_type="flood",
                granularity="commune",
                commune_code="35238",
                geometry=None,
                coverage_known=True,
            )
        ],
        commune_code="35238",
        snapshot_at=SNAPSHOT,
        source_accepted=True,
    )
    assert features["RISK-002"].json_value is None
    assert features["RISK-002"].missing_reason == "source_value_missing"
    context = features["RISK-101"].json_value
    assert isinstance(context, dict)
    assert context["applicable"] == []
    assert [item["source_id"] for item in context["commune_context_only"]] == ["gaspar:35238:11"]


def test_absent_coverage_is_not_an_observed_zero() -> None:
    """Sans couverture connue, l'absence de risque est une absence d'information."""
    unit = box(0, 0, 10, 10)

    def cavity(*, coverage_known: bool) -> RiskObservation:
        return RiskObservation(
            source_id="cavity:1",
            risk_type="cavity",
            granularity="point",
            commune_code="35238",
            geometry=Point(100, 100),
            coverage_known=coverage_known,
        )

    far = cavity(coverage_known=False)
    unknown = compute_risk_features(
        unit, [far], commune_code="35238", snapshot_at=SNAPSHOT, source_accepted=True
    )
    assert unknown["RISK-004"].missing_reason == "source_value_missing"

    known = compute_risk_features(
        unit,
        [cavity(coverage_known=True)],
        commune_code="35238",
        snapshot_at=SNAPSHOT,
        source_accepted=True,
    )
    # Couverture connue : la distance est une mesure, pas un zero de complaisance.
    assert known["RISK-004"].numeric_value is not None
    assert known["RISK-004"].numeric_value > 0


def test_an_unaccepted_family_disables_its_features() -> None:
    features = compute_risk_features(
        box(0, 0, 10, 10),
        [],
        commune_code="35238",
        snapshot_at=SNAPSHOT,
        source_accepted=False,
    )
    for code in ("RISK-001", "RISK-002", "RISK-003", "RISK-004", "RISK-101"):
        assert features[code].missing_reason == "source_not_accepted"


def test_the_import_keeps_the_record_when_its_geometry_cannot_be_repaired() -> None:
    """Une géométrie irréparable ne fait pas disparaître l'observation.

    Elle la fait descendre en précision — `commune` — avec son motif. Descendre est sûr : on
    affirme moins que la source. C'est l'inverse que le ticket interdit.
    """
    source = IMPORTER.read_text(encoding="utf-8")
    assert "ST_MakeValid" in source
    assert "CASE WHEN usable THEN granularity ELSE 'commune' END" in source
    assert "'geometry_quarantined', 'unrepairable_geometry'" in source
    assert "INSERT INTO meta.geometry_quarantine" in source


def test_the_import_uses_the_family_srid_and_purges_the_whole_release() -> None:
    source = IMPORTER.read_text(encoding="utf-8")
    assert "item.source_srid" in source
    assert "SOURCE_SRID" not in source
    body = source[source.index("def main()") :]
    purge = body[body.index("DELETE FROM observation.risk_observation") :][:120]
    assert "WHERE release_id = %s" in purge
    assert "NOT LIKE" not in purge


def test_a_record_producing_nothing_is_counted() -> None:
    """Ce qui empêche une perte silencieuse de recommencer."""
    assert 'counters["yielded_nothing"] += 1' in IMPORTER.read_text(encoding="utf-8")
