import re
from pathlib import Path


def test_entity_match_upserts_do_not_reference_updated_at() -> None:
    """meta.entity_match is append/supersede style: created_at only, no updated_at."""
    source = (
        Path(__file__).parents[1] / "src" / "immo_pipelines" / "spatial" / "importer.py"
    ).read_text(encoding="utf-8")
    blocks = re.findall(
        r"INSERT INTO meta\.entity_match \([\s\S]*?"
        r"ON CONFLICT \([\s\S]*?\) DO (?:NOTHING|UPDATE SET[\s\S]*?)(?=\n            \"\"\")",
        source,
    )
    assert blocks, "expected entity_match inserts in spatial importer"
    updates = [block for block in blocks if "DO UPDATE SET" in block]
    assert updates, "expected at least one entity_match upsert"
    for block in updates:
        assert "updated_at" not in block, block
