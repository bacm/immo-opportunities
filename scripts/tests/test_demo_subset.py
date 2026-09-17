"""Export du sous-ensemble démo : chaque table a une règle, et chaque règle est tenue — A6."""

import gzip
from pathlib import Path
from types import ModuleType


def tables(demo: ModuleType, *names: str) -> list:
    return [demo.Table(name, "id, commune_code", "t.id") for name in names]


def test_a_table_without_rule_stops_the_export(demo: ModuleType) -> None:
    """Une table ajoutée par une migration ne part jamais sur la démo par défaut."""
    rules = {"reference.parcel": demo.keep("true")}
    gaps = demo.check_rules(tables(demo, "reference.parcel", "app.new_secret"), rules)
    assert gaps == ["table sans règle : app.new_secret"]


def test_a_rule_without_table_stops_the_export(demo: ModuleType) -> None:
    rules = {"reference.parcel": demo.keep("true"), "reference.gone": demo.FULL}
    assert demo.check_rules(tables(demo, "reference.parcel"), rules) == [
        "règle sans table : reference.gone"
    ]


def test_personal_and_review_data_leave_only_their_schema(demo: ModuleType) -> None:
    schema_only = {name for name, rule in demo.RULES.items() if rule.mode == "schema"}
    assert {name for name in demo.RULES if name.startswith(("app.", "audit."))} <= schema_only
    assert "meta.matching_review_verdict" in schema_only
    assert "scoring.opportunity_snapshot" in schema_only


def test_catalog_lines_become_tables(demo: ModuleType) -> None:
    catalog = "meta.data_source|id, name|t.id\npublic.no_key|a, b|t::text\n"
    assert demo.parse_catalog(catalog) == [
        demo.Table("meta.data_source", "id, name", "t.id"),
        demo.Table("public.no_key", "a, b", "t::text"),
    ]


def test_the_script_copies_what_the_rules_say(demo: ModuleType) -> None:
    rules = {
        "app.app_user": demo.SCHEMA,
        "meta.data_source": demo.FULL,
        "reference.parcel": demo.keep(demo.COMMUNE),
        "observation.energy_assessment": demo.Rule(
            "filter", demo.COMMUNE, (("building_id", "k_building"),), require="building_id > ''"
        ),
    }
    script = demo.data_script(tables(demo, *sorted(rules)), ["35211", "35238"], rules)
    assert "\\set communes '35211,35238'" in script
    assert "REPEATABLE READ" in script
    assert "app.app_user" not in script
    assert (
        "COPY (SELECT id, commune_code FROM meta.data_source AS t WHERE true ORDER BY t.id)"
        in script
    )
    assert f"FROM reference.parcel AS t WHERE {demo.COMMUNE} ORDER BY t.id" in script
    # Parent absent : la référence devient nulle et le nombre en est publié.
    assert "UPDATE demo_observation_energy_assessment SET building_id = NULL" in script
    assert "'nullifiees|observation.energy_assessment.building_id|'" in script
    # Ce que la nullification rend invalide est écarté, et compté.
    assert "DELETE FROM demo_observation_energy_assessment WHERE NOT (building_id > '')" in script
    assert "'ecartees|observation.energy_assessment|'" in script
    assert "FROM demo_observation_energy_assessment AS t WHERE true" in script
    assert script.index("session_replication_role = replica") < script.index("COPY (SELECT")
    assert script.rstrip().endswith("COMMIT;")


def test_rows_are_counted_in_the_produced_file(demo: ModuleType, tmp_path: Path) -> None:
    dump = tmp_path / "immo-demo.sql.gz"
    with gzip.open(dump, "wb") as stream:
        stream.write(
            b"CREATE TABLE x ();\n\n"
            b"COPY meta.data_source (id, name) FROM stdin;\n"
            b"DS-01\tCadastre\nDS-02\tRNB\n\\.\n\n"
            b"COPY reference.parcel (id) FROM stdin;\n\\.\n"
            b"COPY app.fake (id) FROM stdin;\nCOPY x (y) FROM stdin;\n\\.\n"
        )
    assert demo.count_rows(dump) == {
        "meta.data_source": 2,
        "reference.parcel": 0,
        "app.fake": 1,
    }


def test_border_stats_keep_only_their_own_lines(demo: ModuleType) -> None:
    stats = (
        "nullifiees|observation.transaction_property.parcel_id|12\n"
        "NOTICE: x\n"
        "ajoutees|reference.building|8\n"
        "ecartees|meta.entity_match|3\n"
    )
    assert demo.parse_border(stats) == [
        {"kind": "nullifiees", "target": "observation.transaction_property.parcel_id", "count": 12},
        {"kind": "ajoutees", "target": "reference.building", "count": 8},
        {"kind": "ecartees", "target": "meta.entity_match", "count": 3},
    ]


def test_default_communes_are_the_five_strata(demo: ModuleType) -> None:
    assert demo.DEFAULT_COMMUNES == ("35238", "35288", "35047", "35360", "35211")
