"""Manifestes de release : chargement, garde de reproductibilite, resolution de l'asset.

Un manifeste doit permettre de *retrouver* les octets acceptes, pas seulement de les
redemander a l'amont. Trois sources ont montre que l'URL seule n'y suffit pas :

- DS-02 RNB publie un objet unique par departement, ecrase a chaque mise a jour, sans
  objet date ni versionnement S3. L'URL est un alias par construction.
- DS-01 et DS-05 publient des repertoires dates : l'URL y designe des octets stables.
- DS-04 publie une edition datee par le flux Atom du Geoplateforme.

D'ou la regle portee par ce module : un asset n'est importable de facon reproductible que
s'il porte un SHA-256 **et** qu'au moins un chemin de recuperation existe — une URL datee,
ou une copie archivee nommee dans le manifeste. Le checksum reste la seule contrainte
reelle ; l'URL datee n'est qu'une presomption d'immuabilite, et c'est le SHA-256 qui
tranche apres telechargement. La garde sert a refuser tot, avec un motif lisible, ce qui
echouerait de toute facon apres plusieurs centaines de megaoctets.

Voir BUG-05 : DS-02@2026-08-01 epinglait un alias, l'archive immuable n'etait nommee que
dans la base, et une base fraiche n'avait donc aucun chemin de retour.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from immo_pipelines.cadastre.archive import (
    ArchivedObjectMissingError,
    archive_asset,
    download_asset,
)
from immo_pipelines.cadastre.catalog import DatasetCatalog, RawAssetRegistration
from immo_pipelines.cadastre.contract import sha256_file

# Un marqueur de version date dans le chemin : date ISO, date compacte, ou millesime
# annee-mois. Ce dernier couvre la BDNB, dont l'URL porte `2026-02-a` : un millesime est un
# marqueur de version aussi valable qu'une date pleine, et l'exiger au jour pres refusait une
# source pourtant correctement epinglee.
#
# Presomption d'immuabilite, jamais une preuve : seul le SHA-256 contraint les octets. Une
# annee seule serait trop faible pour valoir marqueur, d'ou le mois obligatoire.
_DATED_PATH = re.compile(r"(?<!\d)(\d{4}-\d{2}(-\d{2})?|\d{8})(?!\d)")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class NonReproducibleManifestError(RuntimeError):
    """Le manifeste ne permet pas de retrouver les octets acceptes."""


class AssetStore(Protocol):
    def put_file(self, source: Path, object_key: str, metadata: Mapping[str, str]) -> str: ...

    def get_file(self, object_key: str, destination: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class ManifestAsset:
    layer: str
    url: str
    sha256: str | None
    byte_size: int | None
    media_type: str
    content_encoding: str | None
    archive_object_key: str | None
    member_path: str | None

    @property
    def url_is_dated(self) -> bool:
        return _DATED_PATH.search(self.url) is not None


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    data_source_id: str
    release_id: str
    release_key: str
    source_published_on: str
    department: str
    contract_version: int
    assets: tuple[ManifestAsset, ...]

    def asset(self, layer: str) -> ManifestAsset:
        for candidate in self.assets:
            if candidate.layer == layer:
                return candidate
        raise KeyError(f"{self.release_id} has no asset for layer {layer}")


@dataclass(frozen=True, slots=True)
class ResolvedAsset:
    raw_asset_id: int
    sha256: str
    # D'ou viennent reellement les octets : la preuve d'import doit le dire, sans quoi
    # « import reussi » ne distingue pas un amont encore disponible d'une archive locale.
    origin: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _asset_from_manifest(value: dict[str, Any]) -> ManifestAsset:
    checksum = value.get("sha256")
    size = value.get("byte_size")
    archive = cast(dict[str, Any], value.get("archive") or {})
    return ManifestAsset(
        layer=str(value["layer"]),
        url=str(value["url"]),
        sha256=str(checksum) if checksum is not None else None,
        byte_size=int(cast(int, size)) if size is not None else None,
        media_type=str(value.get("media_type") or "application/octet-stream"),
        content_encoding=(
            str(value["content_encoding"]) if value.get("content_encoding") is not None else None
        ),
        archive_object_key=(
            str(archive["object_key"]) if archive.get("object_key") is not None else None
        ),
        member_path=str(value["member_path"]) if value.get("member_path") is not None else None,
    )


def load_release_manifest(
    data_source_id: str,
    release_key: str,
    department: str,
    *,
    root: Path | None = None,
) -> ReleaseManifest:
    path = (
        (root or project_root())
        / "contracts"
        / "datasets"
        / data_source_id
        / "releases"
        / f"{release_key}-{department}.json"
    )
    document = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    assets = tuple(
        _asset_from_manifest(entry) for entry in cast(list[dict[str, Any]], document["assets"])
    )
    return ReleaseManifest(
        data_source_id=data_source_id,
        release_id=str(document["release_id"]),
        release_key=str(document["release_key"]),
        source_published_on=str(document["source_published_on"]),
        department=str(document["department"]),
        contract_version=int(cast(int, document["contract_version"])),
        assets=assets,
    )


def require_reproducible(release_id: str, asset: ManifestAsset) -> str:
    """Refuser avant tout telechargement un asset qu'on ne saurait pas retrouver."""
    if asset.sha256 is None:
        raise NonReproducibleManifestError(
            f"{release_id} layer {asset.layer}: no sha256 in the manifest. An unpinned asset"
            " cannot be accepted; fill the checksum from archived bytes before importing."
        )
    if not _SHA256.match(asset.sha256):
        raise NonReproducibleManifestError(
            f"{release_id} layer {asset.layer}: sha256 {asset.sha256!r} is not a lowercase"
            " 64-character hex digest."
        )
    if not asset.url_is_dated and asset.archive_object_key is None:
        raise NonReproducibleManifestError(
            f"{release_id} layer {asset.layer}: {asset.url} carries no date and the manifest"
            " names no archived copy. The producer may overwrite it at any time, leaving no"
            " path back to the accepted bytes — see BUG-05."
        )
    return asset.sha256


