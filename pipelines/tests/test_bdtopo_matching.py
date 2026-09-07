"""Invariants de l'appariement DS-04 — B2b.

Ces tests portent sur le SQL de l'importeur, faute de banc PostgreSQL dans `make check`,
selon la convention deja suivie par `test_ban_parcel_relations.py`. La verification sur
donnees reelles est consignee dans
[`spatial-sources-audit.md`](../../docs/data/spatial-sources-audit.md).

Ce qui est verifie ici tient a quatre interdits du ticket : ne pas inventer d'emprise, ne
pas remplacer une geometrie RNB, ne pas creer d'entite canonique pour la voirie, et ne pas
inventer de seuil.
"""

import re
from pathlib import Path

IMPORTER = Path(__file__).parents[1] / "src" / "immo_pipelines" / "spatial" / "importer.py"


def bdtopo_importer_source() -> str:
    """Le corps de `BdtopoImporter` seul, borne a la classe suivante.

    Decouper jusqu'a la fin du fichier faisait entrer les importeurs ajoutes apres lui, dont
    le SQL rendait ces assertions ambigues.
    """
    source = IMPORTER.read_text(encoding="utf-8")
    start = source.index("class BdtopoImporter")
    remainder = source[start:]
    next_class = remainder.find("\nclass ", 1)
    return remainder if next_class == -1 else remainder[:next_class]


SQL_KEYWORDS = ("INSERT INTO", "UPDATE ", "SELECT ", "CREATE ", "COPY ", "WITH ")


def statement_blocks() -> list[str]:
    """Les instructions SQL de l'importeur, docstrings exclues.

    Les chaines triple-quote du module sont soit du SQL, soit de la prose — et la prose cite
    volontairement des identifiants que l'importeur n'ecrit pas. Les confondre inverserait le
    sens de ces tests.
    """
    blocks = re.findall(r'"""([\s\S]*?)"""', bdtopo_importer_source())
    return [block for block in blocks if any(keyword in block for keyword in SQL_KEYWORDS)]


def sql_of(*fragments: str) -> str:
    """L'unique instruction SQL contenant tous les fragments donnes.

    Les fragments portent sur le SQL seul : la prose de l'importeur cite volontairement des
    identifiants qu'il n'ecrit pas, et la confondre avec du code rendrait ces tests faux.
    """
    matching = [
        block for block in statement_blocks() if all(fragment in block for fragment in fragments)
    ]
    assert len(matching) == 1, (
        f"expected exactly one statement containing {fragments!r}, found {len(matching)}"
    )
    return matching[0]


def all_sql() -> str:
    return "\n".join(statement_blocks())


def test_no_footprint_is_ever_written_onto_a_canonical_building() -> None:
    """Le RNB garde l'identite batiment : aucune emprise BD TOPO ne l'ecrase.

    C'est ce qui protege les 3 864 batiments RNB ponctuels d'heriter d'une emprise, et toute
    geometrie RNB d'etre remplacee par une geometrie divergente.
    """
    sql = all_sql()
    assert "UPDATE reference.building" not in sql
    assert "INSERT INTO reference.building" not in sql
    assert "reference.building.geom" not in sql
    # `reference.building` n'est lu qu'en jointure, pour verifier que l'entite existe.
    assert "SET geom" not in sql


def test_the_road_layer_creates_no_canonical_entity() -> None:
    """La voirie est une couche de contexte : elle sert un calcul, pas une identite."""
    road_sql = sql_of("INSERT INTO observation.road_segment")
    assert "reference.building" not in road_sql
    assert "reference.property_unit" not in road_sql
    assert "meta.entity_source_observation" not in road_sql
    assert "meta.entity_source_identifier" not in road_sql

    # La voirie n'apparait dans aucune table d'entites canoniques.
    assert all_sql().count("INSERT INTO observation.road_segment") == 1


