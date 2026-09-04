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

# Champs qui constituent l'identité d'une adresse. Deux enregistrements partageant un
# identifiant BAN mais divergeant sur l'un de ces champs sont irréconciliables : l'un des
# deux est faux et rien ne permet de choisir. Une divergence portant sur un autre champ
# rend seulement cet attribut inutilisable, l'identité restant certaine.
BAN_IDENTITY_FIELDS = (
    "numero",
    "rep",
    "nom_voie",
    "code_postal",
    "code_insee",
    "nom_commune",
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
    identity_checksum: str


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


# Un identifiant de parcelle (IDU) compte 14 caracteres : commune INSEE (5), prefixe de
# section (3), section (2), numero (4). BAN publie une partie de ses `cad_parcelles` sur
# 15 caracteres, l'ordinal de commune etant complete a quatre chiffres : l'adresse
# `35001_0167` porte `350001000AE0125` la ou l'IDU cadastral est `35001000AE0125`.
# Compares tels quels, ces identifiants ne resolvent contre aucune parcelle : sur le 35,
# 158 866 relations declarees sur 325 934 disparaissaient ainsi. Retirer le zero de
# padding en fait resoudre 158 066, soit 99,5 % — un taux qu'une transformation fausse
# n'atteint pas contre le cadastre reel.
#
# Toute autre longueur est laissee intacte : elle doit rester visible en relation rejetee
# avec son motif, jamais devinee.
# Version de la transformation appliquee a une ligne BAN. Elle change des que la sortie
# change : @2 normalise l'ordinal de commune des `cad_parcelles`, ce que @1 ne faisait pas.
# La cle d'idempotence la porte, sans quoi un reimport apres changement de code rendrait
# l'ancien resultat en se croyant a jour.
BAN_TRANSFORMATION_VERSION = "ban-csv-normalize@2"

_BAN_PADDED_CADASTRAL_ID_LENGTH = 15
_CADASTRAL_ID_LENGTH = 14


def normalize_cadastral_id(value: str) -> str:
    """Ramener un `cad_parcelles` BAN a la forme canonique de l'IDU cadastral."""
    if len(value) == _BAN_PADDED_CADASTRAL_ID_LENGTH and value[2] == "0" and value[:2].isdigit():
        return value[:2] + value[3:]
    return value


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


def _identity_checksum(row: dict[str, str]) -> str:
    identity = {field: row.get(field, "").strip() for field in BAN_IDENTITY_FIELDS}
    return _checksum(identity)


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
                normalize_cadastral_id(identifier.strip())
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
                identity_checksum=_identity_checksum(row),
            )


