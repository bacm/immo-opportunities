import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, text

from immo.auth import Principal
from immo.database import get_engine


class MembershipNotFoundError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class OpportunityNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class Actor:
    user_id: str
    organization_id: str
    organization_name: str
    role: str
    display_name: str
    email: str | None


ROLE_LEVEL = {"viewer": 0, "analyst": 1, "organization_admin": 2, "platform_admin": 3}


def _json(value: object) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _iso(value: Any) -> str:
    return str(value.isoformat())


def _set_context(connection: Connection, principal: Principal) -> Actor:
    connection.execute(
        text("SELECT set_config('app.current_subject', :subject, true)"),
        {"subject": principal.subject},
    )
    user = (
        connection.execute(
            text(
                """
                SELECT users.id AS user_id, users.display_name, users.email
                  FROM app.app_user AS users
                 WHERE users.external_subject = :subject
                """
            ),
            {"subject": principal.subject},
        )
        .mappings()
        .one_or_none()
    )
    if user is None:
        raise MembershipNotFoundError(principal.subject)
    connection.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": user["user_id"]},
    )
    membership = (
        connection.execute(
            text(
                """
                SELECT organization_id, role
                  FROM app.organization_membership
                 WHERE user_id = :user_id
                 ORDER BY is_default DESC, created_at, organization_id
                 LIMIT 1
                """
            ),
            {"user_id": user["user_id"]},
        )
        .mappings()
        .one_or_none()
    )
    if membership is None:
        raise MembershipNotFoundError(principal.subject)
    connection.execute(
        text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
        {"organization_id": membership["organization_id"]},
    )
    organization_name = connection.execute(
        text("SELECT name FROM app.organization WHERE id = :id"),
        {"id": membership["organization_id"]},
    ).scalar_one()
    row = {
        **dict(user),
        **dict(membership),
        "organization_name": organization_name,
    }

    connection.execute(
        text(
            """
            UPDATE app.app_user
               SET last_seen_at = now(), email = :email, display_name = :display_name
             WHERE id = :user_id
            """
        ),
        {
            "user_id": row["user_id"],
            "email": principal.email,
            "display_name": principal.display_name,
        },
    )
    return Actor(
        user_id=str(row["user_id"]),
        organization_id=str(row["organization_id"]),
        organization_name=str(row["organization_name"]),
        role=str(row["role"]),
        display_name=principal.display_name,
        email=principal.email,
    )


@contextmanager
def actor_connection(principal: Principal) -> Generator[tuple[Connection, Actor]]:
    with get_engine().begin() as connection:
        yield connection, _set_context(connection, principal)


def require_role(actor: Actor, minimum: str) -> None:
    if ROLE_LEVEL.get(actor.role, -1) < ROLE_LEVEL[minimum]:
        raise PermissionDeniedError(f"{minimum} role required")


def _require_opportunity(connection: Connection, opportunity_id: str) -> None:
    found = connection.execute(
        text(
            "SELECT 1 FROM scoring.published_opportunity "
            "CROSS JOIN meta.active_regional_release AS regional "
            "WHERE opportunity_snapshot_id = :opportunity_id"
            " AND regional.singleton"
        ),
        {"opportunity_id": opportunity_id},
    ).first()
    if found is None:
        raise OpportunityNotFoundError(opportunity_id)


def get_session(principal: Principal) -> dict[str, Any]:
    with actor_connection(principal) as (_, actor):
        return {
            "user_id": actor.user_id,
            "display_name": actor.display_name,
            "email": actor.email,
            "organization_id": actor.organization_id,
            "organization_name": actor.organization_name,
            "role": actor.role,
        }