def test_an_observation_is_inserted_whether_or_not_it_matches() -> None:
    """Un batiment BD TOPO sans correspondance RNB reste une observation conservee.

    L'insertion des observations ne joint ni `reference.building` ni la table de liens : un
    batiment que le RNB ne connait pas est donc conserve, et son absence de rattachement se
    lit a l'absence de ligne de lien — la quatrieme classe, distincte d'un rejet.
    """
    observation_sql = sql_of("INSERT INTO meta.entity_source_observation")
    assert "reference.building" not in observation_sql
    assert "entity_observation_link" not in observation_sql
    assert "FROM bdtopo_building_stage WHERE NOT is_quarantined" in observation_sql


def test_geometry_alone_never_asserts_a_certain_attachment() -> None:
    """Sans seuil calibre, l'intersection ne peut pas affirmer un rattachement."""
    spatial_sql = sql_of("'spatial_intersection'")
    assert "'ambiguous'" in spatial_sql
    assert "'certain'" not in spatial_sql
    assert "'threshold_calibrated', false" in spatial_sql
    # Le recouvrement mesure est conserve comme preuve, pas comme decision.
    assert "overlap_ratio" in spatial_sql


def test_proximity_is_not_executed_because_it_would_require_an_invented_threshold() -> None:
    """La proximite exige un seuil de distance pour produire le moindre candidat."""
    sql = all_sql()
    assert "'proximity'" not in sql
    assert "ST_DWithin" not in sql
    assert "ST_Distance" not in sql


def test_several_declared_rnb_buildings_make_the_attachment_ambiguous() -> None:
    """Une emprise couvrant plusieurs batiments RNB est ambigue par construction."""
    identifier_sql = sql_of("'official_identifier'")
    assert "identifier_count = 1 THEN 'certain'" in identifier_sql
    assert "ELSE 'ambiguous'" in identifier_sql


def test_the_explicit_link_table_only_serves_where_the_identifier_is_absent() -> None:
    """Sinon elle repeterait le meme couple sous une methode moins directe."""
    relation_sql = sql_of("'source_relation'")
    assert "jsonb_array_length(stage.rnb_identifiers) = 0" in relation_sql


def test_only_a_single_certain_link_produces_an_external_identifier() -> None:
    """Un rattachement ambigu ne doit pas se transformer en identifiant externe."""
    identifier_sql = sql_of("INSERT INTO meta.entity_source_identifier")
    assert "link.decision = 'certain'" in identifier_sql
    assert "HAVING count(*) = 1" in identifier_sql
    # Le RNB reste l'identite preferee.
    assert "false" in identifier_sql.split("is_preferred")[-1] or "'DS-04'" in identifier_sql


def test_every_insert_tolerates_a_reimport() -> None:
    """Reimport stable : aucune instruction ne peut dupliquer une ligne."""
    for fragment in (
        "INSERT INTO meta.entity_source_observation",
        "INSERT INTO observation.road_segment",
        "INSERT INTO meta.geometry_quarantine",
        "'official_identifier'",
        "'source_relation'",
        "'spatial_intersection'",
    ):
        statement = sql_of(fragment)
        assert "ON CONFLICT" in statement, f"{fragment} has no conflict clause"


def test_quarantined_records_are_retained_with_their_motive() -> None:
    quarantine_sql = sql_of("INSERT INTO meta.geometry_quarantine")
    assert "reason_code" in quarantine_sql
    assert "reason_detail" in quarantine_sql
    assert "WHERE is_quarantined" in quarantine_sql


def test_the_commune_is_resolved_against_the_active_referential_not_the_file_name() -> None:
    """L'export du 35 deborde sur 143 communes : le nom du fichier ne dit pas le perimetre."""
    metric_sql = sql_of("INSERT INTO meta.entity_match_metric")
    assert "ST_Covers" in metric_sql
    assert "area_type = 'commune'" in metric_sql


def test_the_metric_distribution_has_four_classes() -> None:
    """Jamais trois : non apparie n'est pas rejete."""
    metric_sql = sql_of("INSERT INTO meta.entity_match_metric")
    for column in (
        "certain_count",
        "ambiguous_count",
        "rejected_count",
        "unmatched_count",
    ):
        assert column in metric_sql