# Deux unités cohabitent dans tout décompte BAN et leur confusion a déjà produit un rapport
# faux (BUG-01) : le nombre de **lignes concernées** par un cas et le nombre de **lignes en
# excès** qu'il produit. Un identifiant présent deux fois concerne deux lignes et n'en produit
# qu'une en excès. Les noms de ce module portent l'unité, jamais le cas seul.
@dataclass(frozen=True, slots=True)
class BanCensus:
    """Décompte d'une archive BAN, sans base de données et sans décision d'import.

    Les classes d'identifiants sont mesurées dans l'ordre où l'import les traite : les
    identités contradictoires partent en quarantaine avant que la déduplication ne voie
    quoi que ce soit, donc `exact_duplicate_*` ne porte que sur les identifiants conservés.
    """

    source_rows: int
    parse_quarantined_rows: int
    identified_rows: int
    identifiers: int
    communes: int
    conflicting_identity_identifiers: int
    conflicting_identity_rows: int
    ambiguous_attribute_identifiers: int
    ambiguous_attribute_rows: int
    ambiguous_attribute_communes: int
    exact_duplicate_identifiers: int
    exact_duplicate_rows: int
    exact_duplicate_excess_rows: int
    cadastral_reference_occurrences: int
    padded_cadastral_reference_occurrences: int
    malformed_cadastral_reference_occurrences: int

    def __post_init__(self) -> None:
        if (
            min(
                self.source_rows,
                self.parse_quarantined_rows,
                self.identified_rows,
                self.identifiers,
                self.communes,
                self.conflicting_identity_identifiers,
                self.ambiguous_attribute_identifiers,
                self.exact_duplicate_identifiers,
                self.cadastral_reference_occurrences,
                self.padded_cadastral_reference_occurrences,
                self.malformed_cadastral_reference_occurrences,
            )
            < 0
        ):
            raise ValueError("BAN census counters cannot be negative")
        for rows, identifiers, label in (
            (
                self.conflicting_identity_rows,
                self.conflicting_identity_identifiers,
                "conflicting identity",
            ),
            (
                self.ambiguous_attribute_rows,
                self.ambiguous_attribute_identifiers,
                "ambiguous attribute",
            ),
            (self.exact_duplicate_rows, self.exact_duplicate_identifiers, "exact duplicate"),
        ):
            if rows < identifiers:
                raise ValueError(f"BAN census reports fewer {label} rows than identifiers")
        if self.identified_rows < self.identifiers:
            raise ValueError("BAN census reports fewer identified rows than identifiers")
        if self.exact_duplicate_excess_rows > self.deduplicated_excess_rows:
            raise ValueError(
                "BAN census reports more exact duplicate rows than rows dropped by deduplication"
            )
        # `source_rows` est compté à la lecture, `identified_rows` est sommé identifiant par
        # identifiant : leur rapprochement est une vraie mesure de conservation, pas une
        # égalité vraie par construction.
        accounted = self.parse_quarantined_rows + self.identified_rows
        if accounted != self.source_rows:
            raise ValueError(
                f"BAN census does not conserve source rows: {accounted} accounted for, "
                f"{self.source_rows} read"
            )

    @property
    def retained_identifiers(self) -> int:
        """Identifiants qui survivent à la quarantaine d'identité."""
        return self.identifiers - self.conflicting_identity_identifiers

    @property
    def retained_rows(self) -> int:
        """Lignes qui atteignent la déduplication."""
        return self.identified_rows - self.conflicting_identity_rows

    @property
    def deduplicated_excess_rows(self) -> int:
        """Lignes en excès supprimées par la déduplication, toutes causes confondues."""
        return self.retained_rows - self.retained_identifiers

    @property
    def attribute_collapse_excess_rows(self) -> int:
        """Lignes devenues identiques après retrait d'un attribut contradictoire.

        Elles ne sont pas des doublons de la source : elles le deviennent parce que la
        divergence qui les distinguait a été retirée avec un motif.
        """
        return self.deduplicated_excess_rows - self.exact_duplicate_excess_rows

    @property
    def ambiguous_attribute_row_share(self) -> float:
        if not self.source_rows:
            return 0.0
        return self.ambiguous_attribute_rows / self.source_rows

    @property
    def expected_normalized_rows(self) -> int:
        return self.retained_identifiers

    @property
    def expected_quarantined_rows(self) -> int:
        return self.parse_quarantined_rows + self.conflicting_identity_rows

    @property
    def expected_deduplicated_rows(self) -> int:
        return self.deduplicated_excess_rows

    def summary(self) -> dict[str, int | float]:
        """Toutes les grandeurs citables, mesurées ou dérivées, sous leur nom publié."""
        return {
            "source_rows": self.source_rows,
            "parse_quarantined_rows": self.parse_quarantined_rows,
            "identified_rows": self.identified_rows,
            "identifiers": self.identifiers,
            "communes": self.communes,
            "conflicting_identity_identifiers": self.conflicting_identity_identifiers,
            "conflicting_identity_rows": self.conflicting_identity_rows,
            "ambiguous_attribute_identifiers": self.ambiguous_attribute_identifiers,
            "ambiguous_attribute_rows": self.ambiguous_attribute_rows,
            "ambiguous_attribute_communes": self.ambiguous_attribute_communes,
            "ambiguous_attribute_row_share": round(self.ambiguous_attribute_row_share, 5),
            "exact_duplicate_identifiers": self.exact_duplicate_identifiers,
            "exact_duplicate_rows": self.exact_duplicate_rows,
            "exact_duplicate_excess_rows": self.exact_duplicate_excess_rows,
            "attribute_collapse_excess_rows": self.attribute_collapse_excess_rows,
            "deduplicated_excess_rows": self.deduplicated_excess_rows,
            "expected_normalized_rows": self.expected_normalized_rows,
            "expected_quarantined_rows": self.expected_quarantined_rows,
            "expected_deduplicated_rows": self.expected_deduplicated_rows,
            "cadastral_reference_occurrences": self.cadastral_reference_occurrences,
            "padded_cadastral_reference_occurrences": (self.padded_cadastral_reference_occurrences),
            "malformed_cadastral_reference_occurrences": (
                self.malformed_cadastral_reference_occurrences
            ),
        }


