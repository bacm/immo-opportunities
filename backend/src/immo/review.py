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
           review_case.matching_stratum,
           review_case.commune_code,
           commune.name AS commune_name,
           review_case.drawn_rank,
           -- Une reference unique **et neutre** pour designer un cas a l'oral et a l'ecrit.
           --
           -- `drawn_rank` ne l'est pas : il est unique dans sa strate d'appariement, pas dans
           -- l'echantillon. « Cas 3 · littoral » designe trois cas differents, et la revue du
           -- 10 septembre a produit plusieurs signalements — « le cas 47 », « le cas 32 » —
           -- qu'on ne peut plus rattacher a un cas precis.
           --
           -- Le completer par la strate d'appariement reglerait l'unicite en revelant la
           -- classe de confiance du moteur, ce que le protocole interdit. La numerotation est
           -- donc tiree d'un hachage de l'identifiant : unique, stable, reproductible, et
           -- sans ordre lisible qui trahirait la strate.
           (SELECT numbered.reference
              FROM (SELECT sibling.id,
                           dense_rank() OVER (ORDER BY md5(sibling.id::text)) AS reference
                      FROM meta.matching_review_case AS sibling
                     WHERE sibling.sample_id = review_case.sample_id) AS numbered
             WHERE numbered.id = review_case.id) AS case_ref,
           -- Un libelle lisible par un humain, jamais l'identifiant technique seul :
           -- « 7 Avenue Georges Pian 35800 Dinard » se juge, `address:ban:35093_0850_00007`
           -- ne se juge pas.
           coalesce(
               left_address.display_label,
               left_building.id,
               source_observation.source_identifier,
               matched.left_entity_id
           ) AS left_label,
           coalesce(source_observation.source_identifier, matched.left_entity_id) AS left_id,
           coalesce(
               source_observation.source_entity_type,
               matched.left_entity_type
           ) AS left_kind,
           round(ST_Area(coalesce(
               source_observation.geometry, left_building.geom
           ))::numeric) AS left_area_m2,
           coalesce(
               right_parcel.cadastral_id,
               right_building.id,
               link.entity_id,
               matched.right_entity_id
           ) AS right_label,
           coalesce(link.entity_id, matched.right_entity_id) AS right_id,
           coalesce(link.entity_type, matched.right_entity_type) AS right_kind,
           round(ST_Area(coalesce(
               right_parcel_geometry.geom, right_building.geom
           ))::numeric) AS right_area_m2,
           -- Les deux geometries, en WGS84. Montrer OU sont les objets n'est pas montrer ce
           -- que le moteur en a conclu : c'est la donnee, et sans elle la question posee est
           -- litteralement sans reponse.
           ST_AsGeoJSON(ST_Transform(coalesce(
               source_observation.geometry, left_building.geom, left_address.geom
           ), 4326)) AS left_geojson,
           ST_AsGeoJSON(ST_Transform(coalesce(
               right_parcel_geometry.geom, right_building.geom
           ), 4326)) AS right_geojson,
           -- La part de l'objet de gauche qui tombe sur celui de droite, recalculee ici a
           -- partir des deux geometries.
           --
           -- C'est une propriete geometrique que le relecteur pourrait mesurer lui-meme sur la
           -- carte, au meme titre que les surfaces deja affichees — pas la decision du moteur.
           -- La nuance compte : le moteur a bien utilise un recouvrement pour decider, mais ce
           -- qui lui est interdit de montrer, c'est sa conclusion, pas le fait mesure.
           --
           -- Sans ce chiffre, un batiment qui touche une parcelle a 3 % se juge a l'oeil sur
           -- deux formes presque superposees a l'ecran. BUG-09 montre que 32 % des relations
           -- sont dans ce cas.
           --
           -- Vaut aussi pour une paire batiment <-> batiment : deux emprises identiques se
           -- superposent exactement a l'ecran, et le relecteur ne voit qu'une seule forme
           -- sans savoir si la seconde est la ou absente. Le chiffre le lui dit.
           round(
               (ST_Area(ST_Intersection(
                    coalesce(source_observation.geometry, left_building.geom),
                    coalesce(right_parcel_geometry.geom, right_building.geom)
                ))
                / nullif(ST_Area(coalesce(
                    source_observation.geometry, left_building.geom
                )), 0))::numeric, 4
           ) AS left_on_right_ratio,
           ST_X(ST_Transform(ST_PointOnSurface(coalesce(
               right_parcel_geometry.geom, right_building.geom,
               source_observation.geometry, left_address.geom
           )), 4326)) AS longitude,
           ST_Y(ST_Transform(ST_PointOnSurface(coalesce(
               right_parcel_geometry.geom, right_building.geom,
               source_observation.geometry, left_address.geom
           )), 4326)) AS latitude
      FROM meta.matching_review_case AS review_case
      LEFT JOIN meta.entity_match AS matched ON matched.id = review_case.match_id
      LEFT JOIN meta.entity_observation_link AS link
             ON link.id = review_case.observation_link_id
      LEFT JOIN meta.entity_source_observation AS source_observation
             ON source_observation.id = link.observation_id
      LEFT JOIN reference.address AS left_address
             ON left_address.id = matched.left_entity_id
            AND matched.left_entity_type = 'address'
      LEFT JOIN reference.building AS left_building
             ON left_building.id = matched.left_entity_id
            AND matched.left_entity_type = 'building'
      LEFT JOIN reference.parcel AS right_parcel
             ON right_parcel.id = coalesce(link.entity_id, matched.right_entity_id)
      LEFT JOIN reference.parcel_geometry AS right_parcel_geometry
             ON right_parcel_geometry.id = right_parcel.id
      LEFT JOIN reference.building AS right_building
             ON right_building.id = coalesce(link.entity_id, matched.right_entity_id)
      LEFT JOIN reference.area AS commune
             ON commune.area_type = 'commune' AND commune.code = review_case.commune_code
