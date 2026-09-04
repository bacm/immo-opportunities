import json
from decimal import Decimal
from typing import Any, TypedDict, cast

from sqlalchemy import text

from immo.database import get_engine


class OpportunitySummary(TypedDict):
    id: str
    property_unit_id: str
    strategy: str
    score: float | None
    score_class: str | None
    confidence_score: float
    confidence_level: str
    segment_code: str
    snapshot_at: str
    calculated_at: str
    baseline_selected: bool


class OpportunityDetail(OpportunitySummary):
    definition_id: str
    definition_version: int
    eligible: bool
    eligibility_results: list[dict[str, Any]]
    missing_features: list[str]
    publication_blockers: list[str]
    release_ids: list[str]
    financial_scenario: dict[str, Any] | None
    components: list[dict[str, Any]]


def _json(value: object) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _float(value: object) -> float:
    return float(cast(Decimal | float, value))


OPPORTUNITY_SELECT = """
    SELECT snapshot.id, snapshot.property_unit_id,
           snapshot.strategy_code AS strategy,
           snapshot.overall_score AS score,
           snapshot.score_class, snapshot.confidence_score,
           snapshot.confidence_level, snapshot.segment_code,
           snapshot.snapshot_at, snapshot.calculated_at,
           snapshot.baseline_selected,
           snapshot.definition_id, snapshot.definition_version,
           snapshot.eligible, snapshot.eligibility_results,
           snapshot.missing_features, snapshot.publication_blockers,
           snapshot.release_ids,
           CASE WHEN scenario.id IS NULL THEN NULL ELSE jsonb_build_object(
               'id', scenario.id,
               'assumptions', scenario.assumptions,
               'prudent', scenario.prudent,
               'central', scenario.central,
               'optimistic', scenario.optimistic,
               'transformation_version', scenario.transformation_version
           ) END AS financial_scenario,
           COALESCE((
               SELECT jsonb_agg(jsonb_build_object(
                   'code', component.component_code,
                   'weight', component.weight,
                   'score', component.score,
                   'weighted_score', component.weighted_score,
                   'formula', component.formula
               ) ORDER BY component.id)
                 FROM scoring.score_component AS component
                WHERE component.opportunity_snapshot_id = snapshot.id
           ), '[]'::jsonb) AS components
      FROM scoring.opportunity_snapshot AS snapshot
      JOIN meta.active_regional_release AS regional ON regional.singleton
      JOIN reference.property_unit AS unit ON unit.id = snapshot.property_unit_id
      LEFT JOIN scoring.estimate_scenario AS scenario
        ON scenario.id = snapshot.estimate_scenario_id
"""


def _summary(row: dict[str, Any]) -> OpportunitySummary:
    return {
        "id": str(row["id"]),
        "property_unit_id": str(row["property_unit_id"]),
        "strategy": str(row["strategy"]),
        "score": _float(row["score"]) if row["score"] is not None else None,
        "score_class": str(row["score_class"]) if row["score_class"] else None,
        "confidence_score": _float(row["confidence_score"]),
        "confidence_level": str(row["confidence_level"]),
        "segment_code": str(row["segment_code"]),
        "snapshot_at": row["snapshot_at"].isoformat(),
        "calculated_at": row["calculated_at"].isoformat(),
        "baseline_selected": bool(row["baseline_selected"]),
    }


def _detail(row: dict[str, Any]) -> OpportunityDetail:
    return {
        **_summary(row),
        "definition_id": str(row["definition_id"]),
        "definition_version": int(row["definition_version"]),
        "eligible": bool(row["eligible"]),
        "eligibility_results": cast(list[dict[str, Any]], _json(row["eligibility_results"])),
        "missing_features": [str(item) for item in _json(row["missing_features"])],
        "publication_blockers": [str(item) for item in _json(row["publication_blockers"])],
        "release_ids": [str(item) for item in _json(row["release_ids"])],
        "financial_scenario": cast(dict[str, Any] | None, _json(row["financial_scenario"])),
        "components": cast(list[dict[str, Any]], _json(row["components"])),
    }


