"""Qualification des mutations DVF et allocation du prix — D1, H7.

Les lignes sont à la forme `geo-dvf`, celle que l'import d'archive produit aussi. Aucune ligne ne
vient d'une vente réelle identifiable : les identifiants sont fabriqués pour le test.
"""

from typing import Any

from immo_pipelines.market_data.dvf import DVF_TRANSFORMATION_VERSION, Mutation


def line(**overrides: str) -> dict[str, str]:
    row = {
        "id_mutation": "2024-1",
        "date_mutation": "2024-05-15",
        "nature_mutation": "Vente",
        "valeur_fonciere": "300000",
        "code_commune": "35000",
        "id_parcelle": "35000000AA0001",
        "type_local": "",
        "surface_reelle_bati": "",
        "nombre_pieces_principales": "",
        "lot1_numero": "",
        "surface_terrain": "",
        "nature_culture": "",
    }
    return row | overrides


def house(**overrides: str) -> dict[str, str]:
    return (
        line(
            type_local="Maison",
            surface_reelle_bati="110",
            nombre_pieces_principales="5",
            surface_terrain="400",
            nature_culture="sols",
        )
        | overrides
    )


def land(parcel: str, surface: str = "600", nature: str = "jardins") -> dict[str, str]:
    return line(id_parcelle=parcel, surface_terrain=surface, nature_culture=nature)


def priced(mutation: Mutation) -> list[dict[str, Any]]:
    return mutation.priced_lots() if mutation.complexity() is None else []


def test_une_maison_et_son_jardin_sur_deux_parcelles_gardent_leur_prix() -> None:
    """H7 : le cas qui ouvrait le ticket. Le prix va à la maison, le jardin venant avec."""
    mutation = Mutation([house(), land("35000000AA0002")])
    assert len(mutation.parcels) == 2
    assert mutation.complexity() is None
    lots = priced(mutation)
    assert [lot["type_local"] for lot in lots] == ["Maison"]


def test_une_maison_et_son_garage_restent_complexes_meme_sur_deux_parcelles() -> None:
    """Deux lots bâtis : le montant les couvre sans dire ce qui revient à chacun."""
    garage = line(
        id_parcelle="35000000AA0002",
        type_local="Dépendance",
        surface_reelle_bati="20",
    )
    assert Mutation([house(), garage]).complexity() == "multiple_priced_lots"
    # Le motif le plus précis gagne aussi sur une seule parcelle.
    same_parcel = Mutation([house(), garage | {"id_parcelle": "35000000AA0001"}])
    assert same_parcel.complexity() == "multiple_priced_lots"


def test_un_terrain_seul_sur_plusieurs_parcelles_reste_non_allouable() -> None:
    """Plusieurs parcelles de terrain : plusieurs lots chiffrables, aucun prix unitaire."""
    mutation = Mutation([land("35000000AA0001"), land("35000000AA0002", "900", "prés")])
    assert mutation.complexity() == "multiple_priced_lots"


def test_un_seul_lot_de_terrain_mesure_sur_plusieurs_parcelles_reste_multiple_parcels() -> None:
    """Le prix couvre une parcelle sans surface connue : il ne va pas au seul lot mesuré."""
    unmeasured = line(id_parcelle="35000000AA0002")
    mutation = Mutation([land("35000000AA0001"), unmeasured])
    assert mutation.complexity() == "multiple_parcels"


def test_un_prix_manquant_passe_avant_tout_autre_motif() -> None:
    mutation = Mutation(
        [house(valeur_fonciere=""), land("35000000AA0002", "600") | {"valeur_fonciere": ""}]
    )
    assert mutation.complexity() == "price_missing"
    assert mutation.price is None


def test_une_maison_sans_surface_batie_reste_sans_prix_unitaire() -> None:
    mutation = Mutation([house(surface_reelle_bati=""), land("35000000AA0002")])
    assert mutation.complexity() == "surface_missing"


def test_un_bien_decrit_deux_fois_ne_fait_pas_deux_lots() -> None:
    """Une ligne par nature de culture : la même maison répétée reste un lot (version 4)."""
    mutation = Mutation(
        [house(), house(surface_terrain="300", nature_culture="jardins"), land("35000000AA0002")]
    )
    assert mutation.complexity() is None


def test_la_version_de_transformation_porte_le_changement_de_regle() -> None:
    """Sans nouvelle version, le réimport garderait les lignes de la règle précédente (BUG-09)."""
    assert DVF_TRANSFORMATION_VERSION == "5"
