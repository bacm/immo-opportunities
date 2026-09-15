#!/usr/bin/env python3
"""Importer une release DS-08 : documents, zones et contraintes — D2.

Les couches structurées seulement. **Aucune pièce écrite n'est lue** : l'interprétation du texte
des règlements est interdite ici et relève de `D2b`, où un humain la fait. Le schéma le garantit
de son côté — `urban_zone.rule_profile` ne peut exister sans sa version, sa date de validation et
son validateur.

## Cinq règles tirées de l'épinglage

Quatre défauts de même famille s'y sont succédé, tous silencieux. Ce script les applique :

1. **Un cas non prévu échoue bruyamment.** Une couche attendue et absente arrête le document, elle
   ne le laisse pas passer à moitié importé.
2. **Un échec est consigné, pas seulement journalisé.**
3. **Un échec passager n'est pas définitif** — il fait sortir en code 3, pour qu'une relance soit
   une décision et non un oubli.
4. **Une lecture partielle vérifie ce qu'elle a reçu** — assuré par `remote_zip`.
5. **Un fichier peut mentir sur sa nature.** `DU_35093` porte deux archives Office sous une
   extension `.dbf`. La signature des couches est vérifiée avant lecture.

## Idempotence

La clé et l'identifiant de run portent la version de transformation. Sans elle, un correctif de
code n'atteindrait jamais les données — constaté sur BUG-09, où la règle du rang était écrite,
testée, et les 1 240 355 relations fautives restaient en base.

Cette clé vit dans `meta.import_run`, et c'était **le défaut de la première version de ce
script** : il n'en écrivait aucun. `set_acceptance` appelle `_require_successful_import`, qui
refusait donc tout verdict sur `DS-08@2026-09-14` — la garde est correcte, une release sans
import traçable ne doit pas être publiable. Voir BUG-14.

La clé porte l'empreinte du **manifeste**, et non celle d'un actif : une release GPU est faite de
184 documents et d'autant d'empreintes de couches ; c'est le manifeste qui les fixe toutes.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from shapely.geometry import shape

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.cnig import Feature, find_layers, read_features
from immo_pipelines.market_data.remote_zip import open_remote
from immo_pipelines.progress import Progress

# 1 : premier import GPU. Zonage et contraintes, sans interpretation de reglement.
GPU_TRANSFORMATION_VERSION = "1"

# Le statut vient du **catalogue**, dont la specification enumere les valeurs, et non du champ
# `ETAT` de `DOC_URBA`.
#
# `ETAT` a d'abord ete interprete de memoire — 03 approuve, 05 annule — ce qui a produit
# 32 documents « annules » alors que le GPU les declare tous APPROVED, et 40 « informational »
# pour un code 07 dont la signification n'a jamais ete sourcee. C'est la meme faute que refuser
# d'interpreter le champ `type` du cadastre pour LAND-010, sauf qu'ici je l'avais commise.
#
# `legalStatus` est documente dans `/api/swagger.yaml` avec ses quatre valeurs. Il fait foi.
LEGAL_STATUS = {
    "APPROVED": "opposable",
    "PARTIALLY_ANNULLED": "opposable",
    "ANNULLED": "cancelled",
    "HISTORICAL": "superseded",
}

# Les prescriptions s'imposent a la parcelle ; `info_*` est porte a connaissance, jamais opposable.
CONSTRAINT_LAYERS = {
    "prescription_surf": "prescription",
    "prescription_lin": "prescription",
    "prescription_pct": "prescription",
    "info_surf": "information",
    "info_lin": "information",
    "info_pct": "information",
}


def parse_date(value: str) -> date | None:
    """Les dates CNIG s'écrivent `AAAAMMJJ` ou `AAAA-MM-JJ` selon la génération de norme."""
    cleaned = value.strip().replace("-", "")
    if len(cleaned) != 8 or not cleaned.isdigit():
        return None
    try:
        return datetime.strptime(cleaned, "%Y%m%d").date()
    except ValueError:
        return None


def geometry_wkt(feature: Feature) -> str | None:
    """La géométrie en WKT, ou `None` si elle est absente ou dégénérée.

    Une géométrie invalide n'est pas réparée en silence : la contrainte `st_isvalid` du schéma la
    refuserait, et c'est voulu. On la signale plutôt que de deviner ce que le producteur voulait.
    """
    if feature.geometry is None:
        return None
    geometry = shape(feature.geometry)
    if geometry.is_empty or not geometry.is_valid:
        # La contrainte `st_isvalid` du schema refuse ces geometries, et c'est voulu : les
        # reparer en silence reviendrait a deviner ce que le producteur voulait dire. Elles sont
        # comptees et le document est importe sans elles, plutot que perdu en entier.
        return None
    return geometry.wkt