def get_workspace(principal: Principal, opportunity_id: str) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        _require_opportunity(connection, opportunity_id)
        state = (
            connection.execute(
                text(
                    """
                    SELECT status, favorite, rejection_reasons, rejection_comment, updated_at
                      FROM app.candidate_state
                     WHERE organization_id = :organization_id
                       AND opportunity_snapshot_id = :opportunity_id
                    """
                ),
                {"organization_id": actor.organization_id, "opportunity_id": opportunity_id},
            )
            .mappings()
            .one_or_none()
        )
        history = connection.execute(
            text(
                """
                SELECT history.id, history.previous_status, history.status,
                       history.rejection_reasons, history.rejection_comment,
                       history.author_name AS author, history.occurred_at
                  FROM app.candidate_status_history AS history
                 WHERE history.organization_id = :organization_id
                   AND history.opportunity_snapshot_id = :opportunity_id
                 ORDER BY history.occurred_at DESC, history.id DESC
                """
            ),
            {"organization_id": actor.organization_id, "opportunity_id": opportunity_id},
        ).mappings()
        notes = connection.execute(
            text(
                """
                SELECT note.id, note.body, note.author_name AS author, note.created_at
                  FROM app.note
                 WHERE note.organization_id = :organization_id
                   AND note.opportunity_snapshot_id = :opportunity_id
                 ORDER BY note.created_at DESC, note.id DESC
                """
            ),
            {"organization_id": actor.organization_id, "opportunity_id": opportunity_id},
        ).mappings()
        scenarios = connection.execute(
            text(
                """
                SELECT id, assumptions, results, created_at
                  FROM app.candidate_scenario
                 WHERE organization_id = :organization_id
                   AND opportunity_snapshot_id = :opportunity_id
                 ORDER BY created_at DESC, id DESC
                """
            ),
            {"organization_id": actor.organization_id, "opportunity_id": opportunity_id},
        ).mappings()
        return {
            "state": {
                "status": str(state["status"]),
                "favorite": bool(state["favorite"]),
                "rejection_reasons": _json(state["rejection_reasons"]),
                "rejection_comment": state["rejection_comment"],
                "updated_at": _iso(state["updated_at"]),
            }
            if state
            else {
                "status": "new",
                "favorite": False,
                "rejection_reasons": [],
                "rejection_comment": None,
                "updated_at": None,
            },
            "history": [
                {
                    **dict(row),
                    "rejection_reasons": _json(row["rejection_reasons"]),
                    "occurred_at": _iso(row["occurred_at"]),
                }
                for row in history
            ],
            "notes": [{**dict(row), "created_at": _iso(row["created_at"])} for row in notes],
            "scenarios": [
                {
                    **dict(row),
                    "assumptions": _json(row["assumptions"]),
                    "results": _json(row["results"]),
                    "created_at": _iso(row["created_at"]),
                }
                for row in scenarios
            ],
        }


def change_status(
    principal: Principal,
    opportunity_id: str,
    *,
    status: str,
    favorite: bool | None,
    rejection_reasons: list[str],
    rejection_comment: str | None,
) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        _require_opportunity(connection, opportunity_id)
        previous = (
            connection.execute(
                text(
                    """
                SELECT status, favorite FROM app.candidate_state
                 WHERE organization_id = :organization_id
                   AND opportunity_snapshot_id = :opportunity_id
                 FOR UPDATE
                """
                ),
                {"organization_id": actor.organization_id, "opportunity_id": opportunity_id},
            )
            .mappings()
            .one_or_none()
        )
        previous_status = str(previous["status"]) if previous else None
        effective_favorite = (
            favorite if favorite is not None else bool(previous["favorite"] if previous else False)
        )
        params = {
            "organization_id": actor.organization_id,
            "opportunity_id": opportunity_id,
            "status": status,
            "favorite": effective_favorite,
            "rejection_reasons": json.dumps(rejection_reasons),
            "rejection_comment": rejection_comment,
            "author_id": actor.user_id,
        }
        state = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.candidate_state (
                        organization_id, opportunity_snapshot_id, status, favorite,
                        rejection_reasons, rejection_comment, updated_by
                    ) VALUES (
                        :organization_id, :opportunity_id, :status, :favorite,
                        CAST(:rejection_reasons AS jsonb), :rejection_comment, :author_id
                    )
                    ON CONFLICT (organization_id, opportunity_snapshot_id) DO UPDATE SET
                        status = EXCLUDED.status, favorite = EXCLUDED.favorite,
                        rejection_reasons = EXCLUDED.rejection_reasons,
                        rejection_comment = EXCLUDED.rejection_comment,
                        updated_by = EXCLUDED.updated_by, updated_at = now()
                    RETURNING status, favorite, rejection_reasons, rejection_comment, updated_at
                    """
                ),
                params,
            )
            .mappings()
            .one()
        )
        if previous_status != status:
            connection.execute(
                text(
                    """
                    INSERT INTO app.candidate_status_history (
                        organization_id, opportunity_snapshot_id, previous_status, status,
                        rejection_reasons, rejection_comment, author_id, author_name
                    ) VALUES (
                        :organization_id, :opportunity_id, :previous_status, :status,
                        CAST(:rejection_reasons AS jsonb), :rejection_comment,
                        :author_id, :author_name
                    )
                    """
                ),
                {
                    **params,
                    "previous_status": previous_status,
                    "author_name": actor.display_name,
                },
            )
        return {
            "status": str(state["status"]),
            "favorite": bool(state["favorite"]),
            "rejection_reasons": _json(state["rejection_reasons"]),
            "rejection_comment": state["rejection_comment"],
            "updated_at": _iso(state["updated_at"]),
        }


def add_note(principal: Principal, opportunity_id: str, body: str) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        _require_opportunity(connection, opportunity_id)
        note_id = f"note:{uuid4()}"
        row = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.note (
                        id, organization_id, opportunity_snapshot_id, body,
                        author_id, author_name
                    ) VALUES (
                        :id, :organization_id, :opportunity_id, :body,
                        :author_id, :author_name
                    )
                    RETURNING id, body, created_at
                    """
                ),
                {
                    "id": note_id,
                    "organization_id": actor.organization_id,
                    "opportunity_id": opportunity_id,
                    "body": body.strip(),
                    "author_id": actor.user_id,
                    "author_name": actor.display_name,
                },
            )
            .mappings()
            .one()
        )
        return {**dict(row), "author": actor.display_name, "created_at": _iso(row["created_at"])}


