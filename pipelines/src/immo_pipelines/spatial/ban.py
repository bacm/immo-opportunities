import csv
import gzip
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

BAN_REQUIRED_COLUMNS = frozenset(
    {
        "id",
        "numero",
        "nom_voie",
        "code_postal",
        "code_insee",
        "nom_commune",
        "x",
        "y",
    }
)


@dataclass(frozen=True, slots=True)
class BanRecord:
    source_row_number: int
    ban_id: str
    fantoir_id: str | None
    house_number: str
    repetition_index: str | None
    street_name: str
    postal_code: str
    commune_code: str
    commune_name: str
    display_label: str
    normalized_label: str
    position_type: str | None
    source_position: str | None
    municipality_certified: bool | None
    geometry_wkt: str
    cadastral_ids: tuple[str, ...]
    properties: dict[str, str]
    record_checksum: str


@dataclass(frozen=True, slots=True)
class BanQuarantine:
    source_row_number: int
    ban_id: str | None
    reason_code: str
    reason_detail: str
    source_properties: dict[str, str]


def normalize_address_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value).strip()


def _optional(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _certified(value: str) -> bool | None:
    if value == "1":
        return True
    if value == "0":
        return False
    return None


def _checksum(row: dict[str, str]) -> str:
    canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def iter_ban_records(path: Path) -> Iterator[BanRecord | BanQuarantine]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        columns = frozenset(reader.fieldnames or [])
        missing = BAN_REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"BAN CSV is missing columns: {sorted(missing)}")
        for row_number, raw in enumerate(reader, start=1):
            row = {str(key): str(value or "") for key, value in raw.items()}
            ban_id = row["id"].strip()
            try:
                if not ban_id:
                    raise ValueError("BAN id is empty")
                x = float(row["x"])
                y = float(row["y"])
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("BAN coordinates are not finite")
                commune_code = row["code_insee"].strip()
                if not re.fullmatch(r"[0-9A-Z]{5}", commune_code):
                    raise ValueError(f"Invalid commune code {commune_code!r}")
                number = row["numero"].strip()
                street = row["nom_voie"].strip()
                commune_name = row["nom_commune"].strip()
                if not number or not street or not commune_name:
                    raise ValueError("BAN address label fields are incomplete")
            except ValueError as exc:
                yield BanQuarantine(
                    source_row_number=row_number,
                    ban_id=ban_id or None,
                    reason_code="invalid_ban_record",
                    reason_detail=str(exc),
                    source_properties=row,
                )
                continue
            repetition = _optional(row.get("rep", ""))
            display_label = " ".join(
                item
                for item in (
                    number,
                    repetition,
                    street,
                    row["code_postal"].strip(),
                    commune_name,
                )
                if item
            )
            cadastral_ids = tuple(
                identifier.strip()
                for identifier in row.get("cad_parcelles", "").split("|")
                if identifier.strip()
            )
            yield BanRecord(
                source_row_number=row_number,
                ban_id=ban_id,
                fantoir_id=_optional(row.get("id_fantoir", "")),
                house_number=number,
                repetition_index=repetition,
                street_name=street,
                postal_code=row["code_postal"].strip(),
                commune_code=commune_code,
                commune_name=commune_name,
                display_label=display_label,
                normalized_label=normalize_address_label(display_label),
                position_type=_optional(row.get("type_position", "")),
                source_position=_optional(row.get("source_position", "")),
                municipality_certified=_certified(row.get("certification_commune", "")),
                geometry_wkt=f"POINT ({x} {y})",
                cadastral_ids=cadastral_ids,
                properties=row,
                record_checksum=_checksum(row),
            )
