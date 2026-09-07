"""Garde de reproductibilite des manifestes de release — regression de BUG-05.

DS-02@2026-08-01 epinglait un alias mouvant et ne nommait aucune archive : une base
fraiche n'avait plus aucun chemin vers les octets acceptes. Les tests ci-dessous verifient
que ce manifeste est desormais refuse, que ceux des sources reelles passent, et que la
resolution prefere l'archive a l'amont.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from immo_pipelines.cadastre.archive import ArchivedObjectMissingError
from immo_pipelines.cadastre.catalog import RawAssetRecord
from immo_pipelines.cadastre.manifest import (
    NonReproducibleManifestError,
    default_object_key,
    load_release_manifest,
    require_reproducible,
    resolve_asset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PINNED_SHA = "b" * 64


def write_manifest(directory: Path, data_source_id: str, release_key: str, asset: Any) -> Path:
    path = directory / "contracts" / "datasets" / data_source_id / "releases"
    path.mkdir(parents=True, exist_ok=True)
    document = {
        "release_id": f"{data_source_id}@{release_key}",
        "release_key": release_key,
        "source_published_on": release_key,
        "department": "35",
        "contract_version": 1,
        "assets": [asset],
    }
    target = path / f"{release_key}-35.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    return target


class FakeCatalog:
    """Substitut de `DatasetCatalog` : seules deux methodes sont sollicitees ici."""

    def __init__(self, archived: RawAssetRecord | None = None) -> None:
        self.archived = archived
        self.registered: list[Any] = []

    def find_raw_asset(self, **_: Any) -> RawAssetRecord | None:
        return self.archived

    def register_raw_asset(self, registration: Any) -> int:
        self.registered.append(registration)
        return 4242


class FakeStore:
    def __init__(self, payload: bytes = b"pinned-bytes") -> None:
        self.payload = payload
        self.fetched: list[str] = []
        self.stored: list[str] = []

    def get_file(self, object_key: str, destination: Path) -> None:
        self.fetched.append(object_key)
        destination.write_bytes(self.payload)

    def put_file(self, source: Path, object_key: str, metadata: Any) -> str:
        self.stored.append(object_key)
        return "etag"


def sha256_of(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def test_withdrawn_ds02_release_is_refused_before_any_download() -> None:
    """Le manifeste du 1er aout epinglait un alias sans archive : il doit etre refuse."""
    manifest = load_release_manifest("DS-02", "2026-08-01", "35", root=PROJECT_ROOT)
    asset = manifest.asset("buildings")

    with pytest.raises(NonReproducibleManifestError) as error:
        require_reproducible(manifest.release_id, asset)

    assert "carries no date" in str(error.value)
    assert "names no archived copy" in str(error.value)


def test_repinned_ds02_release_names_an_archived_copy() -> None:
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=PROJECT_ROOT)
    asset = manifest.asset("buildings")

    assert not asset.url_is_dated
    assert asset.archive_object_key is not None
    assert require_reproducible(manifest.release_id, asset) == asset.sha256


@pytest.mark.parametrize(
    ("data_source_id", "release_key", "layer"),
    [
        ("DS-01", "2026-06-01", "communes"),
        ("DS-01", "2026-06-01", "parcelles"),
        ("DS-01", "2026-06-01", "batiments"),
        ("DS-05", "2026-06-17", "addresses"),
        ("DS-04", "2026-06-15", "bdtopo"),
    ],
)
def test_real_release_manifests_are_reproducible(
    data_source_id: str, release_key: str, layer: str
) -> None:
    manifest = load_release_manifest(data_source_id, release_key, "35", root=PROJECT_ROOT)
    assert require_reproducible(manifest.release_id, manifest.asset(layer))


@pytest.mark.parametrize(
    ("url", "dated"),
    [
        # DS-01 et DS-05 : repertoire date au jour.
        ("https://example.test/2026-06-01/communes.json.gz", True),
        # DS-04 : edition datee dans le nom de fichier.
        ("https://example.test/BDTOPO_D035_2026-06-15/export.7z", True),
        # DS-03 : millesime annee-mois. Exiger le jour refusait cette source a tort.
        (
            "https://example.test/bdnb_millesime_2026-02-a/millesime_2026-02-a_dep35/x.zip",
            True,
        ),
        # DS-02 : alias mouvant, aucun marqueur de version.
        ("https://example.test/files/RNB_35.csv.zip", False),
        # Une annee seule ne vaut pas marqueur de version.
        ("https://example.test/2026/communes.json.gz", False),
    ],
)
def test_version_marker_detection(tmp_path: Path, url: str, dated: bool) -> None:
    write_manifest(
        tmp_path,
        "DS-01",
        "2026-06-01",
        {"layer": "communes", "url": url, "sha256": PINNED_SHA},
    )
    manifest = load_release_manifest("DS-01", "2026-06-01", "35", root=tmp_path)
    assert manifest.asset("communes").url_is_dated is dated


def test_missing_checksum_is_refused(tmp_path: Path) -> None:
    """`sha256: null` etait le cas de DS-01 : une URL datee ne suffit pas sans checksum."""
    write_manifest(
        tmp_path,
        "DS-01",
        "2026-06-01",
        {"layer": "communes", "url": "https://example.test/2026-06-01/communes.json.gz"},
    )
    manifest = load_release_manifest("DS-01", "2026-06-01", "35", root=tmp_path)

    with pytest.raises(NonReproducibleManifestError, match="no sha256"):
        require_reproducible(manifest.release_id, manifest.asset("communes"))


def test_dated_url_without_archive_is_accepted(tmp_path: Path) -> None:
    write_manifest(
        tmp_path,
        "DS-01",
        "2026-06-01",
        {
            "layer": "communes",
            "url": "https://example.test/2026-06-01/communes.json.gz",
            "sha256": PINNED_SHA,
        },
    )
    manifest = load_release_manifest("DS-01", "2026-06-01", "35", root=tmp_path)

    assert require_reproducible(manifest.release_id, manifest.asset("communes")) == PINNED_SHA


def test_uppercase_checksum_is_refused(tmp_path: Path) -> None:
    write_manifest(
        tmp_path,
        "DS-01",
        "2026-06-01",
        {
            "layer": "communes",
            "url": "https://example.test/2026-06-01/communes.json.gz",
            "sha256": PINNED_SHA.upper(),
        },
    )
    manifest = load_release_manifest("DS-01", "2026-06-01", "35", root=tmp_path)

    with pytest.raises(NonReproducibleManifestError, match="lowercase"):
        require_reproducible(manifest.release_id, manifest.asset("communes"))


def test_resolution_prefers_the_manifest_archive_over_upstream(tmp_path: Path) -> None:
    """Base fraiche, object store restaure : le cas que BUG-05 rendait impossible.

    Aucun appel reseau n'est possible dans ce test : si la resolution retombait sur
    l'amont, l'URL inexistante ferait echouer le test au lieu de le laisser passer.
    """
    payload = b"archived-rnb-bytes"
    checksum = sha256_of(payload)
    write_manifest(
        tmp_path,
        "DS-02",
        "2026-09-05",
        {
            "layer": "buildings",
            "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
            "sha256": checksum,
            "media_type": "text/csv",
            "content_encoding": "zip",
            "archive": {
                "object_key": f"DS-02/2026-09-05/department/35/buildings/{checksum}.csv.zip"
            },
        },
    )
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=tmp_path)
    asset = manifest.asset("buildings")
    catalog = FakeCatalog()
    store = FakeStore(payload)
    destination = tmp_path / "rnb.csv.zip"

    resolved = resolve_asset(
        catalog=catalog,  # pyright: ignore[reportArgumentType]
        object_store=store,
        manifest=manifest,
        asset=asset,
        destination=destination,
    )

    assert resolved.origin == "manifest_archive"
    assert resolved.sha256 == checksum
    assert store.fetched == [asset.archive_object_key]
    assert store.stored == []
    assert destination.read_bytes() == payload
    assert len(catalog.registered) == 1


def test_archived_bytes_that_do_not_match_the_pin_are_refused(tmp_path: Path) -> None:
    """Une archive corrompue ou substituee ne doit pas passer pour les octets acceptes."""
    write_manifest(
        tmp_path,
        "DS-02",
        "2026-09-05",
        {
            "layer": "buildings",
            "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
            "sha256": PINNED_SHA,
            "archive": {"object_key": "DS-02/2026-09-05/department/35/buildings/pinned.csv.zip"},
        },
    )
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=tmp_path)

    from immo_pipelines.cadastre.contract import ChecksumMismatchError

    with pytest.raises(ChecksumMismatchError):
        resolve_asset(
            catalog=FakeCatalog(),  # pyright: ignore[reportArgumentType]
            object_store=FakeStore(b"other-bytes"),
            manifest=manifest,
            asset=manifest.asset("buildings"),
            destination=tmp_path / "rnb.csv.zip",
        )


def test_database_archive_wins_over_the_manifest_archive(tmp_path: Path) -> None:
    payload = b"database-archived-bytes"
    checksum = sha256_of(payload)
    write_manifest(
        tmp_path,
        "DS-02",
        "2026-09-05",
        {
            "layer": "buildings",
            "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
            "sha256": PINNED_SHA,
            "archive": {"object_key": "manifest/key.csv.zip"},
        },
    )
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=tmp_path)
    catalog = FakeCatalog(
        RawAssetRecord(id=7, object_key="database/key.csv.zip", byte_size=1, sha256=checksum)
    )
    store = FakeStore(payload)

    resolved = resolve_asset(
        catalog=catalog,  # pyright: ignore[reportArgumentType]
        object_store=store,
        manifest=manifest,
        asset=manifest.asset("buildings"),
        destination=tmp_path / "rnb.csv.zip",
    )

    assert resolved.origin == "database_archive"
    assert resolved.raw_asset_id == 7
    assert store.fetched == ["database/key.csv.zip"]
    assert catalog.registered == []


def test_absent_manifest_archive_falls_through_to_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Au premier import, la cle nommee par le manifeste n'existe pas encore.

    Elle dit ou la copie *doit se trouver*, pas qu'elle y est deja : son absence doit faire
    passer a l'amont, qui archive alors sous cette cle exacte.
    """
    payload = b"freshly-downloaded-bytes"
    checksum = sha256_of(payload)
    object_key = f"DS-02/2026-09-05/department/35/buildings/{checksum}.csv.zip"
    write_manifest(
        tmp_path,
        "DS-02",
        "2026-09-05",
        {
            "layer": "buildings",
            "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
            "sha256": checksum,
            "archive": {"object_key": object_key},
        },
    )
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=tmp_path)

    class EmptyStore(FakeStore):
        def get_file(self, object_key: str, destination: Path) -> None:
            raise ArchivedObjectMissingError(object_key)

    def fake_download(
        url: str, destination: Path, expected: str | None = None, *, prefer_curl: bool = False
    ) -> str:
        destination.write_bytes(payload)
        return checksum

    monkeypatch.setattr("immo_pipelines.cadastre.manifest.download_asset", fake_download)
    store = EmptyStore()

    resolved = resolve_asset(
        catalog=FakeCatalog(),  # pyright: ignore[reportArgumentType]
        object_store=store,
        manifest=manifest,
        asset=manifest.asset("buildings"),
        destination=tmp_path / "rnb.csv.zip",
    )

    assert resolved.origin == "upstream"
    assert resolved.sha256 == checksum
    # Archive sous la cle du manifeste, pas sous une cle recalculee : sinon le manifeste
    # nommerait un objet qui n'existe pas et la recuperation echouerait au coup suivant.
    assert store.stored == [object_key]