@dataclass(slots=True)
class _IdentifierTally:
    commune_code: str
    identity_checksum: bytes
    record_checksums: set[bytes]
    rows: int = 1
    divergent_identity: bool = False


def census_ban_archive(path: Path) -> BanCensus:
    """Compte les lignes d'une archive BAN telles que l'import les classera.

    Aucune connexion n'est requise : c'est la commande qui rend les chiffres d'un rapport
    d'audit reproductibles depuis la seule archive checksumée.
    """
    tallies: dict[str, _IdentifierTally] = {}
    source_rows = 0
    parse_quarantined_rows = 0
    cadastral_reference_occurrences = 0
    padded_cadastral_reference_occurrences = 0
    malformed_cadastral_reference_occurrences = 0
    for record in iter_ban_records(path):
        source_rows += 1
        if isinstance(record, BanQuarantine):
            parse_quarantined_rows += 1
            continue
        raw_references = [
            item.strip()
            for item in record.properties.get("cad_parcelles", "").split("|")
            if item.strip()
        ]
        cadastral_reference_occurrences += len(raw_references)
        padded_cadastral_reference_occurrences += sum(
            1 for item in raw_references if normalize_cadastral_id(item) != item
        )
        malformed_cadastral_reference_occurrences += sum(
            1 for item in record.cadastral_ids if len(item) != _CADASTRAL_ID_LENGTH
        )
        record_checksum = bytes.fromhex(record.record_checksum)
        identity_checksum = bytes.fromhex(record.identity_checksum)
        tally = tallies.get(record.ban_id)
        if tally is None:
            # Seule la divergence d'identité importe (> 1 suffit), alors que le nombre exact
            # de variantes d'enregistrement sépare un doublon exact d'un attribut ambigu.
            tallies[record.ban_id] = _IdentifierTally(
                commune_code=record.commune_code,
                identity_checksum=identity_checksum,
                record_checksums={record_checksum},
            )
            continue
        tally.rows += 1
        tally.record_checksums.add(record_checksum)
        if identity_checksum != tally.identity_checksum:
            tally.divergent_identity = True

    identified_rows = 0
    communes: set[str] = set()
    ambiguous_communes: set[str] = set()
    conflicting_identity_identifiers = 0
    conflicting_identity_rows = 0
    ambiguous_attribute_identifiers = 0
    ambiguous_attribute_rows = 0
    exact_duplicate_identifiers = 0
    exact_duplicate_rows = 0
    exact_duplicate_excess_rows = 0
    for tally in tallies.values():
        identified_rows += tally.rows
        communes.add(tally.commune_code)
        if tally.divergent_identity:
            conflicting_identity_identifiers += 1
            conflicting_identity_rows += tally.rows
            continue
        if len(tally.record_checksums) > 1:
            ambiguous_attribute_identifiers += 1
            ambiguous_attribute_rows += tally.rows
            ambiguous_communes.add(tally.commune_code)
        excess = tally.rows - len(tally.record_checksums)
        if excess:
            exact_duplicate_identifiers += 1
            exact_duplicate_rows += tally.rows
            exact_duplicate_excess_rows += excess

    return BanCensus(
        source_rows=source_rows,
        parse_quarantined_rows=parse_quarantined_rows,
        identified_rows=identified_rows,
        identifiers=len(tallies),
        communes=len(communes),
        conflicting_identity_identifiers=conflicting_identity_identifiers,
        conflicting_identity_rows=conflicting_identity_rows,
        ambiguous_attribute_identifiers=ambiguous_attribute_identifiers,
        ambiguous_attribute_rows=ambiguous_attribute_rows,
        ambiguous_attribute_communes=len(ambiguous_communes),
        exact_duplicate_identifiers=exact_duplicate_identifiers,
        exact_duplicate_rows=exact_duplicate_rows,
        exact_duplicate_excess_rows=exact_duplicate_excess_rows,
        cadastral_reference_occurrences=cadastral_reference_occurrences,
        padded_cadastral_reference_occurrences=padded_cadastral_reference_occurrences,
        malformed_cadastral_reference_occurrences=malformed_cadastral_reference_occurrences,
    )
