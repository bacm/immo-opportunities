"""Lire une archive CNIG malgré ses deux générations de norme — D2, DS-08.

Deux variantes coexistent dans les documents réels du 35, et un import qui n'accepterait qu'une
seule perdrait la moitié des documents :

- **la casse des champs** — le PLU communal `DU_35018` écrit `INSEE` et `IDURBA` en majuscules,
  le PLUi de Rennes Métropole en minuscules ;
- **le nom des fichiers** — `ZONE_URBA.shp` d'un côté, `243500139_zone_urba_20251218.shp` de
  l'autre.

Le premier piège a failli écarter silencieusement le PLUi de Rennes Métropole et ses 43 communes :
une lecture sensible à la casse renvoie une chaîne vide **sans lever d'erreur**, et le document
paraît ne couvrir aucune commune. Il n'a été vu que parce que le symptôme était invraisemblable.
Ces tests existent pour qu'on ne dépende plus de l'invraisemblance d'un symptôme.
"""

import io
import zipfile

from immo_pipelines.market_data.cnig import LAYERS, Feature, find_layers


def _feature(values: dict[str, object]) -> Feature:
    """Un enregistrement tel que `read_features` le produit.

    Noms de champs en minuscules, valeurs débarrassées du remplissage DBF.
    """
    attributes = {
        str(key).lower(): "" if value is None else str(value).strip()
        for key, value in values.items()
    }
    return Feature(attributes=attributes, geometry=None)


def _archive(names: list[str]) -> zipfile.ZipFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"")
    return zipfile.ZipFile(buffer)


def test_un_champ_se_lit_quelle_que_soit_sa_casse() -> None:
    """Le défaut qui a failli faire disparaître Rennes Métropole de l'import."""
    assert _feature({"INSEE": "35238"}).get("INSEE") == "35238"
    assert _feature({"insee": "35238"}).get("INSEE") == "35238"
    assert _feature({"Insee": "35238"}).get("insee") == "35238"


def test_un_champ_absent_donne_une_chaine_vide_et_non_une_erreur() -> None:
    """Une couche peut légitimement ne pas porter un champ optionnel de la norme."""
    assert _feature({"INSEE": "35238"}).get("SIREN") == ""
    assert _feature({"DATEFIN": None}).get("DATEFIN") == ""


def test_les_valeurs_sont_nettoyees() -> None:
    """Les attributs DBF sont à largeur fixe : ils arrivent complétés d'espaces."""
    assert _feature({"IDURBA": "  35018_20161215  "}).get("IDURBA") == "35018_20161215"


def test_les_deux_conventions_de_nommage_designent_la_meme_couche() -> None:
    ancienne = _archive([f"doc/{n}" for n in ("ZONE_URBA.shp", "ZONE_URBA.dbf", "ZONE_URBA.shx")])
    nouvelle = _archive(
        [
            f"doc/{n}"
            for n in (
                "243500139_zone_urba_20251218.shp",
                "243500139_zone_urba_20251218.dbf",
                "243500139_zone_urba_20251218.shx",
            )
        ]
    )
    for archive in (ancienne, nouvelle):
        layers = find_layers(archive)
        assert set(layers) == {"zone_urba"}
        assert layers["zone_urba"].has_geometry


def test_doc_urba_com_n_est_pas_capture_par_doc_urba() -> None:
    """`doc_urba` est un préfixe de `doc_urba_com` : l'ordre de reconnaissance décide."""
    layers = find_layers(
        _archive(["d/DOC_URBA.dbf", "d/DOC_URBA_COM.dbf", "d/DOC_URBA.shp", "d/DOC_URBA.shx"])
    )
    assert set(layers) == {"doc_urba", "doc_urba_com"}
    assert layers["doc_urba_com"].files[".dbf"] == "d/DOC_URBA_COM.dbf"
    assert layers["doc_urba"].files[".dbf"] == "d/DOC_URBA.dbf"


def test_les_pieces_ecrites_ne_sont_jamais_reconnues_comme_une_couche() -> None:
    """Le règlement et le PADD sont hors du périmètre de ce ticket, et le restent."""
    layers = find_layers(
        _archive(
            [
                "d/35018_reglement_20161215.pdf",
                "d/35018_padd_20161215.pdf",
                "d/Avertissement.txt",
                "d/ZONE_URBA.dbf",
            ]
        )
    )
    assert set(layers) == {"zone_urba"}


def test_une_couche_sans_geometrie_est_reconnue_comme_telle() -> None:
    """`DOC_URBA_COM` est une table d'association : un `.dbf` sans `.shp`."""
    layers = find_layers(_archive(["d/DOC_URBA_COM.dbf", "d/DOC_URBA_COM.cpg"]))
    assert layers["doc_urba_com"].has_geometry is False


def test_l_ordre_des_couches_place_le_plus_specifique_en_premier() -> None:
    """Un jour où une couche sera ajoutée, ce test dira si l'ordre reste correct."""
    for index, layer in enumerate(LAYERS):
        for other in LAYERS[index + 1 :]:
            assert not other.startswith(layer), (
                f"`{other}` vient après `{layer}` dont il dérive : il ne sera jamais reconnu."
            )


def test_aucune_extension_etrangere_n_entre() -> None:
    assert find_layers(_archive(["d/zone_urba.qpj", "d/zone_urba.sbn"])) == {}
