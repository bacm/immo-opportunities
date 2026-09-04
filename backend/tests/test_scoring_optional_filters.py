from pathlib import Path


def test_list_opportunities_casts_optional_bind_parameters() -> None:
    """Null optional filters must be typed for psycopg/PostgreSQL."""
    source = (
        Path(__file__).parents[1] / "src" / "immo" / "scoring.py"
    ).read_text(encoding="utf-8")
    start = source.index("def list_opportunities")
    end = source.index("\ndef find_opportunity")
    body = source[start:end]
    for fragment in (
        "CAST(:strategy AS text)",
        "CAST(:minimum_score AS double precision)",
        "CAST(:confidence_level AS text)",
        "CAST(:department_code AS text)",
        "CAST(:cursor_id AS text)",
        "CAST(:cursor_score AS double precision)",
    ):
        assert fragment in body, fragment