def resolve_asset(
    *,
    catalog: DatasetCatalog,
    object_store: AssetStore,
    manifest: ReleaseManifest,
    asset: ManifestAsset,
    destination: Path,
    prefer_curl: bool = False,
) -> ResolvedAsset:
    """Deposer les octets epingles dans `destination`, par le premier chemin disponible.

    Ordre : archive deja enregistree en base, puis copie archivee nommee par le manifeste,
    puis amont. L'amont vient en dernier parce que c'est le seul chemin qui peut avoir
    change sous nos pieds.
    """
    expected_sha = require_reproducible(manifest.release_id, asset)

    archived = catalog.find_raw_asset(
        release_id=manifest.release_id,
        layer=asset.layer,
        territory_code=manifest.department,
        source_url=asset.url,
    )
    if archived is not None:
        # La base affirme que l'archive existe. Son absence est une atteinte a l'integrite
        # de la plateforme, pas un cas normal : la laisser remonter.
        object_store.get_file(archived.object_key, destination)
        sha256_file(destination, archived.sha256)
        return ResolvedAsset(archived.id, archived.sha256, "database_archive")

    if asset.archive_object_key is not None:
        # Base fraiche mais object store restaure : c'est precisement le cas que BUG-05
        # rendait impossible, l'archive n'etant nommee que dans la base perdue.
        #
        # La cle nommee par le manifeste dit ou la copie *doit se trouver*, ce qui n'est pas
        # la meme chose que d'affirmer qu'elle y est deja : au premier import, rien n'a
        # encore ete archive. Son absence fait donc passer a l'amont, qui archivera sous
        # cette cle exacte.
        try:
            object_store.get_file(asset.archive_object_key, destination)
        except ArchivedObjectMissingError:
            pass
        else:
            sha256_file(destination, expected_sha)
            return ResolvedAsset(
                _register(catalog, manifest, asset, destination, expected_sha, etag=None),
                expected_sha,
                "manifest_archive",
            )

    actual_sha = download_asset(asset.url, destination, expected_sha, prefer_curl=prefer_curl)
    object_key = asset.archive_object_key or default_object_key(manifest, asset)
    etag = archive_asset(
        object_store,
        destination,
        object_key=object_key,
        sha256=actual_sha,
        source_url=asset.url,
        release_id=manifest.release_id,
        content_type=asset.media_type,
    )
    return ResolvedAsset(
        _register(catalog, manifest, asset, destination, actual_sha, etag=etag),
        actual_sha,
        "upstream",
    )


def _archive_suffix(url: str) -> str:
    """Conserver l'extension composee de la source (`.json.gz`, `.csv.zip`).

    Le schema doit rester celui sous lequel DS-01 a deja archive ses trois couches, sinon
    les objets deja deposes ne correspondent plus a la cle calculee.
    """
    name = url.rsplit("/", 1)[-1].split("?", 1)[0]
    return "".join(Path(name).suffixes[-2:])


def default_object_key(manifest: ReleaseManifest, asset: ManifestAsset) -> str:
    return (
        f"{manifest.data_source_id}/{manifest.release_key}/department/"
        f"{manifest.department}/{asset.layer}/{asset.sha256}{_archive_suffix(asset.url)}"
    )


def _register(
    catalog: DatasetCatalog,
    manifest: ReleaseManifest,
    asset: ManifestAsset,
    local_path: Path,
    sha256: str,
    *,
    etag: str | None,
) -> int:
    return catalog.register_raw_asset(
        RawAssetRegistration(
            release_id=manifest.release_id,
            layer=asset.layer,
            territory_code=manifest.department,
            source_url=asset.url,
            object_key=asset.archive_object_key or default_object_key(manifest, asset),
            byte_size=local_path.stat().st_size,
            sha256=sha256,
            etag=etag,
            media_type=asset.media_type,
            content_encoding=asset.content_encoding,
        )
    )
