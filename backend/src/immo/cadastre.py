import json
from typing import Any, TypedDict

from sqlalchemy import text

from immo.database import get_engine


class ParcelProvenance(TypedDict):
    data_source_id: str
    release_id: str
    release_key: str
    source_published_on: str | None
    raw_asset_id: int
    layer: str
    source_url: str
    object_key: str
    sha256: str
    source_row_number: int
    record_checksum: str
    transformation_version: str
    was_repaired: bool
    repair_method: str | None


class CadastralParcelRecord(TypedDict):
    cadastral_id: str
    department_code: str
    commune_code: str
    prefix: str
    section: str
    number: str
    stated_area_m2: int | None
    geometry: dict[str, Any]
    provenance: ParcelProvenance


def find_active_parcel(cadastral_id: str) -> CadastralParcelRecord | None:
    statement = text(
        """
        SELECT parcel.cadastral_id,
               parcel.department_code,
               parcel.commune_code,
               parcel.prefix,
               parcel.section,
               parcel.number,
               parcel.stated_area_m2,
               ST_AsGeoJSON(ST_Transform(parcel.geom, 4326)) AS geometry,
               release.data_source_id,
               release.id AS release_id,
               release.release_key,
               release.source_published_on,
               asset.id AS raw_asset_id,
               asset.layer,
               asset.source_url,
               asset.object_key,
               asset.sha256,
               parcel.source_row_number,
               parcel.record_checksum,
               parcel.transformation_version,
               parcel.was_repaired,
               parcel.repair_method
          FROM reference.active_cadastral_parcel AS parcel
          JOIN meta.dataset_release AS release ON release.id = parcel.release_id
          JOIN meta.raw_asset AS asset ON asset.id = parcel.raw_asset_id
         WHERE parcel.cadastral_id = :cadastral_id
        """
    )
    with get_engine().connect() as connection:
        row = connection.execute(statement, {"cadastral_id": cadastral_id}).mappings().one_or_none()
    if row is None:
        return None
    return {
        "cadastral_id": str(row["cadastral_id"]),
        "department_code": str(row["department_code"]),
        "commune_code": str(row["commune_code"]),
        "prefix": str(row["prefix"]),
        "section": str(row["section"]),
        "number": str(row["number"]),
        "stated_area_m2": row["stated_area_m2"],
        "geometry": json.loads(str(row["geometry"])),
        "provenance": {
            "data_source_id": str(row["data_source_id"]),
            "release_id": str(row["release_id"]),
            "release_key": str(row["release_key"]),
            "source_published_on": (
                row["source_published_on"].isoformat() if row["source_published_on"] else None
            ),
            "raw_asset_id": int(row["raw_asset_id"]),
            "layer": str(row["layer"]),
            "source_url": str(row["source_url"]),
            "object_key": str(row["object_key"]),
            "sha256": str(row["sha256"]),
            "source_row_number": int(row["source_row_number"]),
            "record_checksum": str(row["record_checksum"]),
            "transformation_version": str(row["transformation_version"]),
            "was_repaired": bool(row["was_repaired"]),
            "repair_method": row["repair_method"],
        },
    }
