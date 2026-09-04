from pathlib import Path


def migration_source() -> str:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260805_0008_real_map.py"
    return path.read_text(encoding="utf-8")


def test_mvt_functions_are_versioned_and_use_render_geometries() -> None:
    source = migration_source()

    assert "tiles.parcel_render_v1" in source
    assert "tiles.building_render_v1" in source
    assert "ST_AsMVTGeom" in source
    assert "ST_AsMVT(tile, 'parcels'" in source
    assert "ST_AsMVT(tile, 'buildings'" in source
    assert "z BETWEEN 13 AND 22" in source
    assert "z BETWEEN 15 AND 22" in source


def test_martin_can_only_execute_explicit_mvt_functions() -> None:
    source = migration_source()

    assert "SECURITY DEFINER" in source
    assert "REVOKE ALL ON FUNCTION tiles." in source
    assert "GRANT EXECUTE ON FUNCTION tiles.{function} TO tiles_ro" in source
    assert "GRANT EXECUTE ON FUNCTION tiles.refresh_render_v1(text) TO pipeline_rw" in source


def test_martin_auto_publication_is_disabled_for_render_tables() -> None:
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260805_0009_martin_function_only.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "REVOKE SELECT ON TABLES FROM tiles_ro" in source
    assert "tiles.parcel_render_v1" in source
    assert "tiles.cadastral_parcels" in source


def test_mvt_functions_filter_on_an_indexed_geometry_without_case_expression() -> None:
    path = (
        Path(__file__).parents[1] / "migrations" / "versions" / "20260805_0010_mvt_gist_filter.py"
    )
    source = path.read_text(encoding="utf-8")

    assert source.count("source.geom && ST_TileEnvelope(z, x, y)") == 2
    assert "CASE WHEN z < 16 THEN source.geom_generalized" in source
