"""Revue manuelle stratifiée des appariements — B4.

Une exigence gouverne tout ce module : **le relecteur ne voit pas le jugement du moteur avant
de rendre le sien.** Ni la décision, ni la confiance, ni la justification ne sortent d'ici tant
qu'un verdict n'a pas été enregistré. Sans cela la revue mesurerait l'accord avec le moteur,
et un accord n'est pas une exactitude.

Ce qui est exposé à la place : les identifiants source des deux côtés, la géométrie, la commune.
De quoi aller regarder la donnée d'origine — ce que le protocole demande — sans rien apprendre
de ce que le moteur en a conclu.
"""

from typing import Any

from sqlalchemy import text

from immo.database import get_engine

# Ce que le relecteur peut voir avant son verdict. Toute colonne ajoutée ici doit être neutre :
# elle décrit le cas, jamais la conclusion.
BLIND_CASE_SELECT = """
    SELECT review_case.id,
           review_case.sample_id,
           review_case.territorial_stratum,
           review_case.commune_code,
           commune.name AS commune_name,
           review_case.drawn_rank,
           -- Le côté gauche : l'observation ou l'entité qui porte la relation.
           coalesce(
               source_observation.source_identifier,
               matched.left_entity_id
           ) AS left_label,
           coalesce(
               source_observation.source_entity_type,
               matched.left_entity_type
           ) AS left_kind,
           -- Le côté droit : l'entité canonique visée.
           coalesce(link.entity_id, matched.right_entity_id) AS right_label,
           coalesce(link.entity_type, matched.right_entity_type) AS right_kind,
           ST_X(ST_Transform(ST_PointOnSurface(
               coalesce(source_observation.geometry, address.geom, parcel_geometry.geom)
           ), 4326)) AS longitude,
           ST_Y(ST_Transform(ST_PointOnSurface(
               coalesce(source_observation.geometry, address.geom, parcel_geometry.geom)
           ), 4326)) AS latitude,
           EXISTS (
               SELECT 1 FROM meta.matching_review_verdict AS recorded
                WHERE recorded.case_id = review_case.id
           ) AS already_judged
      FROM meta.matching_review_case AS review_case
      LEFT JOIN meta.entity_match AS matched ON matched.id = review_case.match_id
      LEFT JOIN meta.entity_observation_link AS link
             ON link.id = review_case.observation_link_id
      LEFT JOIN meta.entity_source_observation AS source_observation
             ON source_observation.id = link.observation_id
      LEFT JOIN reference.address AS address
             ON address.id = matched.left_entity_id AND matched.left_entity_type = 'address'
      LEFT JOIN reference.parcel AS parcel
             ON parcel.id = matched.right_entity_id AND matched.right_entity_type = 'parcel'
      LEFT JOIN reference.parcel_geometry AS parcel_geometry ON parcel_geometry.id = parcel.id
      LEFT JOIN reference.area AS commune
             ON commune.area_type = 'commune' AND commune.code = review_case.commune_code
"""


def _blind_record(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "sample_id": str(row["sample_id"]),
        "territorial_stratum": str(row["territorial_stratum"]),
        "commune_code": str(row["commune_code"]) if row["commune_code"] else None,
        "commune_name": str(row["commune_name"]) if row["commune_name"] else None,
        "drawn_rank": int(row["drawn_rank"]),
        "left_label": str(row["left_label"]) if row["left_label"] else None,
        "left_kind": str(row["left_kind"]) if row["left_kind"] else None,
        "right_label": str(row["right_label"]) if row["right_label"] else None,
        "right_kind": str(row["right_kind"]) if row["right_kind"] else None,
        "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
        "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
    }


def review_progress(sample_id: str) -> dict[str, Any] | None:
    """Avancement du lot, sans rien dire des verdicts eux-mêmes.

    Le compte des verdicts rendus est neutre : il ne révèle pas leur contenu, donc il ne
    contamine pas le jugement suivant.
    """
    with get_engine().connect() as connection:
        sample = (
            connection.execute(
                text(
                    """
                SELECT id, seed, target_size, size_rationale, protocol_document, drawn_at
                  FROM meta.matching_review_sample WHERE id = :sample_id
                """
                ),
                {"sample_id": sample_id},
            )
            .mappings()
            .one_or_none()
        )
        if sample is None:
            return None
        counts = (
            connection.execute(
                text(
                    """
                SELECT count(*) AS total,
                       count(*) FILTER (
                           WHERE EXISTS (
                               SELECT 1 FROM meta.matching_review_verdict AS verdict
                                WHERE verdict.case_id = review_case.id
                           )
                       ) AS judged
                  FROM meta.matching_review_case AS review_case
                 WHERE review_case.sample_id = :sample_id
                """
                ),
                {"sample_id": sample_id},
            )
            .mappings()
            .one()
        )
    return {
        "sample_id": str(sample["id"]),
        "seed": int(sample["seed"]),
        "target_size": int(sample["target_size"]),
        "size_rationale": str(sample["size_rationale"]),
        "protocol_document": str(sample["protocol_document"]),
        "drawn_at": sample["drawn_at"].isoformat(),
        "total_cases": int(counts["total"]),
        "judged_cases": int(counts["judged"]),
    }