def list_opportunities(
    *,
    strategy: str | None,
    minimum_score: float | None,
    confidence_level: str | None,
    department_code: str | None,
    limit: int,
    cursor_score: float | None,
    cursor_id: str | None,
) -> list[OpportunitySummary]:
    statement = text(
        OPPORTUNITY_SELECT
        + """
          JOIN scoring.published_opportunity AS published
            ON published.opportunity_snapshot_id = snapshot.id
         WHERE (CAST(:strategy AS text) IS NULL OR snapshot.strategy_code = CAST(:strategy AS text))
           AND (
                CAST(:minimum_score AS double precision) IS NULL
                OR snapshot.overall_score >= CAST(:minimum_score AS double precision)
           )
           AND (
                CAST(:confidence_level AS text) IS NULL
                OR snapshot.confidence_level = CAST(:confidence_level AS text)
           )
           AND (
                CAST(:department_code AS text) IS NULL
                OR unit.department_code = CAST(:department_code AS text)
           )
           AND (
                CAST(:cursor_id AS text) IS NULL
                OR snapshot.overall_score < CAST(:cursor_score AS double precision)
                OR (
                    snapshot.overall_score = CAST(:cursor_score AS double precision)
                    AND snapshot.id > CAST(:cursor_id AS text)
                )
           )
         ORDER BY snapshot.overall_score DESC, snapshot.id
         LIMIT :limit
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(
            statement,
            {
                "strategy": strategy,
                "minimum_score": minimum_score,
                "confidence_level": confidence_level,
                "department_code": department_code,
                "limit": limit,
                "cursor_score": cursor_score,
                "cursor_id": cursor_id,
            },
        ).mappings()
        return [_summary(dict(row)) for row in rows]


def find_opportunity(opportunity_id: str) -> OpportunityDetail | None:
    statement = text(
        OPPORTUNITY_SELECT + " JOIN scoring.published_opportunity AS published "
        "ON published.opportunity_snapshot_id = snapshot.id "
        "WHERE snapshot.id = :opportunity_id"
    )
    with get_engine().connect() as connection:
        row = (
            connection.execute(statement, {"opportunity_id": opportunity_id})
            .mappings()
            .one_or_none()
        )
    return _detail(dict(row)) if row is not None else None


def list_opportunity_history(opportunity_id: str) -> list[OpportunitySummary] | None:
    statement = text(
        OPPORTUNITY_SELECT
        + """
         WHERE (snapshot.property_unit_id, snapshot.strategy_code) = (
             SELECT origin.property_unit_id, origin.strategy_code
               FROM scoring.opportunity_snapshot AS origin
               JOIN scoring.published_opportunity AS published
                 ON published.opportunity_snapshot_id = origin.id
              WHERE origin.id = :opportunity_id
         )
         ORDER BY snapshot.calculated_at DESC, snapshot.id
        """
    )
    with get_engine().connect() as connection:
        rows = list(connection.execute(statement, {"opportunity_id": opportunity_id}).mappings())
    return [_summary(dict(row)) for row in rows] if rows else None


def list_opportunity_evidence(opportunity_id: str) -> list[dict[str, Any]] | None:
    exists_statement = text(
        "SELECT 1 FROM scoring.opportunity_snapshot AS snapshot "
        "JOIN scoring.published_opportunity AS published "
        "ON published.opportunity_snapshot_id = snapshot.id "
        "JOIN meta.active_regional_release AS regional ON regional.singleton "
        "WHERE snapshot.id = :opportunity_id"
    )
    statement = text(
        """
        SELECT feature_code, component_code, direction, impact,
               raw_value, normalized_value, comparison,
               source_observation_ids, source_release_ids, observed_at,
               quality, formula, explanation
          FROM scoring.score_evidence
         WHERE opportunity_snapshot_id = :opportunity_id
         ORDER BY abs(impact) DESC, feature_code
        """
    )
    with get_engine().connect() as connection:
        if connection.execute(exists_statement, {"opportunity_id": opportunity_id}).first() is None:
            return None
        rows = list(connection.execute(statement, {"opportunity_id": opportunity_id}).mappings())
    return [
        {
            "feature_code": str(row["feature_code"]),
            "component_code": str(row["component_code"]) if row["component_code"] else None,
            "direction": str(row["direction"]),
            "impact": _float(row["impact"]),
            "value": _json(row["raw_value"]),
            "normalized_value": _float(row["normalized_value"]),
            "comparison": str(row["comparison"]) if row["comparison"] else None,
            "source_observation_ids": _json(row["source_observation_ids"]),
            "source_release_ids": _json(row["source_release_ids"]),
            "observed_at": row["observed_at"].isoformat() if row["observed_at"] else None,
            "quality": str(row["quality"]),
            "formula": str(row["formula"]),
            "explanation": str(row["explanation"]),
        }
        for row in rows
    ]


def list_opportunity_comparables(opportunity_id: str) -> list[dict[str, Any]] | None:
    context_statement = text(
        """
        SELECT property_unit_id, snapshot_at
          FROM scoring.opportunity_snapshot AS snapshot
          JOIN scoring.published_opportunity AS published
            ON published.opportunity_snapshot_id = snapshot.id
          JOIN meta.active_regional_release AS regional ON regional.singleton
         WHERE snapshot.id = :opportunity_id
        """
    )
    statement = text(
        """
        SELECT transaction.source_identifier AS transaction_id,
               selection.included, selection.decision_reason AS reason,
               selection.distance_m, selection.segment_code,
               selection.transaction_date, selection.property_type,
               selection.surface_m2, selection.normalized_price_m2,
               selection.price_transformations, selection.source_release_ids
          FROM market.comparable_selection AS selection
          JOIN observation.transaction_property AS property
            ON property.id = selection.transaction_property_id
          JOIN observation."transaction" AS transaction
            ON transaction.id = property.transaction_id
         WHERE selection.property_unit_id = :property_unit_id
           AND selection.snapshot_at = :snapshot_at
         ORDER BY selection.included DESC, selection.distance_m, transaction.source_identifier
        """
    )
    with get_engine().connect() as connection:
        context = (
            connection.execute(context_statement, {"opportunity_id": opportunity_id})
            .mappings()
            .one_or_none()
        )
        if context is None:
            return None
        rows = list(
            connection.execute(
                statement,
                {
                    "property_unit_id": context["property_unit_id"],
                    "snapshot_at": context["snapshot_at"],
                },
            ).mappings()
        )
    return [
        {
            "transaction_id": str(row["transaction_id"]),
            "included": bool(row["included"]),
            "reason": str(row["reason"]),
            "distance_m": _float(row["distance_m"]) if row["distance_m"] is not None else None,
            "segment_code": str(row["segment_code"]),
            "transaction_date": row["transaction_date"].isoformat(),
            "property_type": str(row["property_type"]),
            "surface_m2": _float(row["surface_m2"]) if row["surface_m2"] is not None else None,
            "normalized_price_m2": (
                _float(row["normalized_price_m2"])
                if row["normalized_price_m2"] is not None
                else None
            ),
            "price_transformations": _json(row["price_transformations"]),
            "source_release_ids": _json(row["source_release_ids"]),
        }
        for row in rows
    ]


def list_opportunity_sources(opportunity_id: str) -> list[dict[str, Any]] | None:
    statement = text(
        """
        SELECT source.id AS data_source_id, source.name, source.producer,
               source.attribution, release.id AS release_id, release.release_key,
               release.source_published_on, release.acceptance_status
          FROM scoring.opportunity_snapshot AS snapshot
          JOIN scoring.published_opportunity AS published
            ON published.opportunity_snapshot_id = snapshot.id
          JOIN meta.active_regional_release AS regional ON regional.singleton
          CROSS JOIN LATERAL jsonb_array_elements_text(snapshot.release_ids) AS item(release_id)
          JOIN meta.dataset_release AS release ON release.id = item.release_id
          JOIN meta.data_source AS source ON source.id = release.data_source_id
         WHERE snapshot.id = :opportunity_id
         ORDER BY source.id, release.id
        """
    )
    exists_statement = text(
        "SELECT 1 FROM scoring.opportunity_snapshot AS snapshot "
        "JOIN scoring.published_opportunity AS published "
        "ON published.opportunity_snapshot_id = snapshot.id "
        "JOIN meta.active_regional_release AS regional ON regional.singleton "
        "WHERE snapshot.id = :opportunity_id"
    )
    with get_engine().connect() as connection:
        if connection.execute(exists_statement, {"opportunity_id": opportunity_id}).first() is None:
            return None
        rows = list(connection.execute(statement, {"opportunity_id": opportunity_id}).mappings())
    return [
        {
            "data_source_id": str(row["data_source_id"]),
            "name": str(row["name"]),
            "producer": str(row["producer"]),
            "attribution": str(row["attribution"]),
            "release_id": str(row["release_id"]),
            "release_key": str(row["release_key"]),
            "source_published_on": (
                row["source_published_on"].isoformat() if row["source_published_on"] else None
            ),
            "acceptance_status": str(row["acceptance_status"]),
        }
        for row in rows
    ]


def find_score_definition(definition_id: str) -> dict[str, Any] | None:
    definition_statement = text(
        """
        SELECT definition.*,
               active.definition_id IS NOT NULL AS active
          FROM scoring.score_definition AS definition
          LEFT JOIN scoring.active_score_definition AS active
            ON active.definition_id = definition.id
           AND active.definition_version = definition.version
         WHERE definition.id = :definition_id
         ORDER BY definition.version DESC
         LIMIT 1
        """
    )
    component_statement = text(
        """
        SELECT code, label, weight, display_order
          FROM scoring.score_definition_component
         WHERE definition_id = :definition_id AND definition_version = :version
         ORDER BY display_order
        """
    )
    feature_statement = text(
        """
        SELECT feature_code, feature_version, component_code, weight,
               requirement, transformation, direction,
               transformation_parameters, explanation_template
          FROM scoring.score_definition_feature
         WHERE definition_id = :definition_id AND definition_version = :version
         ORDER BY component_code NULLS LAST, feature_code
        """
    )
    eligibility_statement = text(
        """
        SELECT code, predicate, feature_codes, failure_message
          FROM scoring.score_eligibility_rule
         WHERE definition_id = :definition_id AND definition_version = :version
         ORDER BY code
        """
    )
    with get_engine().connect() as connection:
        definition = (
            connection.execute(definition_statement, {"definition_id": definition_id})
            .mappings()
            .one_or_none()
        )
        if definition is None:
            return None
        parameters = {"definition_id": definition_id, "version": definition["version"]}
        components = list(connection.execute(component_statement, parameters).mappings())
        features = list(connection.execute(feature_statement, parameters).mappings())
        eligibility = list(connection.execute(eligibility_statement, parameters).mappings())
    return {
        "id": str(definition["id"]),
        "version": int(definition["version"]),
        "strategy": str(definition["strategy_code"]),
        "contract_path": str(definition["contract_path"]),
        "contract_digest": str(definition["contract_digest"]),
        "feature_registry_version": int(definition["feature_registry_version"]),
        "parameters": _json(definition["parameters"]),
        "publication_eligible": bool(definition["publication_eligible"]),
        "meaning": str(definition["meaning"]),
        "active": bool(definition["active"]),
        "components": [dict(item) for item in components],
        "features": [
            {**dict(item), "transformation_parameters": _json(item["transformation_parameters"])}
            for item in features
        ],
        "eligibility": [
            {**dict(item), "feature_codes": _json(item["feature_codes"])} for item in eligibility
        ],
    }
