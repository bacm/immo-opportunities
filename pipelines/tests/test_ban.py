import csv
import gzip
from pathlib import Path

from immo_pipelines.spatial.ban import (
    BAN_REQUIRED_COLUMNS,
    BanQuarantine,
    BanRecord,
    iter_ban_records,
    normalize_address_label,
)


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
