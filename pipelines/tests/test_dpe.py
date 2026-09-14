"""Éligibilité, appariement déclaré et neutralité de l'absence — D4, DS-07.

Les règles de lecture sont pures et se testent sur un extrait fabriqué. Les invariants qui
portent sur le SQL de l'import sont vérifiés sur son texte, faute de banc PostgreSQL dans
`make check` — même convention que `test_spatial_matching_report.py`.
"""

import csv
import gzip
import importlib.util
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from immo_pipelines.market_data.dpe import (
    DPE_TRANSFORMATION_VERSION,
    Assessment,
    Rejection,
    classify,
    missing_columns,
    read_extract,
)
from immo_pipelines.market_data.features import (
    BuildingObservation,
    EnergyAssessment,
    compute_renovation_features,
    select_energy_assessment,
)
from immo_pipelines.scoring.engine import (
    ConfidenceInputs,
    FeatureInput,
    load_score_definition,
    score_opportunity,
)

REPO = Path(__file__).resolve().parents[2]
IMPORTER = REPO / "pipelines" / "scripts" / "import_dpe_release.py"
PINNER = REPO / "pipelines" / "scripts" / "pin_dpe_release.py"
SNAPSHOT = date(2026, 9, 9)

COLUMNS = (
    "numero_dpe",
    "date_etablissement_dpe",
    "date_reception_dpe",
    "modele_dpe",
    "etiquette_dpe",
    "conso_5_usages_par_m2_ep",
    "code_insee_ban",
    "id_rnb",
    "provenance_id_rnb",
    "identifiant_ban",
    "score_ban",
    "statut_geocodage",
    "type_batiment",
    "periode_construction",
    "qualite_isolation_murs",
    "qualite_isolation_plancher bas",
    "dpe_desactive",
)

GEOCODED = "adresse géocodée ban à l'adresse"
NOT_GEOCODED = "adresse non géocodée ban car aucune correspondance trouvée"


def row(**overrides: str) -> dict[str, str]:
    base = dict.fromkeys(COLUMNS, "")
    base.update(
        {
            "numero_dpe": "2635E0004998U",
            "date_etablissement_dpe": "2026-01-02",
            "date_reception_dpe": "2026-01-02",
            "modele_dpe": "DPE 3CL 2021 méthode logement",
            "etiquette_dpe": "F",
            "conso_5_usages_par_m2_ep": "293",
            "code_insee_ban": "35360",
            "identifiant_ban": "35360_1875_00016",
            "score_ban": "0.61",
            "statut_geocodage": GEOCODED,
            "type_batiment": "maison",
            "periode_construction": "1948-1974",
            "qualite_isolation_murs": "insuffisante",
            "qualite_isolation_plancher bas": "moyenne",
        }
    )
    base.update(overrides)
    return base


def load(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        # Une etiquette predite ne porte pas de modele reglementaire : la liste fermee des
        # modeles est ce qui tient l'interdit « aucun DPE simule » sur une source qui ne marque
        # pas la simulation.
        ({"modele_dpe": "BDNB Expert prédiction"}, "unknown_assessment_model"),
        ({"modele_dpe": ""}, "unknown_assessment_model"),
        ({"dpe_desactive": "1"}, "deactivated"),
        ({"date_etablissement_dpe": "2026-09-10"}, "after_snapshot"),
        ({"date_reception_dpe": ""}, "not_deposited"),
        ({"numero_dpe": ""}, "identifier_missing"),
        ({"date_etablissement_dpe": "pas une date"}, "assessment_date_missing"),
        ({"code_insee_ban": ""}, "commune_missing"),
    ],
)
def test_ineligible_records_are_rejected_with_a_reason(
    overrides: dict[str, str], reason: str
) -> None:
    result = classify(row(**overrides), snapshot_at=SNAPSHOT)
    assert isinstance(result, Rejection)
    assert result.reason == reason
    # Le motif n'est jamais vide : c'est lui qui rend le rejet auditable.
    assert result.detail


def test_an_eligible_record_keeps_its_declared_identifiers_and_envelope() -> None:
    result = classify(
        row(id_rnb="RS85TS7QYFDZ", provenance_id_rnb="Reprise RNB"), snapshot_at=SNAPSHOT
    )
    assert isinstance(result, Assessment)
    assert result.dpe_number == "2635E0004998U"
    assert result.rnb_id == "RS85TS7QYFDZ"
    assert result.ban_id == "35360_1875_00016"
    assert result.energy_label == "F"
    assert result.consumption_kwh_m2_year == 293
    # La colonne s'ecrit avec une espace dans l'export CSV : la nommer autrement ferait
    # disparaitre la caracteristique sans bruit.
    assert result.envelope["lower_floor"] == "moyenne"
    assert result.envelope["walls"] == "insuffisante"
    assert result.properties["provenance_id_rnb"] == "Reprise RNB"