def add_review(
    principal: Principal,
    opportunity_id: str,
    *,
    decision: str,
    rejection_reasons: list[str],
    confidence: int,
    field_visit_performed: bool,
    strategy_code: str | None = None,
    protocol_version: str | None = None,
    protocol_arm: str | None = None,
    evaluation_split: str | None = None,
    segment_code: str | None = None,
    blind_id: str | None = None,
    double_review_group: str | None = None,
) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        _require_opportunity(connection, opportunity_id)
        review_id = f"review:{uuid4()}"
        reviewer_pseudonym = connection.execute(
            text(
                """
                INSERT INTO app.pilot_reviewer_identity (organization_id, user_id)
                VALUES (:organization_id, :author_id)
                ON CONFLICT (organization_id, user_id) DO UPDATE
                    SET user_id = EXCLUDED.user_id
                RETURNING pseudonym
                """
            ),
            {"organization_id": actor.organization_id, "author_id": actor.user_id},
        ).scalar_one()
        row = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.candidate_review (
                        id, organization_id, opportunity_snapshot_id, decision,
                        rejection_reasons, confidence, field_visit_performed,
                        author_id, author_name, strategy_code, protocol_version,
                        protocol_arm, evaluation_split, segment_code,
                        reviewer_pseudonym, blind_id, double_review_group
                    ) VALUES (
                        :id, :organization_id, :opportunity_id, :decision,
                        CAST(:rejection_reasons AS jsonb), :confidence,
                        :field_visit_performed, :author_id, :author_name,
                        :strategy_code, :protocol_version, :protocol_arm,
                        :evaluation_split, :segment_code, :reviewer_pseudonym,
                        :blind_id, :double_review_group
                    )
                    RETURNING id, decision, rejection_reasons, confidence,
                              field_visit_performed, strategy_code, protocol_version,
                              evaluation_split, segment_code, reviewer_pseudonym,
                              blind_id, double_review_group, reviewed_at
                    """
                ),
                {
                    "id": review_id,
                    "organization_id": actor.organization_id,
                    "opportunity_id": opportunity_id,
                    "decision": decision,
                    "rejection_reasons": json.dumps(rejection_reasons),
                    "confidence": confidence,
                    "field_visit_performed": field_visit_performed,
                    "author_id": actor.user_id,
                    "author_name": actor.display_name,
                    "strategy_code": strategy_code,
                    "protocol_version": protocol_version,
                    "protocol_arm": protocol_arm,
                    "evaluation_split": evaluation_split,
                    "segment_code": segment_code,
                    "reviewer_pseudonym": reviewer_pseudonym,
                    "blind_id": blind_id,
                    "double_review_group": double_review_group,
                },
            )
            .mappings()
            .one()
        )
        return {
            **dict(row),
            "rejection_reasons": _json(row["rejection_reasons"]),
            "author": actor.display_name,
            "reviewed_at": _iso(row["reviewed_at"]),
        }


def add_review_outcome(
    principal: Principal,
    review_id: str,
    *,
    stage: str,
    result: str,
    details: dict[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        review = connection.execute(
            text(
                """
                SELECT 1 FROM app.candidate_review
                 WHERE id = :review_id AND organization_id = :organization_id
                """
            ),
            {"review_id": review_id, "organization_id": actor.organization_id},
        ).first()
        if review is None:
            raise OpportunityNotFoundError(review_id)
        outcome_id = f"outcome:{uuid4()}"
        row = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.candidate_review_outcome (
                        id, organization_id, candidate_review_id, stage, result,
                        details, observed_at, author_id
                    ) VALUES (
                        :id, :organization_id, :review_id, :stage, :result,
                        CAST(:details AS jsonb), CAST(:observed_at AS timestamptz), :author_id
                    )
                    RETURNING id, candidate_review_id, stage, result,
                              details, observed_at, created_at
                    """
                ),
                {
                    "id": outcome_id,
                    "organization_id": actor.organization_id,
                    "review_id": review_id,
                    "stage": stage,
                    "result": result,
                    "details": json.dumps(details),
                    "observed_at": observed_at,
                    "author_id": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        return {
            **dict(row),
            "details": _json(row["details"]),
            "observed_at": _iso(row["observed_at"]),
            "created_at": _iso(row["created_at"]),
        }


def calculate_scenario(assumptions: dict[str, Decimal]) -> dict[str, float]:
    purchase = assumptions["purchase_price_eur"]
    works = assumptions["works_cost_eur"]
    resale = assumptions["resale_price_eur"]
    fees = assumptions["fees_eur"]
    finance = assumptions["finance_cost_eur"]
    holding = assumptions["holding_cost_eur"]
    total = purchase + works + fees + finance + holding
    margin = resale - total
    return {
        "total_cost_eur": float(total),
        "net_margin_eur": float(margin),
        "return_on_cost": float(margin / total) if total else 0.0,
    }


def add_scenario(
    principal: Principal, opportunity_id: str, assumptions: dict[str, Decimal]
) -> dict[str, Any]:
    results = calculate_scenario(assumptions)
    serialized = {key: float(value) for key, value in assumptions.items()}
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        _require_opportunity(connection, opportunity_id)
        scenario_id = f"scenario:user:{uuid4()}"
        row = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.candidate_scenario (
                        id, organization_id, opportunity_snapshot_id,
                        assumptions, results, author_id
                    ) VALUES (
                        :id, :organization_id, :opportunity_id,
                        CAST(:assumptions AS jsonb), CAST(:results AS jsonb), :author_id
                    )
                    RETURNING created_at
                    """
                ),
                {
                    "id": scenario_id,
                    "organization_id": actor.organization_id,
                    "opportunity_id": opportunity_id,
                    "assumptions": json.dumps(serialized),
                    "results": json.dumps(results),
                    "author_id": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        return {
            "id": scenario_id,
            "assumptions": serialized,
            "results": results,
            "created_at": _iso(row["created_at"]),
        }


def add_saved_search(principal: Principal, *, name: str, filters: dict[str, Any]) -> dict[str, Any]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "analyst")
        search_id = f"search:{uuid4()}"
        row = (
            connection.execute(
                text(
                    """
                    INSERT INTO app.saved_search (
                        id, organization_id, name, filters, owner_id
                    ) VALUES (:id, :organization_id, :name, CAST(:filters AS jsonb), :owner_id)
                    RETURNING created_at
                    """
                ),
                {
                    "id": search_id,
                    "organization_id": actor.organization_id,
                    "name": name.strip(),
                    "filters": json.dumps(filters),
                    "owner_id": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        return {
            "id": search_id,
            "name": name.strip(),
            "filters": filters,
            "created_at": _iso(row["created_at"]),
        }


def list_import_runs(principal: Principal, request_id: str, limit: int) -> list[dict[str, Any]]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "organization_admin")
        rows = connection.execute(
            text(
                """
                SELECT run.id, run.release_id, run.territory_type, run.territory_code,
                       run.status, run.started_at, run.completed_at, run.source_row_count,
                       run.normalized_row_count, run.quarantined_row_count, run.error_message
                  FROM meta.import_run AS run
                 ORDER BY run.started_at DESC, run.id DESC LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()
        _audit(connection, actor, request_id, "admin.import_runs.read", "import_run", None)
        return [
            {
                **dict(row),
                "started_at": _iso(row["started_at"]),
                "completed_at": _iso(row["completed_at"]) if row["completed_at"] else None,
            }
            for row in rows
        ]


def list_match_metrics(
    principal: Principal,
    request_id: str,
    limit: int,
    relation_type: str | None = None,
    commune_code: str | None = None,
) -> list[dict[str, Any]]:
    """Distribution en quatre classes par commune — exigence FR-012.

    Les quatre classes sont exposées telles quelles, jamais additionnées : « non apparié » est
    une absence de décision, « rejeté » une décision motivée. `coverage` distingue de surcroît
    une commune sans aucun enregistrement source d'une commune où rien n'apparie — les quatre
    classes à zéro identifient exactement le premier cas.
    """
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "organization_admin")
        rows = connection.execute(
            text(
                """
                SELECT metric.release_id, metric.commune_code, commune.name AS commune_name,
                       metric.relation_type, metric.algorithm_code, metric.algorithm_version,
                       metric.certain_count, metric.ambiguous_count,
                       metric.rejected_count, metric.unmatched_count,
                       metric.certain_count + metric.ambiguous_count
                         + metric.rejected_count + metric.unmatched_count AS total_count,
                       metric.measured_at
                  FROM meta.entity_match_metric AS metric
                  LEFT JOIN reference.area AS commune
                         ON commune.area_type = 'commune'
                        AND commune.code = metric.commune_code
                 WHERE (
                           CAST(:relation_type AS text) IS NULL
                           OR metric.relation_type = CAST(:relation_type AS text)
                       )
                   AND (
                           CAST(:commune_code AS text) IS NULL
                           OR metric.commune_code = CAST(:commune_code AS text)
                       )
                 ORDER BY metric.relation_type, metric.commune_code
                 LIMIT :limit
                """
            ),
            {
                "limit": limit,
                "relation_type": relation_type,
                "commune_code": commune_code,
            },
        ).mappings()
        _audit(
            connection, actor, request_id, "admin.match_metrics.read", "entity_match_metric", None
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            total = int(row["total_count"])
            results.append(
                {
                    **dict(row),
                    "total_count": total,
                    # Un taux ne se publie jamais sans son volume, et n'existe pas sans lui.
                    "certain_rate": (int(row["certain_count"]) / total) if total else None,
                    "coverage": "source_absent" if total == 0 else "covered",
                    "measured_at": _iso(row["measured_at"]),
                }
            )
        return results


def list_data_quality(principal: Principal, request_id: str, limit: int) -> list[dict[str, Any]]:
    with actor_connection(principal) as (connection, actor):
        require_role(actor, "organization_admin")
        rows = connection.execute(
            text(
                """
                SELECT check_code, check_version, scope_type, scope_code, layer,
                       status, severity, blocks_publication, observed_value,
                       expected_value, details, checked_at
                  FROM meta.data_quality_check
                 ORDER BY checked_at DESC, id DESC LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()
        _audit(connection, actor, request_id, "admin.data_quality.read", "data_quality", None)
        return [
            {
                **dict(row),
                "observed_value": float(row["observed_value"])
                if row["observed_value"] is not None
                else None,
                "expected_value": float(row["expected_value"])
                if row["expected_value"] is not None
                else None,
                "details": _json(row["details"]),
                "checked_at": _iso(row["checked_at"]),
            }
            for row in rows
        ]


def _audit(
    connection: Connection,
    actor: Actor,
    request_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO audit.sensitive_access_event (
                organization_id, actor_id, action, resource_type, resource_id, request_id
            ) VALUES (
                :organization_id, :actor_id, :action, :resource_type, :resource_id, :request_id
            )
            """
        ),
        {
            "organization_id": actor.organization_id,
            "actor_id": actor.user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request_id": request_id,
        },
    )
