"""RNB, BAN, BDNB et BD TOPO dans le graphe d'assets — BUG-02, BUG-19.

La fonction commune est exercée sur un manifeste de fixture, avec un catalogue, un stockage et un
importeur substitués : aucune base ni aucun réseau.
"""

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, ClassVar

import pytest
from dagster import AssetKey, DagsterInstance, MultiPartitionKey, materialize

from immo_pipelines.assets import (
    ds02_rnb_release,
    ds03_bdnb_release,
    ds04_bdtopo_release,
    ds05_ban_release,
    spatial_sources,
)
from immo_pipelines.cadastre.catalog import RawAssetRecord
from immo_pipelines.cadastre.contract import ChecksumMismatchError
from immo_pipelines.definitions import defs
from immo_pipelines.spatial import release_import
from immo_pipelines.spatial.importer import SpatialImportOutcome
from immo_pipelines.spatial.release_import import (
    BAN,
    BDNB,
    BDTOPO,
    RNB,
    DepartmentReleaseImport,
    SourceImport,
    import_department_release,
)

PAYLOAD = b"rnb-pinned-bytes"
CHECKSUM = hashlib.sha256(PAYLOAD).hexdigest()
OBJECT_KEY = f"DS-02/2026-09-05/department/35/buildings/{CHECKSUM}.csv.zip"


def fixture_root(root: Path) -> Path:
    releases = root / "contracts" / "datasets" / "DS-02" / "releases"
    releases.mkdir(parents=True)
    (root / "contracts" / "datasets" / "DS-02" / "v1.json").write_text("{}", encoding="utf-8")
    manifest = {
        "release_id": "DS-02@2026-09-05",
        "release_key": "2026-09-05",
        "source_published_on": "2026-09-05",
        "department": "35",
        "contract_version": 1,
        "assets": [
            {
                "layer": "buildings",
                "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
                "sha256": CHECKSUM,
                "archive": {"object_key": OBJECT_KEY},
            }
        ],
    }
    (releases / "2026-09-05-35.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


class FakeCatalog:
    """Le catalogue en mémoire : une archive enregistrée est retrouvée à l'appel suivant."""

    archived: RawAssetRecord | None = None
    releases: ClassVar[list[str]] = []
    raw_assets: ClassVar[list[Any]] = []

    def __init__(self, connection: Any) -> None:
        del connection

    def register_release(self, **kwargs: Any) -> None:
        FakeCatalog.releases.append(kwargs["release_id"])

    def find_raw_asset(self, **_: Any) -> RawAssetRecord | None:
        return FakeCatalog.archived

    def register_raw_asset(self, registration: Any) -> int:
        FakeCatalog.raw_assets.append(registration)
        FakeCatalog.archived = RawAssetRecord(
            id=4242, object_key=OBJECT_KEY, byte_size=len(PAYLOAD), sha256=CHECKSUM
        )
        return 4242


class FakeStore:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.fetched: list[str] = []

    def get_file(self, object_key: str, destination: Path) -> None:
        self.fetched.append(object_key)
        destination.write_bytes(self.payload)

    def put_file(self, source: Path, object_key: str, metadata: Any) -> str:
        raise AssertionError("aucun archivage attendu")


class FakeImporter:
    calls: ClassVar[list[dict[str, Any]]] = []
    refreshed: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, connection: Any) -> None:
        del connection

    def import_archive(self, **kwargs: Any) -> SpatialImportOutcome:
        FakeImporter.calls.append(
            {key: value for key, value in kwargs.items() if key != "source_path"}
        )
        assert kwargs["source_path"].read_bytes() == PAYLOAD
        return SpatialImportOutcome(kwargs["import_run_id"], 3, 2, 1, len(FakeImporter.calls) > 1)

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None:
        FakeImporter.refreshed.append((release_id, department_code))


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> SourceImport:
    FakeCatalog.archived = None
    FakeCatalog.releases = []
    FakeCatalog.raw_assets = []
    FakeImporter.calls = []
    FakeImporter.refreshed = []
    monkeypatch.setattr(release_import, "DatasetCatalog", FakeCatalog)

    def no_download(*_: Any, **__: Any) -> str:
        raise AssertionError("aucun téléchargement attendu")

    monkeypatch.setattr("immo_pipelines.cadastre.manifest.download_asset", no_download)
    return SourceImport(
        data_source_id=RNB.data_source_id,
        layer=RNB.layer,
        source_srid=RNB.source_srid,
        run_prefix=RNB.run_prefix,
        transformation_version=RNB.transformation_version,
        local_name=RNB.local_name,
        importer=FakeImporter,
    )


def test_une_rematerialisation_ne_retelecharge_rien_et_garde_ses_cles(
    tmp_path: Path, fakes: SourceImport
) -> None:
    root = fixture_root(tmp_path)
    store = FakeStore(PAYLOAD)
    first = import_department_release(
        fakes,
        "2026-09-05",
        "35",
        connection=object(),
        object_store=store,
        root=root,  # type: ignore[arg-type]
    )
    second = import_department_release(
        fakes,
        "2026-09-05",
        "35",
        connection=object(),
        object_store=store,
        root=root,  # type: ignore[arg-type]
    )
    assert (first.asset_origin, second.asset_origin) == ("manifest_archive", "database_archive")
    assert len(FakeCatalog.raw_assets) == 1
    assert FakeImporter.calls[0] == FakeImporter.calls[1]
    assert FakeImporter.calls[0]["import_run_id"] == "rnb:2026-09-05:35:2"
    assert FakeImporter.calls[0]["idempotency_key"] == (
        f"DS-02@2026-09-05:35:buildings:{CHECKSUM}:2"
    )
    assert second.outcome.skipped_as_idempotent
    assert FakeImporter.refreshed == [("DS-02@2026-09-05", "35")] * 2


