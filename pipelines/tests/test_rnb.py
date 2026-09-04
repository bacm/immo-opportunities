import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from immo_pipelines.cadastre.contract import SchemaChangeError
from immo_pipelines.spatial.rnb import RnbQuarantine, RnbRecord, iter_rnb_records

FIELDS = ["rnb_id", "point", "shape", "status", "ext_ids", "addresses", "plots", "validated_by"]


def write_rnb_archive(path: Path, rows: list[dict[str, str]], fields: list[str] = FIELDS) -> None:
    content = io.StringIO(newline="")
    writer = csv.DictWriter(content, fieldnames=fields, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("RNB_35.csv", content.getvalue())


def rnb_row(identifier: str, shape: str) -> dict[str, str]:
    return {
        "rnb_id": identifier,
        "point": "SRID=4326;POINT(-1.67 48.11)",
        "shape": shape,
        "status": "constructed",
        "ext_ids": json.dumps(
            [
                {"id": "bdnb-bc-A", "source": "bdnb", "source_version": "2023_01"},
                {"id": "BATIMENT-A", "source": "bdtopo", "source_version": "2023_09"},
            ]
        ),
        "addresses": json.dumps([{"cle_interop_ban": "35238_0001_00001", "street": "rue exemple"}]),
        "plots": json.dumps([{"id": "35238000AB0001", "bdg_cover_ratio": 0.95}]),
        "validated_by": "[]",
    }


def test_rnb_reader_preserves_all_source_ids_relations_and_polygon(tmp_path: Path) -> None:
    archive = tmp_path / "rnb.zip"
    write_rnb_archive(
        archive,
        [
            rnb_row(
                "RNB-A",
                "SRID=4326;POLYGON((-1.671 48.11,-1.67 48.11,"
                "-1.67 48.111,-1.671 48.111,-1.671 48.11))",
            )
        ],
    )

    records = list(iter_rnb_records(archive))

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, RnbRecord)
    assert record.geometry_type == "MultiPolygon"
    assert record.commune_code == "35238"
    assert {item["source"] for item in record.external_ids} == {"bdnb", "bdtopo"}
    assert record.plots[0]["id"] == "35238000AB0001"
    assert len(record.record_checksum) == 64


def test_rnb_point_creates_an_identity_without_inventing_a_polygon(tmp_path: Path) -> None:
    archive = tmp_path / "rnb.zip"
    write_rnb_archive(archive, [rnb_row("RNB-POINT", "SRID=4326;POINT(-1.67 48.11)")])

    record = next(iter_rnb_records(archive))

    assert isinstance(record, RnbRecord)
    assert record.geometry_type == "Point"


def test_invalid_rnb_geometry_is_quarantined(tmp_path: Path) -> None:
    archive = tmp_path / "rnb.zip"
    write_rnb_archive(archive, [rnb_row("RNB-BAD", "POINT(-1.67 48.11)")])

    record = next(iter_rnb_records(archive))

    assert isinstance(record, RnbQuarantine)
    assert record.reason_code == "invalid_rnb_record"


def test_rnb_schema_change_blocks_import(tmp_path: Path) -> None:
    archive = tmp_path / "rnb.zip"
    fields = [field for field in FIELDS if field != "plots"]
    row = rnb_row("RNB-A", "SRID=4326;POINT(-1.67 48.11)")
    row.pop("plots")
    write_rnb_archive(archive, [row], fields)

    with pytest.raises(SchemaChangeError, match="plots"):
        list(iter_rnb_records(archive))
