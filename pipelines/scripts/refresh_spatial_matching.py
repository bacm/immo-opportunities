"""Recalcule les métriques d'appariement de toutes les relations spatiales — B3.

Les métriques par commune sont produites à l'import, donc **contre les seules données présentes
à cet instant**. La relation adresse ↔ bâtiment en portait la conséquence : calculée pendant
l'import BAN, elle restait vide en silence si le RNB était importé après, la jointure ne produisant
aucune ligne sans échouer.

Ce script rejoue les calculs contre l'état courant de la base, quel que soit l'ordre dans lequel
les sources ont été importées. Il est idempotent : les métriques sont mises à jour en place.
"""

import argparse
import json

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.importer import (
    BanImporter,
    BdnbImporter,
    BdtopoImporter,
    RnbImporter,
)

# Tables dont le volume change massivement a chaque import, et dont le planificateur doit
# connaitre la taille reelle avant de choisir un plan.
HOT_TABLES: tuple[str, ...] = (
    "reference.address",
    "reference.building",
    "reference.building_parcel",
    "reference.area",
    "meta.entity_match",
    "meta.entity_observation_link",
    "meta.entity_source_identifier",
    "meta.entity_source_observation",
)


def analyze_hot_tables(connection: psycopg.Connection[object]) -> None:
    """Rafraichir les statistiques avant de planifier quoi que ce soit.

    Mesure du 8 septembre 2026 : apres insertion de 566 248 relations adresse <-> batiment, la
    metrique par commune qui les lit a tourne **4 h 44 sans aboutir**. Statistiques rafraichies,
    la meme requete rend en **2,2 s**. Le planificateur ignorait les lignes fraichement inserees
    et choisissait un plan catastrophique.

    Autovacuum finit par le faire, mais son seuil par defaut — 10 % des lignes — le declenche
    bien apres la requete qui suit immediatement l'insertion.

    `ANALYZE` exige d'etre proprietaire de la table. `pipeline_rw` ne l'est pas : il se contente
    d'un avertissement et saute la table. Le role de connexion est deja membre de
    `migration_owner`, proprietaire des tables ; on l'endosse ici, dans un script de maintenance
    lance par un operateur, et nulle part ailleurs.
    """
    connection.execute("SET ROLE migration_owner")
    for table in HOT_TABLES:
        connection.execute(f"ANALYZE {table}")
    connection.execute("RESET ROLE")
    connection.commit()


def active_release(connection: psycopg.Connection[object], data_source_id: str) -> str | None:
    """La release active de la source, ou la dernière importée avec succès."""
    row = connection.execute(
        """
        SELECT release.id
          FROM meta.dataset_release AS release
         WHERE release.data_source_id = %s
           AND EXISTS (
               SELECT 1 FROM meta.import_run AS run
                WHERE run.release_id = release.id AND run.status = 'succeeded'
           )
         ORDER BY release.source_published_on DESC, release.id DESC
         LIMIT 1
        """,
        (data_source_id,),
    ).fetchone()
    return str(row[0]) if row else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute spatial matching metrics")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), default="35")
    arguments = parser.parse_args()
    department = str(arguments.department)

    settings = CadastreSettings.from_environment()
    outcome: dict[str, object] = {"department": department}
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        analyze_hot_tables(connection)

        ban_release = active_release(connection, "DS-05")
        rnb_release = active_release(connection, "DS-02")
        bdtopo_release = active_release(connection, "DS-04")
        bdnb_release = active_release(connection, "DS-03")

        if rnb_release is not None:
            RnbImporter(connection).refresh_match_metrics(rnb_release, department)
            outcome["building_parcel"] = rnb_release
        if ban_release is not None:
            ban = BanImporter(connection)
            ban.refresh_match_metrics(ban_release, department)
            outcome["address_parcel"] = ban_release
            # Independant de l'ordre d'import, contrairement au calcul fait dans _publish_stage.
            outcome["address_building_relations"] = ban.refresh_address_building_relations(
                ban_release
            )
            # Les relations qui viennent d'etre inserees doivent etre visibles du
            # planificateur avant la metrique qui les lit — voir analyze_hot_tables.
            analyze_hot_tables(connection)
            ban.refresh_address_building_metrics(ban_release, department)
            outcome["address_building"] = ban_release
        if bdtopo_release is not None:
            BdtopoImporter(connection).refresh_match_metrics(bdtopo_release, department)
            outcome["bdtopo_building_rnb"] = bdtopo_release
        if bdnb_release is not None:
            BdnbImporter(connection).refresh_match_metrics(bdnb_release, department)
            outcome["bdnb_group_rnb"] = bdnb_release

    print(json.dumps(outcome, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