def next_blind_case(sample_id: str) -> dict[str, Any] | None:
    """Le prochain cas non encore jugé, dans l'ordre du tirage."""
    statement = text(
        BLIND_CASE_SELECT
        + """
         WHERE review_case.sample_id = :sample_id
           AND NOT EXISTS (
               SELECT 1 FROM meta.matching_review_verdict AS verdict
                WHERE verdict.case_id = review_case.id
           )
         ORDER BY review_case.matching_stratum, review_case.drawn_rank
         LIMIT 1
        """
    )
    with get_engine().connect() as connection:
        row = connection.execute(statement, {"sample_id": sample_id}).mappings().one_or_none()
    return _blind_record(row) if row is not None else None


def record_verdict(
    *,
    case_id: int,
    verdict: str,
    reviewer: str,
    rationale: str,
    evidence_consulted: str,
) -> dict[str, Any]:
    """Enregistrer un verdict. Append-only : un désaccord ultérieur s'ajoute, il n'écrase pas."""
    if verdict not in {"correct", "incorrect", "undecidable"}:
        raise ValueError(f"Unsupported verdict {verdict}")
    with get_engine().begin() as connection:
        row = (
            connection.execute(
                text(
                    """
                INSERT INTO meta.matching_review_verdict (
                    case_id, verdict, reviewer, rationale, evidence_consulted
                ) VALUES (
                    :case_id, :verdict, :reviewer, :rationale, :evidence_consulted
                )
                RETURNING id, case_id, verdict, recorded_at
                """
                ),
                {
                    "case_id": case_id,
                    "verdict": verdict,
                    "reviewer": reviewer,
                    "rationale": rationale,
                    "evidence_consulted": evidence_consulted,
                },
            )
            .mappings()
            .one()
        )
    return {
        "id": int(row["id"]),
        "case_id": int(row["case_id"]),
        "verdict": str(row["verdict"]),
        "recorded_at": row["recorded_at"].isoformat(),
    }


def review_results(sample_id: str) -> list[dict[str, Any]]:
    """Taux d'exactitude par strate.

    Un cas indécidable n'est **jamais** compté comme correct : il a sa propre colonne, et le
    taux d'exactitude se calcule sur les seuls cas tranchés. Le dénominateur est donc explicite,
    et un lot majoritairement indécidable se lit comme tel plutôt que comme un bon score.

    Seul le **dernier** verdict de chaque cas compte, mais les précédents restent en base : un
    désaccord entre relecteurs est conservé, pas arbitré en silence.
    """
    statement = text(
        """
        WITH latest AS (
            SELECT DISTINCT ON (verdict.case_id)
                   verdict.case_id, verdict.verdict
              FROM meta.matching_review_verdict AS verdict
              JOIN meta.matching_review_case AS review_case
                ON review_case.id = verdict.case_id
             WHERE review_case.sample_id = :sample_id
             ORDER BY verdict.case_id, verdict.recorded_at DESC, verdict.id DESC
        )
        SELECT review_case.matching_stratum, review_case.territorial_stratum,
               count(*) AS drawn,
               count(latest.case_id) AS judged,
               count(*) FILTER (WHERE latest.verdict = 'correct') AS correct,
               count(*) FILTER (WHERE latest.verdict = 'incorrect') AS incorrect,
               count(*) FILTER (WHERE latest.verdict = 'undecidable') AS undecidable,
               count(*) FILTER (
                   WHERE latest.verdict IN ('correct', 'incorrect')
               ) AS decided
          FROM meta.matching_review_case AS review_case
          LEFT JOIN latest ON latest.case_id = review_case.id
         WHERE review_case.sample_id = :sample_id
         GROUP BY review_case.matching_stratum, review_case.territorial_stratum
         ORDER BY review_case.matching_stratum, review_case.territorial_stratum
        """
    )
    with get_engine().connect() as connection:
        rows = list(connection.execute(statement, {"sample_id": sample_id}).mappings())
    results: list[dict[str, Any]] = []
    for row in rows:
        decided = int(row["decided"])
        results.append(
            {
                "matching_stratum": str(row["matching_stratum"]),
                "territorial_stratum": str(row["territorial_stratum"]),
                "drawn": int(row["drawn"]),
                "judged": int(row["judged"]),
                "correct": int(row["correct"]),
                "incorrect": int(row["incorrect"]),
                "undecidable": int(row["undecidable"]),
                # Sur les seuls cas tranchés, et nul si aucun ne l'est.
                "accuracy": (int(row["correct"]) / decided) if decided else None,
            }
        )
    return results