def test_a_contradicted_geocoding_status_is_flagged_without_dropping_the_address() -> None:
    contradicted = classify(row(statut_geocodage=NOT_GEOCODED), snapshot_at=SNAPSHOT)
    assert isinstance(contradicted, Assessment)
    # L'adresse reste : la jointure d'identifiant est verifiable. C'est la confiance qui
    # deviendra absente avec son motif, cote import.
    assert contradicted.ban_id == "35360_1875_00016"
    assert contradicted.geocoding_contradicted is True

    plain = classify(row(), snapshot_at=SNAPSHOT)
    assert isinstance(plain, Assessment)
    assert plain.geocoding_contradicted is False


def test_reading_an_extract_yields_both_assessments_and_rejections(tmp_path: Path) -> None:
    path = tmp_path / "assessments.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(row(numero_dpe="A", id_rnb="RS85TS7QYFDZ"))
        writer.writerow(row(numero_dpe="B", modele_dpe="prédiction"))
        # Une description d'installation contient des retours a la ligne dans la source reelle :
        # l'extrait se lit avec un lecteur CSV, jamais ligne a ligne.
        writer.writerow(row(numero_dpe="C", type_batiment="maison\navec retour"))

    records = list(read_extract(path, snapshot_at=SNAPSHOT))
    assert [type(record).__name__ for record in records] == [
        "Assessment",
        "Rejection",
        "Assessment",
    ]
    assert records[2].properties["type_batiment"] == "maison\navec retour"  # type: ignore[union-attr]