def import_document(
    connection: psycopg.Connection[Any],
    *,
    release_id: str,
    asset: dict[str, Any],
    department: str,
) -> dict[str, int]:
    """Un document, ses zones et ses contraintes. Tout ou rien : une seule transaction."""
    archive = zipfile.ZipFile(open_remote(asset["url"]))
    layers = find_layers(archive)
    if "doc_urba" not in layers:
        raise RuntimeError(f"{asset['name']} : pas de couche DOC_URBA")

    document_provenance = "doc_urba"
    try:
        document = next(read_features(archive, layers["doc_urba"]), None)
    except Exception:
        # `DOC_URBA` illisible — pour `DU_35093`, deux archives Office deposees sous une
        # extension `.dbf`. Les zones du meme document declarent pourtant leur `IDURBA`, et
        # c'est le producteur qui l'ecrit, sur une couche lisible de la meme archive.
        #
        # Prendre le producteur au mot sur un autre canal n'est pas deviner : c'est le meme
        # raisonnement que le rattrapage de communes par le catalogue. Sans cela, les 57 zones
        # de Dinard seraient perdues pour une table de metadonnees defectueuse.
        document = None
        document_provenance = "zone_urba_fallback"

    if document is None and "zone_urba" in layers:
        first_zone = next(read_features(archive, layers["zone_urba"]), None)
        if first_zone is not None and first_zone.get("idurba"):
            document = first_zone
            document_provenance = "zone_urba_fallback"

    if document is None:
        raise RuntimeError(f"{asset['name']} : DOC_URBA vide et aucun repli possible")

    identifier = document.get("idurba")
    if not identifier:
        # Sans `IDURBA`, le document ne porte pas sa version exacte, et D2b n'aurait rien a quoi
        # rattacher un profil de regles. C'est le risque declare de la v0.5.
        raise RuntimeError(f"{asset['name']} : IDURBA absent, version du document inconnue")

    approved = parse_date(document.get("datappro"))
    provenance = "cnig_datappro"
    if approved is None:
        # `DATAPPRO` vide sur certains documents. Le catalogue porte la date de publication, qui
        # n'est pas la date d'approbation mais s'en approche et vient du meme producteur. La
        # provenance est marquee pour que le rapport distingue les deux.
        published = str(asset.get("published_at") or "")
        if len(published) >= 10:
            day, month, year = published[:2], published[3:5], published[6:10]
            approved = parse_date(f"{year}{month}{day}")
        provenance = "catalog_published_at"
    if approved is None:
        raise RuntimeError(
            f"{asset['name']} : ni DATAPPRO ni date de publication exploitables "
            f"({document.get('datappro')!r}, {asset.get('published_at')!r})"
        )

    document_id = f"urban-document:gpu:{release_id}:{identifier}"
    connection.execute(
        """
        INSERT INTO observation.urban_document (
            id, release_id, source_identifier, document_type, document_version,
            authority_name, published_at, valid_from, valid_to, status, commune_codes,
            source_url, properties
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
        ON CONFLICT (release_id, source_identifier) DO NOTHING
        """,
        (
            document_id,
            release_id,
            identifier,
            str(asset["document_type"]),
            identifier,
            str(asset.get("territory") or ""),
            approved,
            approved,
            parse_date(document.get("datefin")),
            # Un statut inconnu reste `informational` : ni opposable, ni annule, et visible
            # comme tel plutot que devine.
            LEGAL_STATUS.get(str(asset.get("legal_status") or ""), "informational"),
            # `commune_codes` est du `jsonb` : une liste Python y arriverait comme un litteral
            # de tableau PostgreSQL, que le type refuse.
            json.dumps(asset["communes"]),
            asset["url"],
            json.dumps(
                {
                    "cnig_etat": document.get("etat"),
                    "cnig_typedoc": document.get("typedoc"),
                    "siren": document.get("siren") or None,
                    "legal_status": asset.get("legal_status"),
                    # D'ou vient la liste des communes. `catalog_fallback` est une provenance
                    # degradee, et le rapport de couverture doit pouvoir la distinguer.
                    "communes_provenance": asset.get("communes_provenance", "doc_urba_com"),
                    "approval_date_provenance": provenance,
                    "document_metadata_provenance": document_provenance,
                    # Les pieces ecrites ne sont pas lues ici : leurs noms sont conserves pour
                    # que D2b sache ou aller, sans qu'aucun texte n'entre en base.
                    "written_pieces_url": document.get("urlreg") or None,
                }
            ),
        ),
    )

    counters = {"zones": 0, "constraints": 0, "invalid_geometry": 0}

    if "zone_urba" in layers:
        rows: list[tuple[Any, ...]] = []
        for index, feature in enumerate(read_features(archive, layers["zone_urba"])):
            wkt = geometry_wkt(feature)
            if wkt is None:
                counters["invalid_geometry"] += 1
                continue
            rows.append(
                (
                    document_id,
                    f"{identifier}:{index}",
                    # `libelle` est le code du reglement local : `UG2b` a Rennes n'a aucun
                    # rapport avec `UG2b` ailleurs. `typezone` est normalise CNIG et seul
                    # comparable entre documents. Les deux sont portes, jamais confondus.
                    feature.get("libelle"),
                    feature.get("typezone"),
                    wkt,
                    json.dumps(
                        {
                            "libelong": feature.get("libelong") or None,
                            "destdomi": feature.get("destdomi") or None,
                            "datvalid": feature.get("datvalid") or None,
                        }
                    ),
                )
            )
        connection.cursor().executemany(
            """
            -- `id` est une identite generee : la base l'attribue. L'unicite metier est
            -- (document_id, source_identifier), et c'est elle qui porte l'idempotence.
            INSERT INTO observation.urban_zone (
                document_id, source_identifier, zone_code, zone_type, geom, properties
            ) VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 2154), %s::jsonb)
            ON CONFLICT (document_id, source_identifier) DO NOTHING
            """,
            rows,
        )
        counters["zones"] = len(rows)

    for layer, kind in CONSTRAINT_LAYERS.items():
        if layer not in layers:
            continue
        rows = []
        for index, feature in enumerate(read_features(archive, layers[layer])):
            wkt = geometry_wkt(feature)
            if wkt is None:
                counters["invalid_geometry"] += 1
                continue
            rows.append(
                (
                    document_id,
                    f"{identifier}:{layer}:{index}",
                    kind,
                    feature.get("typepsc") or feature.get("typeinf"),
                    feature.get("libelle"),
                    wkt,
                    json.dumps({"cnig_layer": layer, "txt": feature.get("txt") or None}),
                )
            )
        connection.cursor().executemany(
            """
            INSERT INTO observation.urban_constraint (
                document_id, source_identifier, constraint_type, constraint_code, label,
                geom, properties
            ) VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 2154), %s::jsonb)
            ON CONFLICT (document_id, source_identifier) DO NOTHING
            """,
            rows,
        )
        counters["constraints"] += len(rows)

    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description="Importer une release GPU épinglée")
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--limit", type=int, default=None, help="limiter le nombre de documents")
    parser.add_argument(
        "--only",
        default=None,
        help="noms de documents, séparés par des virgules — rejouer sans relire tout le lot",
    )
    arguments = parser.parse_args()

    manifest_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "datasets"
        / "DS-08"
        / "releases"
        / f"{arguments.release}-{arguments.department}.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    release_id = str(manifest["release_id"])

    settings = CadastreSettings.from_environment()
    totals = {"documents": 0, "zones": 0, "constraints": 0, "invalid_geometry": 0}
    failures: list[dict[str, str]] = []
    transient = 0

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET ROLE pipeline_rw")
        connection.execute(
            """
            INSERT INTO meta.dataset_release (
                id, data_source_id, release_key, source_published_on, contract_version,
                lifecycle_status, acceptance_status, source_srid, canonical_srid, coverage,
                schema_fingerprint
            ) VALUES (%s, 'DS-08', %s, %s, 1, 'discovered', 'pending', 2154, 2154, %s::jsonb,
                      'ds-08-cnig-v1')
            ON CONFLICT (id) DO NOTHING
            """,
            (
                release_id,
                manifest["release_key"],
                manifest["source_published_on"],
                json.dumps({"department": arguments.department}),
            ),
        )
        idempotency_key = (
            f"{release_id}:{arguments.department}:documents:"
            f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}:"
            f"{GPU_TRANSFORMATION_VERSION}"
        )
        import_run_id = (
            f"gpu:{manifest['release_key']}:{arguments.department}:{GPU_TRANSFORMATION_VERSION}"
        )
        existing = connection.execute(
            "SELECT id, status FROM meta.import_run WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        if existing is not None and existing[1] == "succeeded" and not arguments.only:
            print(f"déjà importé par {existing[0]}, rien à faire")
            return 0
        # Un run neuf repart de zero ; un run `running` reprend la ou il s'est arrete.
        #
        # La distinction compte : la reprise existe parce qu'un import departemental demande plus
        # d'une heure et a ete interrompu deux fois. Mais reprendre **sans run** ferait attester
        # « 184 documents » par un run qui n'en a lu aucun — un run doit dire ce qu'il a fait,
        # pas ce qu'il a trouve.
        resuming = existing is not None and existing[1] == "running"
        if existing is not None and not resuming:
            connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))
        if not resuming:
            connection.execute(
                "DELETE FROM observation.urban_document WHERE release_id = %s", (release_id,)
            )
        connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', 'documents', 'documents', %s::int))
            ON CONFLICT (id) DO NOTHING
            """,
            (
                import_run_id,
                release_id,
                arguments.department,
                idempotency_key,
                len(manifest["assets"]),
            ),
        )
        connection.commit()

        # Reprise : ne pas relire une archive dont le document est deja en base. Un import
        # departemental demande plus d'une heure, et il a ete interrompu deux fois — une coupure
        # reseau, puis un `make rebuild` lance pour un autre ticket, qui recree PostgreSQL et
        # coupe toutes les connexions en cours.
        imported = {
            row[0]
            for row in connection.execute(
                "SELECT source_identifier FROM observation.urban_document WHERE release_id = %s",
                (release_id,),
            ).fetchall()
        }
        assets = manifest["assets"]
        if arguments.only:
            wanted = {name.strip() for name in arguments.only.split(",")}
            assets = [a for a in assets if a["name"] in wanted]
        assets = assets[: arguments.limit]
        remaining = [
            asset
            for asset in assets
            if not any(name.startswith(str(asset["name"]).removeprefix("DU_")) for name in imported)
        ]
        # Le total est celui du travail **restant**, pas du manifeste : annoncer « 145/184 » sur
        # une reprise laisserait croire qu'il reste 39 documents a lire alors qu'ils sont deja
        # sautes.
        progress = Progress(len(remaining), "DS-08")
        for asset in remaining:
            try:
                counters = import_document(
                    connection,
                    release_id=release_id,
                    asset=asset,
                    department=arguments.department,
                )
                connection.commit()
            except Exception as error:
                connection.rollback()
                message = f"{type(error).__name__}: {error}".lower()
                if any(
                    marker in message
                    for marker in (
                        "timed out",
                        "timeout",
                        "connection",
                        "not a zip",
                        "429",
                        "débit limité",
                        "too many requests",
                    )
                ):
                    # Un echec reseau ne dit rien du document : ne pas le consigner comme
                    # defectueux, et sortir en code 3 pour qu'une relance soit une decision.
                    transient += 1
                    progress.advance(failed=True)
                    print(f"  {asset['name']} : échec passager ({error})", flush=True)
                    continue
                # `pyshp` leve parfois une exception dont le message est un entier nu : sans le
                # type, l'echec est illisible dans le rapport.
                detail = f"{type(error).__name__}: {error}"
                failures.append({"name": str(asset["name"]), "reason": detail})
                progress.advance(failed=True)
                print(f"  {asset['name']} : échec ({detail})", flush=True)
                continue
            totals["documents"] += 1
            for key, value in counters.items():
                totals[key] = totals.get(key, 0) + value
            progress.advance(detail=f"{totals['zones']} zones, {totals['constraints']} contraintes")
            print(
                f"  {asset['name']:16s} {counters['zones']:5d} zones, "
                f"{counters['constraints']:5d} contraintes",
                flush=True,
            )

        # Le run n'est « reussi » que si rien ne reste a reprendre. Un lot interrompu garde le
        # statut `running` : c'est ce qui empeche `set_acceptance` de prononcer un verdict sur
        # une release importee a moitie.
        connection.execute(
            """
            UPDATE meta.import_run SET
                status = CASE WHEN %(transient)s::int > 0 THEN 'running' ELSE 'succeeded' END,
                completed_at = CASE WHEN %(transient)s::int > 0 THEN NULL ELSE now() END,
                source_row_count = %(documents)s,
                normalized_row_count = %(zones)s,
                quarantined_row_count = %(invalid)s,
                error_message = %(error)s,
                runner_metadata = runner_metadata || %(detail)s::jsonb
             WHERE id = %(id)s
            """,
            {
                "id": import_run_id,
                "transient": transient,
                "documents": totals["documents"],
                "zones": totals["zones"],
                "invalid": totals["invalid_geometry"],
                "error": (f"{len(failures)} document(s) illisible(s)" if failures else None),
                "detail": json.dumps({**totals, "failures": failures}, sort_keys=True),
            },
        )
        connection.commit()

    print(json.dumps({**totals, "failures": failures}, ensure_ascii=False, sort_keys=True))
    if transient:
        print(f"{transient} échec(s) passager(s) : relancer pour compléter")
        return 3
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
