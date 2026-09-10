"""Ce qui sort vers le relecteur, et ce qui n'en sort pas — B4.

`_blind_record` est une liste blanche, pas une projection de la ligne SQL. La requête lit
`matching_stratum` — elle en a besoin pour formuler la question — mais la strate d'appariement
**est** la classe de confiance du moteur : la montrer ferait mesurer à la revue l'accord avec le
moteur au lieu de l'exactitude.

D'où la contrainte sur la référence affichée. `drawn_rank` n'est unique que dans sa strate
d'appariement : « Cas 3 · littoral » désignait trois cas distincts, et les signalements de la
revue du 10 septembre 2026 ne se rattachent plus à un cas précis. La compléter par la strate
réglerait l'unicité en révélant justement ce qu'il faut taire, donc la référence publique est
tirée d'un hachage de l'identifiant.
"""

import pytest

from immo.review import BLIND_CASE_SELECT, _blind_record

# Tout ce que la requête sait et que le relecteur ne doit pas apprendre avant son verdict.
FORBIDDEN = ("matching_stratum", "decision", "confidence", "rationale", "evidence")

ROW = {
    "id": 42,
    "sample_id": "b4-2026-09-08",
    "territorial_stratum": "littoral",
    "matching_stratum": "certain_source_relation",
    "commune_code": "35093",
    "commune_name": "DINARD",
    "drawn_rank": 3,
    "case_ref": 167,
    "left_label": "BATIMENT0000000297021878",
    "left_id": "BATIMENT0000000297021878",
    "left_kind": "building",
    "left_area_m2": 91,
    "left_geojson": '{"type":"Polygon","coordinates":[]}',
    "right_label": "building:rnb:252GG72M5784",
    "right_id": "building:rnb:252GG72M5784",
    "right_kind": "building",
    "right_area_m2": 91,
    "right_geojson": '{"type":"Polygon","coordinates":[]}',
    "left_on_right_ratio": 1.0,
    "longitude": -2.0688,
    "latitude": 48.6297,
}


@pytest.mark.parametrize("field", FORBIDDEN)
def test_le_jugement_du_moteur_ne_sort_pas(field: str) -> None:
    assert field not in _blind_record(ROW), (
        f"`{field}` atteint le relecteur avant son verdict : la revue mesurerait l'accord avec "
        "le moteur, pas l'exactitude."
    )


def test_une_reference_unique_est_exposee() -> None:
    record = _blind_record(ROW)
    assert record["case_ref"] == 167
    assert record["drawn_rank"] == 3, "le rang de tirage reste utile au dépouillement"


def test_la_reference_ne_derive_pas_du_rang_de_tirage() -> None:
    """Une numérotation ordonnée par strate rendrait la strate lisible dans le numéro."""
    assert "dense_rank() OVER (ORDER BY md5(" in BLIND_CASE_SELECT, (
        "La référence publique doit venir d'un hachage de l'identifiant. Toute numérotation "
        "ordonnée par `drawn_rank` ou par strate laisserait deviner la classe de confiance."
    )
    numbering = BLIND_CASE_SELECT.split("AS case_ref")[0].rsplit("(SELECT numbered.reference", 1)[1]
    for leak in ("matching_stratum", "drawn_rank"):
        assert leak not in numbering, f"la numérotation publique s'appuie sur `{leak}`"
