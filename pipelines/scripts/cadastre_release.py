"""Inspect, accept, publish or roll back a DS-01 release explicitly."""

import argparse
import json
from typing import Any

import psycopg

from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.settings import CadastreSettings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report")
    report.add_argument("release_id")

    compare = subparsers.add_parser("compare")
    compare.add_argument("left_release_id")
    compare.add_argument("right_release_id")

    accept = subparsers.add_parser("accept")
    accept.add_argument("release_id")
    accept.add_argument("--mode", choices=("accepted", "display_only", "rejected"), required=True)

    publish = subparsers.add_parser("publish")
    publish.add_argument("release_id")
    publish.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    publish.add_argument("--actor", required=True)
    publish.add_argument("--reason", required=True)
    publish.add_argument("--action", choices=("publish", "rollback"), default="publish")

    rollback = subparsers.add_parser("rollback-unpublished")
    rollback.add_argument("release_id")
    rollback.add_argument("--actor", required=True)
    rollback.add_argument("--reason", required=True)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    settings = CadastreSettings.from_environment()
    result: dict[str, Any]
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        catalog = DatasetCatalog(connection)
        if arguments.command == "report":
            result = catalog.quality_report(arguments.release_id)
        elif arguments.command == "compare":
            result = catalog.compare_releases(arguments.left_release_id, arguments.right_release_id)
        elif arguments.command == "accept":
            catalog.set_acceptance(arguments.release_id, arguments.mode)
            result = {"release_id": arguments.release_id, "acceptance": arguments.mode}
        elif arguments.command == "publish":
            catalog.publish(
                arguments.release_id,
                arguments.department,
                actor=arguments.actor,
                reason=arguments.reason,
                action=arguments.action,
            )
            result = {
                "release_id": arguments.release_id,
                "department": arguments.department,
                "action": arguments.action,
            }
        else:
            catalog.rollback_unpublished(
                arguments.release_id,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            result = {"release_id": arguments.release_id, "rollback": "unpublished"}
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
