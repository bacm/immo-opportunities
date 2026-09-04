import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class ContractError(ValueError):
    """The versioned dataset contract is invalid."""


class SchemaChangeError(ContractError):
    """A source feature no longer matches the declared contract."""


class ChecksumMismatchError(ContractError):
    """Downloaded bytes differ from the expected checksum."""


@dataclass(frozen=True)
class LayerContract:
    name: str
    target: str
    required_properties: dict[str, str]
    optional_properties: dict[str, str]
    additional_properties: str


@dataclass(frozen=True)
class DatasetContract:
    contract_id: str
    version: int
    source_srid: int
    canonical_srid: int
    normalization_version: str
    repair_version: str
    allowed_geometry_types: frozenset[str]
    layers: dict[str, LayerContract]
    raw: dict[str, Any]

    def layer(self, name: str) -> LayerContract:
        try:
            return self.layers[name]
        except KeyError as exc:
            raise ContractError(f"Layer {name!r} is not declared by {self.contract_id}") from exc

    def schema_fingerprint(self) -> str:
        payload = json.dumps(self.raw["layers"], sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_contract(path: Path | None = None) -> DatasetContract:
    contract_path = path or _project_root() / "contracts" / "datasets" / "DS-01" / "v1.json"
    raw_value = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(raw_value, dict):
        raise ContractError("Dataset contract root must be an object")
    raw = cast(dict[str, Any], raw_value)
    if raw.get("contract_id") != "DS-01" or raw.get("contract_version") != 1:
        raise ContractError("Expected DS-01 contract version 1")
    spatial = cast(dict[str, Any], raw["spatial"])
    raw_layers = cast(dict[str, dict[str, Any]], raw["layers"])
    layers = {
        name: LayerContract(
            name=name,
            target=str(value["target"]),
            required_properties=cast(dict[str, str], value["required_properties"]),
            optional_properties=cast(dict[str, str], value["optional_properties"]),
            additional_properties=str(value["additional_properties"]),
        )
        for name, value in raw_layers.items()
    }
    return DatasetContract(
        contract_id="DS-01",
        version=1,
        source_srid=int(spatial["source_srid"]),
        canonical_srid=int(spatial["canonical_srid"]),
        normalization_version=str(spatial["normalization"]),
        repair_version=str(spatial["repair"]),
        allowed_geometry_types=frozenset(cast(list[str], spatial["allowed_geometry_types"])),
        layers=layers,
        raw=raw,
    )


def sha256_file(path: Path, expected: str | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    actual = digest.hexdigest()
    if expected is not None and actual != expected:
        raise ChecksumMismatchError(f"Expected sha256 {expected}, got {actual}")
    return actual


def validate_properties(contract: LayerContract, properties: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for name, type_spec in contract.required_properties.items():
        if name not in properties:
            errors.append(f"missing required property {name}")
            continue
        if not _matches_type(properties[name], type_spec):
            errors.append(f"property {name} does not match {type_spec}")
    for name, type_spec in contract.optional_properties.items():
        if name in properties and not _matches_type(properties[name], type_spec):
            errors.append(f"property {name} does not match {type_spec}")
    if errors:
        raise SchemaChangeError("; ".join(errors))
    declared = set(contract.required_properties) | set(contract.optional_properties)
    return tuple(sorted(set(properties) - declared))


def _matches_type(value: Any, type_spec: str) -> bool:
    alternatives = type_spec.split("|")
    if value is None:
        return "null" in alternatives
    for kind in alternatives:
        if kind == "string" and isinstance(value, str):
            return True
        if kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if kind == "number" and isinstance(value, int | float) and not isinstance(value, bool):
            return True
        if kind == "boolean" and isinstance(value, bool):
            return True
        if kind == "object" and isinstance(value, dict):
            return True
    return False