def test_a_lost_database_archive_is_not_silently_replaced_by_upstream(tmp_path: Path) -> None:
    """La base affirme que l'archive existe : son absence est un probleme d'integrite."""
    write_manifest(
        tmp_path,
        "DS-02",
        "2026-09-05",
        {
            "layer": "buildings",
            "url": "https://rnb-opendata.invalid/files/RNB_35.csv.zip",
            "sha256": PINNED_SHA,
            "archive": {"object_key": "manifest/key.csv.zip"},
        },
    )
    manifest = load_release_manifest("DS-02", "2026-09-05", "35", root=tmp_path)

    class EmptyStore(FakeStore):
        def get_file(self, object_key: str, destination: Path) -> None:
            raise ArchivedObjectMissingError(object_key)

    with pytest.raises(ArchivedObjectMissingError):
        resolve_asset(
            catalog=FakeCatalog(  # pyright: ignore[reportArgumentType]
                RawAssetRecord(id=7, object_key="lost/key.csv.zip", byte_size=1, sha256=PINNED_SHA)
            ),
            object_store=EmptyStore(),
            manifest=manifest,
            asset=manifest.asset("buildings"),
            destination=tmp_path / "rnb.csv.zip",
        )


def test_default_object_key_keeps_the_layout_ds01_already_archived_under() -> None:
    """Changer le schema de cle orphelinerait les objets DS-01 deja deposes dans MinIO."""
    manifest = load_release_manifest("DS-01", "2026-06-01", "35", root=PROJECT_ROOT)
    asset = manifest.asset("communes")

    assert default_object_key(manifest, asset) == (
        f"DS-01/2026-06-01/department/35/communes/{asset.sha256}.json.gz"
    )