"""


# La question posee, mot pour mot, selon la strate. Deux identifiants cote a cote et une carte
# se pretent a toutes les interpretations : un relecteur qui repond a la mauvaise question
# produit des verdicts pires qu'aucun verdict, parce qu'ils ont l'air valides.
STRATUM_QUESTIONS: dict[str, str] = {
    "certain_official_identifier": (
        "Ce bâtiment BD TOPO et ce bâtiment RNB sont-ils le même bâtiment ?"
    ),
    "certain_source_relation": "Ces deux objets se correspondent-ils sur le terrain ?",
    "ambiguous": "Ces deux objets se correspondent-ils sur le terrain ?",
}

OUT_OF_SCOPE = (
    "Vous ne jugez que l'identité : ces deux objets désignent-ils la même chose ? "
    "Ni l'accès à la rue, ni l'état du bâti, ni la qualité de la donnée source n'entrent "
    "dans ce verdict."
)


def _question(stratum: str, left_kind: str | None, right_kind: str | None) -> str:
    """Formuler la question dans les termes des objets réellement comparés."""
    if left_kind == "address" and right_kind == "parcel":
        return "Cette adresse est-elle bien l'adresse de cette parcelle ?"
    if left_kind == "building" and right_kind == "parcel":
        return "Ce bâtiment est-il bien situé sur cette parcelle ?"
    if right_kind == "building":
        return "Ces deux objets désignent-ils le même bâtiment ?"
    return STRATUM_QUESTIONS.get(stratum, "Ces deux objets se correspondent-ils sur le terrain ?")


def _blind_record(row: Any) -> dict[str, Any]:
    left_kind = str(row["left_kind"]) if row["left_kind"] else None
    right_kind = str(row["right_kind"]) if row["right_kind"] else None
    return {
        "id": int(row["id"]),
        "sample_id": str(row["sample_id"]),
        "territorial_stratum": str(row["territorial_stratum"]),
        "commune_code": str(row["commune_code"]) if row["commune_code"] else None,
        "commune_name": str(row["commune_name"]) if row["commune_name"] else None,
        "drawn_rank": int(row["drawn_rank"]),
        "case_ref": int(row["case_ref"]),
        "question": _question(str(row["matching_stratum"]), left_kind, right_kind),
        "out_of_scope": OUT_OF_SCOPE,
        "left_label": str(row["left_label"]) if row["left_label"] else None,
        "left_id": str(row["left_id"]) if row["left_id"] else None,
        "left_kind": left_kind,
        "left_area_m2": float(row["left_area_m2"]) if row["left_area_m2"] is not None else None,
        "left_geojson": str(row["left_geojson"]) if row["left_geojson"] else None,
        "right_label": str(row["right_label"]) if row["right_label"] else None,
        "right_id": str(row["right_id"]) if row["right_id"] else None,
        "right_kind": right_kind,
        "right_area_m2": float(row["right_area_m2"]) if row["right_area_m2"] is not None else None,
        "right_geojson": str(row["right_geojson"]) if row["right_geojson"] else None,
        "left_on_right_ratio": (
            float(row["left_on_right_ratio"]) if row["left_on_right_ratio"] is not None else None
        ),
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
    # Ordre entrelace : le 1er cas de chacune des 12 cellules, puis le 2e, et ainsi de suite.
    # L'ordre naturel du tirage aurait fait juger 60 cas ambigus littoraux avant le premier
    # certain — or ce sont les certains qui decident de la publication, et un probleme de
    # methode se serait vu au soixantieme cas au lieu du dixieme.
    #
    # La position est calculee depuis `drawn_rank`, fige au tirage, et non depuis un rang
    # recalcule sur les cas restants : un rang recalcule redonnerait la premiere place a la
    # meme cellule apres chaque verdict, et n'entrelacerait donc rien. Le tirage attribue 15
    # rangs par territoire dans chaque strate, d'ou le modulo.
    statement = text(
        BLIND_CASE_SELECT
        + """
         WHERE review_case.sample_id = :sample_id
           AND (
               -- Jamais juge.
               NOT EXISTS (
                   SELECT 1 FROM meta.matching_review_verdict AS verdict
                    WHERE verdict.case_id = review_case.id
               )
               -- Ou rappele depuis, et pas encore rejuge : un rappel redonne le cas a juger
               -- sans effacer le verdict precedent, qui reste visible au depouillement.
               OR EXISTS (
                   SELECT 1 FROM meta.matching_review_recall AS recall
                    WHERE recall.case_id = review_case.id
                      AND NOT EXISTS (
                          SELECT 1 FROM meta.matching_review_verdict AS later
                           WHERE later.case_id = review_case.id
                             AND later.recorded_at > recall.recalled_at
                      )
               )
           )
         ORDER BY
                  -- Les cas rappeles d'abord : ils bloquent le depouillement de leur strate,
                  -- et les rendre en fin de file les ferait juger apres les 160 autres.
                  EXISTS (
                      SELECT 1 FROM meta.matching_review_recall AS recall
                       WHERE recall.case_id = review_case.id
                  ) DESC,
                  (review_case.drawn_rank - 1) % 15,
                  review_case.matching_stratum,
                  review_case.territorial_stratum
         LIMIT 1
        """
    )
    with get_engine().connect() as connection:
        row = connection.execute(statement, {"sample_id": sample_id}).mappings().one_or_none()
    return _blind_record(row) if row is not None else None


def case_context(case_id: int) -> dict[str, Any]:
    """Le voisinage du cas, pour lever les doutes que la seule paire ne permet pas de trancher.

    Deux doutes sont revenus dans la revue réelle du 9 septembre 2026, et la base savait y
    répondre alors que l'écran ne le montrait pas :

    - « c'est peut-être un *bis* » — les adresses au même numéro dans la même voie, ou leur
      **absence explicite**, qui est l'information utile ;
    - « cette adresse couvre plusieurs parcelles » — les autres parcelles rattachées à la même
      adresse.

    Aucune décision du moteur n'est exposée ici : savoir qu'un objet fait partie d'un ensemble
    n'est pas savoir ce que le moteur a conclu de chacun.
    """
    # Un batiment BD TOPO n'a ni adresse ni libelle humain : son `cleabs` est introuvable dans
    # l'application, et le juger sans repere est impossible. La revue reelle du 10 septembre
    # 2026 l'a montre des le premier cas de cette strate — verdict `undecidable`, motif
    # « je n'ai pas d'adresse et le code de l'objet de gauche est introuvable sur l'app ».
    #
    # Les adresses proches ne sont **pas** un appariement : aucune n'est declaree correspondre
    # a ce batiment. Ce sont des reperes, au meme titre qu'un nom de rue sur une carte.
    nearby_statement = text(
        """
        WITH target AS (
            SELECT coalesce(
                       source_observation.geometry, building.geom, address.geom
                   ) AS geometry
              FROM meta.matching_review_case AS review_case
              LEFT JOIN meta.entity_observation_link AS link
                     ON link.id = review_case.observation_link_id
              LEFT JOIN meta.entity_source_observation AS source_observation
                     ON source_observation.id = link.observation_id
              LEFT JOIN meta.entity_match AS matched ON matched.id = review_case.match_id
              LEFT JOIN reference.building AS building
                     ON building.id = matched.left_entity_id
              LEFT JOIN reference.address AS address
                     ON address.id = matched.left_entity_id
             WHERE review_case.id = :case_id
        )
        SELECT address.display_label,
               round(ST_Distance(address.geom, target.geometry)::numeric) AS distance_m
          FROM target
          JOIN reference.address AS address
            ON target.geometry IS NOT NULL
           AND ST_DWithin(address.geom, target.geometry, 80)
         ORDER BY ST_Distance(address.geom, target.geometry)
         LIMIT 6
        """
    )
    with get_engine().connect() as connection:
        nearby = list(connection.execute(nearby_statement, {"case_id": case_id}).mappings())
        siblings = list(
            connection.execute(
                text(
                    """
                    WITH target AS (
                        SELECT address.commune_code, address.street_name,
                               address.house_number, address.id
                          FROM meta.matching_review_case AS review_case
                          JOIN meta.entity_match AS matched
                            ON matched.id = review_case.match_id
                          JOIN reference.address AS address
                            ON address.id = matched.left_entity_id
                         WHERE review_case.id = :case_id
                    )
                    SELECT address.display_label,
                           coalesce(address.repetition_index, '') AS repetition_index,
                           address.id = target.id AS is_case
                      FROM reference.address AS address, target
                     WHERE address.commune_code = target.commune_code
                       AND address.street_name IS NOT DISTINCT FROM target.street_name
                       AND address.house_number IS NOT DISTINCT FROM target.house_number
                     ORDER BY coalesce(address.repetition_index, '')
                     LIMIT 12
                    """
                ),
                {"case_id": case_id},
            ).mappings()
        )
        related = list(
            connection.execute(
                text(
                    """
                    WITH target AS (
                        SELECT matched.left_entity_id AS address_id,
                               matched.right_entity_id AS parcel_id
                          FROM meta.matching_review_case AS review_case
                          JOIN meta.entity_match AS matched
                            ON matched.id = review_case.match_id
                         WHERE review_case.id = :case_id
                    )
                    SELECT parcel.cadastral_id,
                           round(ST_Area(parcel_geometry.geom)::numeric) AS area_m2,
                           sibling.right_entity_id = target.parcel_id AS is_case
                      FROM target
                      JOIN meta.entity_match AS sibling
                        ON sibling.left_entity_id = target.address_id
                       AND sibling.algorithm_code = 'ban-cad-parcelles'
                      JOIN reference.parcel AS parcel ON parcel.id = sibling.right_entity_id
                      JOIN reference.parcel_geometry AS parcel_geometry
                        ON parcel_geometry.id = parcel.id
                     ORDER BY parcel.cadastral_id
                     LIMIT 12
                    """
                ),
                {"case_id": case_id},
            ).mappings()
        )
    return {
        "case_id": case_id,
        "nearby_addresses": [
            {
                "display_label": str(row["display_label"]),
                "distance_m": float(row["distance_m"]),
            }
            for row in nearby
        ],
        "sibling_addresses": [
            {
                "display_label": str(row["display_label"]),
                "repetition_index": str(row["repetition_index"]),
                "is_case": bool(row["is_case"]),
            }
            for row in siblings
        ],
        "related_parcels": [
            {
                "cadastral_id": str(row["cadastral_id"]),
                "area_m2": float(row["area_m2"]) if row["area_m2"] is not None else None,
                "is_case": bool(row["is_case"]),
            }
            for row in related
        ],
    }


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
               count(*) FILTER (
                   WHERE EXISTS (
                       SELECT 1 FROM meta.matching_review_recall AS recall
                        WHERE recall.case_id = review_case.id
                   )
               ) AS recalled,
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
                "recalled": int(row["recalled"]),
                "judged": int(row["judged"]),
                "correct": int(row["correct"]),
                "incorrect": int(row["incorrect"]),
                "undecidable": int(row["undecidable"]),
                # Sur les seuls cas tranchés, et nul si aucun ne l'est.
                "accuracy": (int(row["correct"]) / decided) if decided else None,
            }
        )
    return results
