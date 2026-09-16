"""Importer une release départementale d'une source à une couche — BUG-02, BUG-19.

Ce que les scripts RNB et BAN faisaient chacun de leur côté : enregistrer la release, résoudre
l'asset épinglé (archive en base, archive nommée par le manifeste, puis amont), importer, puis
rafraîchir les métriques d'appariement. L'asset Dagster et le script appellent la même fonction,
avec les mêmes clés de run et d'idempotence : rematérialiser retrouve les imports déjà faits.
"""

import hashlib
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from psycopg import Connection

from immo_pipelines.cadastre.archive import extract_seven_zip_member, extract_zip_member
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import (
    AssetStore,
    ReleaseManifest,
    load_release_manifest,
    project_root,
    resolve_asset,
)
from immo_pipelines.spatial.ban import BAN_TRANSFORMATION_VERSION
from immo_pipelines.spatial.bdnb import BDNB_TRANSFORMATION_VERSION
from immo_pipelines.spatial.bdtopo import BDTOPO_TRANSFORMATION_VERSION
from immo_pipelines.spatial.importer import (
    BanImporter,
    BdnbImporter,
    BdtopoImporter,
    RnbImporter,
    SpatialImportOutcome,
)

# Version de la transformation RNB, incluse dans la cle d'idempotence.
#
# Sans elle, une release deja importee est rejouee a vide : le garde d'idempotence voit un
# `import_run` reussi pour la meme cle et retourne sans rien faire. Un correctif de code ne
# peut alors jamais atteindre les donnees, ce qui s'est produit avec BUG-09 — la regle du rang
# etait ecrite, testee, et les 1 240 355 relations fautives restaient en base.
#
# 2 : BUG-09, la relation batiment <-> parcelle cesse d'etre certaine par defaut.
RNB_TRANSFORMATION_VERSION = "2"


class DepartmentImporter(Protocol):
    def import_archive(
        self,
        *,
        import_run_id: str,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        source_path: Path,
        idempotency_key: str,
    ) -> SpatialImportOutcome: ...

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None: ...


@dataclass(frozen=True, slots=True)
class SourceImport:
    """Ce qui distingue une source à une couche d'une autre."""

    data_source_id: str
    layer: str
    source_srid: int
    run_prefix: str
    transformation_version: str
    local_name: str
    importer: Callable[[Connection[Any]], DepartmentImporter]
    # La BAN coupe la connexion avant les en-tetes de reponse avec httpx.
    prefer_curl: bool = False
    # Le membre que le manifeste epingle, extrait de l'archive ; l'archive est ensuite supprimee.
    extract: Callable[[Path, str, Path], Path] | None = None


RNB = SourceImport(
    data_source_id="DS-02",
    layer="buildings",
    source_srid=4326,
    run_prefix="rnb",
    transformation_version=RNB_TRANSFORMATION_VERSION,
    local_name="rnb.csv.zip",
    importer=RnbImporter,
)
BAN = SourceImport(
    data_source_id="DS-05",
    layer="addresses",
    source_srid=2154,
    run_prefix="ban",
    transformation_version=BAN_TRANSFORMATION_VERSION,
    local_name="addresses.csv.gz",
    importer=BanImporter,
    prefer_curl=True,
)
BDNB = SourceImport(
    data_source_id="DS-03",
    layer="bdnb",
    source_srid=2154,
    run_prefix="bdnb",
    transformation_version=BDNB_TRANSFORMATION_VERSION,
    local_name="bdnb.zip",
    importer=BdnbImporter,
    extract=extract_zip_member,
)
BDTOPO = SourceImport(
    data_source_id="DS-04",
    layer="bdtopo",
    source_srid=2154,
    run_prefix="bdtopo",
    transformation_version=BDTOPO_TRANSFORMATION_VERSION,
    local_name="bdtopo.7z",
    importer=BdtopoImporter,
    extract=extract_seven_zip_member,
)


@dataclass(frozen=True, slots=True)
class DepartmentReleaseImport:
    release_id: str
    department_code: str
    asset_origin: str
    sha256: str
    outcome: SpatialImportOutcome


def contract_fingerprint(data_source_id: str, *, root: Path | None = None) -> str:
    path = (root or project_root()) / "contracts" / "datasets" / data_source_id / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_keys(source: SourceImport, manifest: ReleaseManifest, sha256: str) -> tuple[str, str]:
    """Identifiant de run et cle d'idempotence.

    La version entre dans les deux : dans la cle, pour qu'un correctif atteigne les donnees ;
    dans l'identifiant, pour que le nouveau run n'entre pas en collision de cle primaire avec
    l'ancien.
    """
    version = source.transformation_version
    run_id = f"{source.run_prefix}:{manifest.release_key}:{manifest.department}:{version}"
    key = f"{manifest.release_id}:{manifest.department}:{source.layer}:{sha256}:{version}"
    return run_id, key


def import_department_release(
    source: SourceImport,
    release_key: str,
    department_code: str,
    *,
    connection: Connection[Any],
    object_store: AssetStore,
    root: Path | None = None,
) -> DepartmentReleaseImport:
    manifest = load_release_manifest(source.data_source_id, release_key, department_code, root=root)
    asset = manifest.asset(source.layer)
    catalog = DatasetCatalog(connection)
    catalog.register_release(
        release_id=manifest.release_id,
        release_key=manifest.release_key,
        published_on=date.fromisoformat(manifest.source_published_on),
        schema_fingerprint=contract_fingerprint(source.data_source_id, root=root),
        department_code=manifest.department,
        data_source_id=source.data_source_id,
        source_srid=source.source_srid,
    )
    with tempfile.TemporaryDirectory(prefix=f"immo-{source.run_prefix}-") as directory:
        local_path = Path(directory) / source.local_name
        # Un checksum divergent leve ici, avant toute ecriture d'import.
        resolved = resolve_asset(
            catalog=catalog,
            object_store=object_store,
            manifest=manifest,
            asset=asset,
            destination=local_path,
            prefer_curl=source.prefer_curl,
        )
        source_path = local_path
        if source.extract is not None:
            if asset.member_path is None:
                raise RuntimeError(f"{source.data_source_id} manifest must name the archive member")
            source_path = source.extract(local_path, asset.member_path, Path(directory))
            # L'archive n'a plus d'utilite une fois le membre extrait, et les deux ensemble
            # saturent le disque du conteneur (BD TOPO : 529 Mo et 3,1 Go).
            local_path.unlink(missing_ok=True)
        run_id, idempotency_key = run_keys(source, manifest, resolved.sha256)
        importer = source.importer(connection)
        outcome = importer.import_archive(
            import_run_id=run_id,
            release_id=manifest.release_id,
            department_code=manifest.department,
            raw_asset_id=resolved.raw_asset_id,
            source_path=source_path,
            idempotency_key=idempotency_key,
        )
        importer.refresh_match_metrics(manifest.release_id, manifest.department)
    return DepartmentReleaseImport(
        release_id=manifest.release_id,
        department_code=manifest.department,
        asset_origin=resolved.origin,
        sha256=resolved.sha256,
        outcome=outcome,
    )