def test_an_extract_missing_a_required_column_is_caught_before_any_write(
    tmp_path: Path,
) -> None:
    """Un changement de schéma amont arrête l'import, il ne produit pas des lignes vides."""
    complete = tmp_path / "complete.csv.gz"
    with gzip.open(complete, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(row())
    assert missing_columns(complete) == ()

    truncated = tmp_path / "truncated.csv.gz"
    kept = [column for column in COLUMNS if column not in {"id_rnb", "score_ban"}]
    with gzip.open(truncated, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=kept)
        writer.writeheader()
    assert set(missing_columns(truncated)) == {"id_rnb", "score_ban"}


def test_multiple_address_level_assessments_stay_ambiguous() -> None:
    """Le contrat DS-07 bloque la publication tant qu'une adresse porte plusieurs diagnostics."""
    selection = select_energy_assessment(
        [
            EnergyAssessment("dpe-1", date(2025, 1, 1), "F", 350, True, address_id="a"),
            EnergyAssessment("dpe-2", date(2025, 2, 1), "C", 130, True, address_id="a"),
        ],
        building_id="b",
        address_ids={"a"},
        snapshot_at=SNAPSHOT,
    )
    assert selection.assessment is None
    assert selection.missing_reason == "ambiguous_match"


def test_the_selected_assessment_reference_stays_verifiable() -> None:
    selection = select_energy_assessment(
        [
            EnergyAssessment(
                "2635E0004998U",
                date(2026, 1, 2),
                "F",
                293,
                True,
                building_id="building:rnb:RS85TS7QYFDZ",
                match_confidence=1,
            )
        ],
        building_id="building:rnb:RS85TS7QYFDZ",
        address_ids=set(),
        snapshot_at=SNAPSHOT,
    )
    features = compute_renovation_features(
        [BuildingObservation("DS-04:b", "1948-1974", 93)],
        selection,
        snapshot_at=SNAPSHOT,
        dpe_source_accepted=True,
    )
    # Le numero du diagnostic retenu voyage avec chaque feature qu'il alimente : sans lui, une
    # etiquette F ne serait plus verifiable contre la source.
    for code in ("REN-004", "REN-005", "REN-006", "REN-007", "REN-008"):
        assert features[code].source_ids == ("2635E0004998U",) or features[code].missing_reason


def _inputs(with_dpe: bool) -> list[FeatureInput]:
    values: dict[str, float | None] = {
        "LAND-002": 0.5,
        "BLD-001": 0.5,
        "REN-002": 0.5,
        "MKT-101": 0.5,
        "FIN-101": 0.5,
        "FIN-102": 0.5,
        "FIN-103": 0.5,
        "FIN-104": 0.7,
        "FIN-105": 0.6,
        "FIN-106": 0.5,
        "REN-001": 0.5,
        "REN-003": 0.5,
    }
    if with_dpe:
        values["REN-005"] = 0.9
        values["REN-007"] = 0.8
        values["REN-008"] = 1.0
    return [
        FeatureInput(code=code, value=value, profiled_score=value, local_percentile=value)
        for code, value in values.items()
    ]


def test_missing_dpe_changes_no_score_contribution_only_confidence() -> None:
    """L'interdit central de DS-07, vérifié plutôt qu'affirmé.

    Un bien sans diagnostic récent ressemble superficiellement à un bien inoccupé. Le produit ne
    fait pas de prédiction de vacance : l'absence ne pèse sur aucune composante, elle ne réduit
    que la confiance.
    """
    definition = load_score_definition(REPO / "contracts" / "scoring" / "renovation-resale-v1.json")
    confident = ConfidenceInputs(
        match_quality=1, freshness=1, source_consistency=1, comparable_quality=1
    )
    without = score_opportunity(
        definition,
        _inputs(with_dpe=False),
        snapshot_at=SNAPSHOT,
        release_ids=("DS-07@2026-09-14-extract",),
        confidence_inputs=confident,
    )

    dpe_evidence = [item for item in without.evidence if item.feature_code.startswith("REN-0")]
    absent = [item for item in dpe_evidence if item.feature_code in {"REN-005", "REN-007"}]
    assert absent, "les features DPE doivent figurer dans la preuve, même absentes"
    for item in absent:
        assert item.impact == 0
        assert item.direction == "neutral"
    assert "REN-005" in without.missing_features

    reduced = ConfidenceInputs(
        match_quality=0.4, freshness=1, source_consistency=1, comparable_quality=1
    )
    degraded = score_opportunity(
        definition,
        _inputs(with_dpe=False),
        snapshot_at=SNAPSHOT,
        release_ids=("DS-07@2026-09-14-extract",),
        confidence_inputs=reduced,
    )
    # Seule la confiance bouge : le classement, lui, est inchangé.
    assert degraded.overall_score == without.overall_score
    assert degraded.confidence_score < without.confidence_score


def test_the_import_identity_carries_the_transformation_version() -> None:
    """Sans elle, un correctif de code n'atteint jamais les données — constaté sur BUG-09."""
    module = load(IMPORTER)
    identity = module.assessment_id("DS-07@2026-09-14-extract", "2635E0004998U")
    assert f":v{DPE_TRANSFORMATION_VERSION}:" in identity

    source = IMPORTER.read_text(encoding="utf-8")
    assert "DPE_TRANSFORMATION_VERSION" in source.split("idempotency_key = (")[1][:200]
    # Et les etats successifs ne coexistent pas : dans `main`, la purge precede le chargement.
    body = source[source.index("def main()") :]
    assert body.index("DELETE FROM observation.energy_assessment") < body.index(
        "counters = stage_rows("
    )
    # La purge porte sur la release entiere, pas sur ses seules autres versions : sinon un
    # reimport de la meme version bute sur `energy_assessment_pkey` et un run interrompu ne
    # repart jamais. Constate en verifiant le critere « reimport stable ».
    purge = body[body.index("DELETE FROM observation.energy_assessment") :][:200]
    assert "WHERE release_id = %(release_id)s" in purge
    assert "NOT LIKE" not in purge


def test_the_import_matches_on_declared_identifiers_only() -> None:
    """B4 a établi qu'aucune règle géométrique ne rend l'appariement d'adresse vérifiable."""
    source = IMPORTER.read_text(encoding="utf-8")
    joins = source[source.index("CREATE TEMP TABLE dpe_resolved") : source.index("INSERT INTO obs")]
    assert "'building:rnb:' || stage.rnb_id" in joins
    assert "'address:ban:' || stage.ban_id" in joins
    for geometric in ("ST_", "geom", "DWithin", "distance"):
        assert geometric not in joins


def test_the_pinned_extract_names_an_archive_because_the_api_is_not_a_path_back() -> None:
    source = PINNER.read_text(encoding="utf-8")
    # Le gzip ne doit dependre que des donnees : sans `mtime=0`, deux epinglages du meme contenu
    # auraient deux empreintes differentes et le checksum ne prouverait plus rien.
    assert "mtime=0" in source
    assert '"archive": {"object_key": object_key(release, department)}' in source
