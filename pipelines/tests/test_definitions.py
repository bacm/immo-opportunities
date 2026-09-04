import json
from datetime import UTC, date, datetime
from decimal import Decimal

from dagster import AssetKey, materialize

from immo_pipelines.assets import cadastre_department_release, foundation_diagnostic
from immo_pipelines.assets.cadastre import _json_compatible, cadastre_department_partitions
from immo_pipelines.definitions import defs
from immo_pipelines.pilot import BRITTANY_DEPARTMENTS


def test_definitions_include_foundation_diagnostic() -> None:
    assert defs.assets is not None
    assert AssetKey("foundation_diagnostic") in foundation_diagnostic.keys
    assert AssetKey("cadastre_department_release") in cadastre_department_release.keys
    assert tuple(cadastre_department_partitions.get_partition_keys()) == BRITTANY_DEPARTMENTS


def test_foundation_diagnostic_materializes() -> None:
    result = materialize([foundation_diagnostic])

    assert result.success


def test_cadastre_metadata_converts_postgres_values_to_json() -> None:
    value = {
        "published_on": date(2026, 6, 1),
        "checked_at": datetime(2026, 8, 4, 14, 0, tzinfo=UTC),
        "whole_count": Decimal("865418"),
        "ratio": Decimal("0.125"),
    }

    converted = _json_compatible(value)

    assert json.loads(json.dumps(converted)) == {
        "published_on": "2026-06-01",
        "checked_at": "2026-08-04T14:00:00+00:00",
        "whole_count": 865418,
        "ratio": 0.125,
    }
