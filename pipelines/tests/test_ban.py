import csv
import gzip
from pathlib import Path

import pytest

from immo_pipelines.spatial.ban import (
    BAN_IDENTITY_FIELDS,
    BAN_REQUIRED_COLUMNS,
    BanCensus,
    BanQuarantine,
    BanRecord,
    census_ban_archive,
    iter_ban_records,
    normalize_address_label,
)
from immo_pipelines.spatial.importer import BAN_QUARANTINABLE_ATTRIBUTES


def write_ban_archive(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted(BAN_REQUIRED_COLUMNS | {"id_fantoir", "rep", "cad_parcelles"})
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def ban_row() -> dict[str, str]:
    return {
        "id": "35238_0001_00001",
        "id_fantoir": "35238_0001",
        "numero": "1",
        "rep": "bis",
        "nom_voie": "Rue de l'Été",
        "code_postal": "35000",
        "code_insee": "35238",
        "nom_commune": "Rennes",
        "x": "351234.5",
        "y": "6789234.5",
        "cad_parcelles": "35238000AB0001|35238000AB0002",
    }


def test_ban_reader_preserves_identifiers_and_multiple_parcels(tmp_path: Path) -> None:
    archive = tmp_path / "ban.csv.gz"
    write_ban_archive(archive, [ban_row()])

    record = next(iter_ban_records(archive))

    assert isinstance(record, BanRecord)
    assert record.ban_id == "35238_0001_00001"
    assert record.fantoir_id == "35238_0001"
    assert record.cadastral_ids == ("35238000AB0001", "35238000AB0002")
    assert record.normalized_label == "1 bis rue de l ete 35000 rennes"
    assert record.geometry_wkt.startswith("POINT")
    assert len(record.record_checksum) == 64


def test_ban_address_without_parcel_is_valid_and_not_forced_to_match(tmp_path: Path) -> None:
    archive = tmp_path / "ban.csv.gz"
    row = ban_row()
    row["cad_parcelles"] = ""
    write_ban_archive(archive, [row])

    record = next(iter_ban_records(archive))

    assert isinstance(record, BanRecord)
    assert record.cadastral_ids == ()


def test_invalid_ban_coordinates_are_quarantined(tmp_path: Path) -> None:
    archive = tmp_path / "ban.csv.gz"
    row = ban_row()
    row["x"] = "not-a-number"
    write_ban_archive(archive, [row])

    record = next(iter_ban_records(archive))

    assert isinstance(record, BanQuarantine)
    assert record.reason_code == "invalid_ban_record"


def test_address_normalization_is_case_and_accent_insensitive() -> None:
    assert normalize_address_label("  Rue de l'ÉTÉ — Rennes ") == "rue de l ete rennes"


def read_records(path: Path, rows: list[dict[str, str]]) -> list[BanRecord]:
    write_ban_archive(path, rows)
    records = list(iter_ban_records(path))
    assert all(isinstance(record, BanRecord) for record in records)
    return [record for record in records if isinstance(record, BanRecord)]


def test_divergent_position_keeps_the_address_identity_intact(tmp_path: Path) -> None:
    """Cas réel majoritaire : 216 des 217 identifiants conflictuels du 35 ne divergent que
    par leur position. L'identité doit rester reconnue comme unique."""
    first = ban_row()
    second = ban_row() | {"x": "351999.5", "y": "6789999.5"}

    records = read_records(tmp_path / "ban.csv.gz", [first, second])

    assert records[0].identity_checksum == records[1].identity_checksum
    assert records[0].record_checksum != records[1].record_checksum


def test_divergent_address_label_breaks_the_identity(tmp_path: Path) -> None:
    """Cas absent du millésime observé, donc fabriqué : ce garde-fou n'a jamais été
    déclenché par des données réelles et doit rester couvert par un test."""
    first = ban_row()
    second = ban_row() | {"nom_voie": "Rue de l'Hiver"}

    records = read_records(tmp_path / "ban.csv.gz", [first, second])

    assert records[0].identity_checksum != records[1].identity_checksum


def test_divergent_parcel_relation_keeps_the_address_identity_intact(tmp_path: Path) -> None:
    first = ban_row()
    second = ban_row() | {"cad_parcelles": "35238000AB0009"}

    records = read_records(tmp_path / "ban.csv.gz", [first, second])

    assert records[0].identity_checksum == records[1].identity_checksum
    assert records[0].record_checksum != records[1].record_checksum


def test_exact_duplicate_shares_both_checksums(tmp_path: Path) -> None:
    records = read_records(tmp_path / "ban.csv.gz", [ban_row(), ban_row()])

    assert records[0].record_checksum == records[1].record_checksum
    assert records[0].identity_checksum == records[1].identity_checksum


def test_identity_checksum_ignores_every_quarantinable_attribute() -> None:
    """Un attribut ne peut pas être à la fois identitaire (divergence bloquante) et
    retirable (divergence tolérée) : les deux ensembles doivent rester disjoints."""
    source_columns = {
        "geometry_wkt": ("x", "y"),
        "cadastral_ids": ("cad_parcelles",),
        "position_type": ("type_position",),
        "source_position": ("source_position",),
        "municipality_certified": ("certification_commune",),
        "fantoir_id": ("id_fantoir",),
    }
    for column, _attribute, _reason in BAN_QUARANTINABLE_ATTRIBUTES:
        for source_field in source_columns[column]:
            assert source_field not in BAN_IDENTITY_FIELDS


def mixed_archive(path: Path) -> Path:
    """Archive contenant une fois chaque cas que le décompte doit savoir séparer."""
    rows = [
        ban_row(),
        ban_row(),  # doublon exact
        ban_row() | {"id": "35238_0001_00002"},
        ban_row() | {"id": "35238_0001_00002", "x": "351999.5"},  # position contradictoire
        ban_row() | {"id": "35238_0001_00003"},
        ban_row() | {"id": "35238_0001_00003", "nom_voie": "Rue de l'Hiver"},  # identité rompue
        ban_row() | {"id": "35238_0001_00004"},
        ban_row() | {"id": "35238_0001_00005"},
        ban_row() | {"id": "35238_0001_00006", "x": "not-a-number"},  # illisible
    ]
    write_ban_archive(path, rows)
    return path


def test_census_separates_rows_concerned_from_rows_in_excess(tmp_path: Path) -> None:
    """BUG-01 : le rapport confondait « lignes concernées » et « lignes en excès ».
    Les deux unités sont figées ici sur une archive où elles diffèrent."""
    census = census_ban_archive(mixed_archive(tmp_path / "ban.csv.gz"))

    assert census.source_rows == 9
    assert census.parse_quarantined_rows == 1
    assert census.identified_rows == 8
    assert census.identifiers == 5
    assert census.communes == 1

    # un identifiant conflictuel concerne deux lignes et n'en met qu'une en excès
    assert census.conflicting_identity_identifiers == 1
    assert census.conflicting_identity_rows == 2

    assert census.ambiguous_attribute_identifiers == 1
    assert census.ambiguous_attribute_rows == 2
    assert census.ambiguous_attribute_communes == 1

    assert census.exact_duplicate_identifiers == 1
    assert census.exact_duplicate_rows == 2
    assert census.exact_duplicate_excess_rows == 1
    assert census.attribute_collapse_excess_rows == 1
    assert census.deduplicated_excess_rows == 2


def test_census_predicts_import_counters_that_cannot_be_swapped(tmp_path: Path) -> None:
    """Les trois compteurs de `meta.import_run` sont figés à des valeurs distinctes :
    intervertir quarantaine et déduplication fait échouer le test."""
    census = census_ban_archive(mixed_archive(tmp_path / "ban.csv.gz"))

    assert census.expected_normalized_rows == 4
    assert census.expected_quarantined_rows == 3
    assert census.expected_deduplicated_rows == 2
    assert (
        census.expected_normalized_rows
        + census.expected_quarantined_rows
        + census.expected_deduplicated_rows
        == census.source_rows
    )


def test_census_refuses_counters_that_lose_source_rows() -> None:
    """L'invariant de conservation est un garde-fou exécuté, pas une phrase de rapport."""
    with pytest.raises(ValueError, match="does not conserve source rows"):
        BanCensus(
            source_rows=9,
            parse_quarantined_rows=1,
            identified_rows=7,  # une ligne lue mais rattachée à aucun identifiant
            identifiers=5,
            communes=1,
            conflicting_identity_identifiers=1,
            conflicting_identity_rows=2,
            ambiguous_attribute_identifiers=1,
            ambiguous_attribute_rows=2,
            ambiguous_attribute_communes=1,
            exact_duplicate_identifiers=1,
            exact_duplicate_rows=2,
            exact_duplicate_excess_rows=1,
        )
