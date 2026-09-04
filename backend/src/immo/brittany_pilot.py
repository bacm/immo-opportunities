from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import text

from immo.auth import Principal
from immo.connected_mvp import actor_connection, require_role

BRITTANY_DEPARTMENTS = ("22", "29", "35", "56")
BRITTANY_DATASETS = tuple(f"DS-{number:02d}" for number in range(1, 10))


def get_brittany_readiness(principal: Principal) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "organization_admin")
        rows = connection.execute(
            text(
                """
                SELECT department_code, data_source_id, release_id,
                       acceptance_status, ready, blocking_quality_count
                  FROM meta.brittany_release_readiness
                 ORDER BY department_code, data_source_id
                """
            )
        ).mappings()
        territories: dict[str, dict[str, Any]] = {
            department: {"covered": True, "sources": []} for department in BRITTANY_DEPARTMENTS
        }
        for row in rows:
            department = str(row["department_code"])
            ready = bool(row["ready"]) and int(row["blocking_quality_count"]) == 0
            territories[department]["covered"] = territories[department]["covered"] and ready
            territories[department]["sources"].append(
                {
                    "data_source_id": str(row["data_source_id"]),
                    "release_id": str(row["release_id"]) if row["release_id"] else None,
                    "acceptance_status": (
                        str(row["acceptance_status"]) if row["acceptance_status"] else "missing"
                    ),
                    "blocking_quality_count": int(row["blocking_quality_count"]),
                    "ready": ready,
                }
            )
        active_bundle = (
            connection.execute(
                text(
                    """
                SELECT active.bundle_id, active.published_at, active.published_by
                  FROM meta.active_regional_release AS active WHERE singleton
                """
                )
            )
            .mappings()
            .one_or_none()
        )
        segmentation = (
            connection.execute(
                text(
                    """
                SELECT id, version, status FROM scoring.segment_definition
                 WHERE id = 'brittany-market-segments'
                 ORDER BY version DESC LIMIT 1
                """
                )
            )
            .mappings()
            .one()
        )
        active_scores = int(
            connection.execute(
                text(
                    """
                    SELECT count(*) FROM scoring.active_score_definition AS active
                    JOIN scoring.score_definition AS definition
                      ON definition.id = active.definition_id
                     AND definition.version = active.definition_version
                   WHERE definition.publication_eligible
                    """
                )
            ).scalar_one()
        )
        regional_coverage = all(item["covered"] for item in territories.values())
        publishable = (
            regional_coverage and active_scores == 2 and segmentation["status"] == "active"
        )
        blockers: list[str] = []
        if not regional_coverage:
            blockers.append("regional_data_not_covered")
        if active_scores != 2:
            blockers.append("score_definitions_not_active")
        if segmentation["status"] != "active":
            blockers.append("segmentation_not_active")
        return {
            "publishable": publishable,
            "blockers": blockers,
            "territories": territories,
            "active_score_count": active_scores,
            "segmentation": dict(segmentation),
            "active_bundle": dict(active_bundle) if active_bundle else None,
        }


def publish_brittany(principal: Principal, *, reason: str) -> dict[str, str]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "platform_admin")
        bundle_id = f"brittany:{uuid4()}"
        connection.execute(
            text("SELECT meta.stage_brittany_release(:bundle_id, :actor, :reason)"),
            {"bundle_id": bundle_id, "actor": actor.user_id, "reason": reason},
        )
        connection.execute(
            text("SELECT meta.publish_brittany_release(:bundle_id, :actor, :reason, 'publish')"),
            {"bundle_id": bundle_id, "actor": actor.user_id, "reason": reason},
        )
        return {"bundle_id": bundle_id, "status": "published"}


def rollback_brittany(principal: Principal, *, bundle_id: str, reason: str) -> dict[str, str]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "platform_admin")
        connection.execute(
            text("SELECT meta.publish_brittany_release(:bundle_id, :actor, :reason, 'rollback')"),
            {"bundle_id": bundle_id, "actor": actor.user_id, "reason": reason},
        )
        return {"bundle_id": bundle_id, "status": "published"}


def withdraw_brittany(principal: Principal, *, reason: str) -> dict[str, str]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "platform_admin")
        connection.execute(
            text("SELECT meta.withdraw_brittany_release(:actor, :reason)"),
            {"actor": actor.user_id, "reason": reason},
        )
        return {"status": "withdrawn"}