def test_un_checksum_divergent_arrete_avant_tout_import(
    tmp_path: Path, fakes: SourceImport
) -> None:
    root = fixture_root(tmp_path)
    with pytest.raises(ChecksumMismatchError):
        import_department_release(
            fakes,
            "2026-09-05",
            "35",
            connection=object(),  # type: ignore[arg-type]
            object_store=FakeStore(b"autres-octets"),
            root=root,
        )
    assert FakeCatalog.raw_assets == []
    assert FakeImporter.calls == []
    assert FakeImporter.refreshed == []


def test_les_cles_sont_celles_des_scripts_d_avant() -> None:
    """Changer une clé ferait réimporter des releases déjà en base."""
    assert (RNB.run_prefix, RNB.layer, RNB.transformation_version, RNB.source_srid) == (
        "rnb",
        "buildings",
        "2",
        4326,
    )
    assert (BAN.run_prefix, BAN.layer, BAN.source_srid, BAN.prefer_curl) == (
        "ban",
        "addresses",
        2154,
        True,
    )


def test_bdnb_et_bdtopo_gardent_leurs_cles_et_extraient_leur_membre() -> None:
    assert (BDNB.run_prefix, BDNB.layer, BDNB.source_srid) == ("bdnb", "bdnb", 2154)
    assert (BDTOPO.run_prefix, BDTOPO.layer, BDTOPO.source_srid) == ("bdtopo", "bdtopo", 2154)
    assert BDNB.extract is not None and BDNB.extract.__name__ == "extract_zip_member"
    assert BDTOPO.extract is not None and BDTOPO.extract.__name__ == "extract_seven_zip_member"


def test_le_membre_extrait_est_importe_et_l_archive_supprimee(
    tmp_path: Path, fakes: SourceImport, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture_root(tmp_path)
    manifest = root / "contracts" / "datasets" / "DS-02" / "releases" / "2026-09-05-35.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["assets"][0]["member_path"] = "data/membre.gpkg"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    seen: dict[str, Any] = {}

    def extract(archive: Path, member: str, directory: Path) -> Path:
        seen["archive"] = archive
        seen["member"] = member
        target = directory / "membre.gpkg"
        target.write_bytes(PAYLOAD)
        return target

    class Importer(FakeImporter):
        def import_archive(self, **kwargs: Any) -> SpatialImportOutcome:
            seen["source_path"] = kwargs["source_path"]
            seen["archive_left"] = seen["archive"].exists()
            return super().import_archive(**kwargs)

    source = dataclasses.replace(fakes, importer=Importer, extract=extract)
    import_department_release(
        source,
        "2026-09-05",
        "35",
        connection=object(),
        object_store=FakeStore(PAYLOAD),
        root=root,  # type: ignore[arg-type]
    )
    assert seen["member"] == "data/membre.gpkg"
    assert seen["source_path"].name == "membre.gpkg"
    assert seen["archive_left"] is False


def test_les_assets_sont_dans_les_definitions_et_partitionnes_par_departement() -> None:
    assert defs.assets is not None
    keys = {key for definition in defs.assets for key in definition.keys}  # type: ignore[union-attr]
    # invariant-ok: assertion-supprimee — étendue à BDNB et BD TOPO (BUG-19).
    assert {
        AssetKey("ds02_rnb_release"),
        AssetKey("ds03_bdnb_release"),
        AssetKey("ds04_bdtopo_release"),
        AssetKey("ds05_ban_release"),
    } <= keys
    for definition in (ds02_rnb_release, ds03_bdnb_release, ds04_bdtopo_release, ds05_ban_release):
        partitions = definition.partitions_def
        assert partitions is not None
        dimensions = {d.name: d.partitions_def for d in partitions.partitions_defs}  # type: ignore[attr-defined]
        assert tuple(dimensions["department"].get_partition_keys()) == ("22", "29", "35", "56")


def test_l_asset_materialise_sa_partition(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str, str]] = []

    def fake_import(source: SourceImport, release: str, department: str, **_: Any) -> Any:
        seen.append((source.data_source_id, release, department))
        return DepartmentReleaseImport(
            f"DS-02@{release}",
            department,
            "database_archive",
            CHECKSUM,
            SpatialImportOutcome("rnb:2026-09-05:35:2", 3, 2, 1, True),
        )

    class Settings:
        minio_endpoint = minio_access_key = minio_secret_key = "x"
        database_host = database_name = database_user = database_password = "x"
        database_port = 5432

    class Connection:
        def __enter__(self) -> "Connection":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

    monkeypatch.setattr(spatial_sources, "import_department_release", fake_import)
    monkeypatch.setattr(spatial_sources.CadastreSettings, "from_environment", lambda: Settings())
    monkeypatch.setattr(spatial_sources, "MinioObjectStore", lambda *_: object())
    monkeypatch.setattr(spatial_sources.psycopg, "connect", lambda **_: Connection())

    instance = DagsterInstance.ephemeral()
    instance.add_dynamic_partitions("rnb_releases", ["2026-09-05"])
    result = materialize(
        [ds02_rnb_release],
        instance=instance,
        partition_key=MultiPartitionKey({"department": "35", "release": "2026-09-05"}),
    )
    assert result.success
    assert seen == [("DS-02", "2026-09-05", "35")]
    materialization = result.asset_materializations_for_node("ds02_rnb_release")[0]
    assert materialization.metadata["import_run_id"].value == "rnb:2026-09-05:35:2"
