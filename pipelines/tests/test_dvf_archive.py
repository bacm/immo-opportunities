"""Le lecteur du format DGFiP brut — D8.

Les deux pièges de la reconstruction sont nommés dans le ticket : le préfixe de section absent et
la section sur un seul caractère. Ils sont silencieux — un identifiant mal rembourré ne lève rien,
il ne se rattache simplement à aucune parcelle.

La validation d'ensemble a été faite contre la vérité d'Etalab sur 2022, où les deux sources
existent : 78 448 lignes converties pour 78 448 publiées, et **42 990 identifiants de parcelle
coïncidant à l'ensemble près**, zéro d'un côté comme de l'autre. Elle n'est pas rejouable dans
`make check`, qui n'a ni réseau ni fichier de 600 Mo ; elle est consignée dans
`docs/data/dvf-quality-35.md`.
"""

import gzip
from pathlib import Path

from immo_pipelines.market_data.dvf_archive import (
    GEODVF_COLUMNS,
    cadastral_id,
    commune_code,
    convert,
    decimal,
    iso_date,
    mutation_key,
    price,
    read_department,
    to_geodvf,
)

ENTETE = (
    "Code service CH|Reference document|1 Articles CGI|2 Articles CGI|3 Articles CGI|"
    "4 Articles CGI|5 Articles CGI|No disposition|Date mutation|Nature mutation|Valeur fonciere|"
    "No voie|B/T/Q|Type de voie|Code voie|Voie|Code postal|Commune|Code departement|Code commune|"
    "Prefixe de section|Section|No plan|No Volume|1er lot|Surface Carrez du 1er lot|2eme lot|"
    "Surface Carrez du 2eme lot|3eme lot|Surface Carrez du 3eme lot|4eme lot|"
    "Surface Carrez du 4eme lot|5eme lot|Surface Carrez du 5eme lot|Nombre de lots|"
    "Code type local|Type local|Identifiant local|Surface reelle bati|Nombre pieces principales|"
    "Nature culture|Nature culture speciale|Surface terrain"
)


def ligne(**overrides: str) -> str:
    champs = {
        "No disposition": "1",
        "Date mutation": "05/03/2016",
        "Nature mutation": "Vente",
        "Valeur fonciere": "185000,00",
        "Code departement": "35",
        "Code commune": "051",
        "Prefixe de section": "",
        "Section": "AZ",
        "No plan": "323",
        "1er lot": "",
        "Type local": "Maison",
        "Surface reelle bati": "112",
        "Nombre pieces principales": "5",
        "Surface terrain": "608",
    }
    champs.update(overrides)
    colonnes = ENTETE.split("|")
    return "|".join(champs.get(nom, "") for nom in colonnes)


def brut(**overrides: str) -> dict[str, str]:
    import csv

    return next(csv.DictReader([ENTETE, ligne(**overrides)], delimiter="|"))


def test_un_prefixe_de_section_absent_vaut_zero_zero_zero() -> None:
    """Le cas courant : sans rembourrage, l'identifiant fait treize caractères et ne joint rien."""
    assert cadastral_id(brut(**{"Prefixe de section": ""})) == "35051000AZ0323"
    assert len(cadastral_id(brut()) or "") == 14


def test_un_prefixe_de_section_non_nul_est_conserve() -> None:
    assert cadastral_id(brut(**{"Prefixe de section": "302"})) == "35051302AZ0323"


def test_une_section_sur_un_caractere_est_cadree_a_droite_par_zero() -> None:
    """`A` s'écrit `0A` au cadastre — 130 229 parcelles du 35 sont dans ce cas."""
    assert cadastral_id(brut(Section="A")) == "350510000A0323"


def test_un_numero_de_plan_court_est_rembourre_a_quatre() -> None:
    assert cadastral_id(brut(**{"No plan": "7"})) == "35051000AZ0007"


def test_sans_section_ni_plan_l_identifiant_est_absent_jamais_tronque() -> None:
    """Une valeur manquante reste manquante : un identifiant partiel joindrait la mauvaise
    parcelle."""
    assert cadastral_id(brut(Section="")) is None
    assert cadastral_id(brut(**{"No plan": ""})) is None


def test_le_code_commune_concatene_departement_et_commune() -> None:
    assert commune_code(brut()) == "35051"
    assert commune_code(brut(**{"Code departement": "9", "Code commune": "7"})) == "09007"


def test_la_date_passe_en_iso_et_une_date_illisible_reste_vide() -> None:
    assert iso_date("05/03/2016") == "2016-03-05"
    assert iso_date("5/3/2016") == "2016-03-05"
    assert iso_date("") == ""
    assert iso_date("2016-03-05") == ""


def test_la_virgule_decimale_devient_un_point() -> None:
    assert decimal("185000,00") == "185000.00"
    assert decimal("") == ""


def test_la_cle_de_mutation_est_celle_calibree_contre_etalab() -> None:
    """Date, commune, valeur, disposition — écart mesuré de 0,13 % sur 2022."""
    assert mutation_key(brut()) == "05/03/2016:35051:185000,00:1"
    assert mutation_key(brut(**{"No disposition": "2"})) != mutation_key(brut())


def test_seules_les_colonnes_consommees_sont_ecrites() -> None:
    """Une colonne inutilisée donnerait l'illusion d'une donnée portée."""
    assert set(to_geodvf(brut())) == set(GEODVF_COLUMNS)


def test_un_prix_de_zero_est_une_absence_pas_un_prix() -> None:
    """La publication d'avril 2019 écrit `0,00` là où les récentes laissent vide."""
    assert price("0,00") == ""
    assert price("0") == ""
    assert price("") == ""
    assert price("185000,00") == "185000.00"
    assert to_geodvf(brut(**{"Valeur fonciere": "0,00"}))["valeur_fonciere"] == ""


def test_le_departement_filtre_un_fichier_national() -> None:
    lignes = [ENTETE, ligne(), ligne(**{"Code departement": "22", "Code commune": "001"})]
    retenues = list(read_department(lignes, "35"))
    assert len(retenues) == 1
    assert retenues[0]["code_commune"] == "35051"


def test_la_conversion_ecrit_un_csv_gzip_lisible_et_compte_les_absences(tmp_path: Path) -> None:
    source = tmp_path / "brut.txt"
    source.write_text(
        "\n".join([ENTETE, ligne(), ligne(Section=""), ligne(**{"Date mutation": ""})]) + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "converti.csv.gz"
    counters = convert(source, destination, "35")
    assert counters == {
        "lines": 3,
        "without_parcel": 1,
        "without_date": 1,
        "without_price": 0,
    }
    with gzip.open(destination, "rt", encoding="utf-8") as handle:
        contenu = handle.read()
    assert contenu.splitlines()[0] == ",".join(GEODVF_COLUMNS)
    assert "35051000AZ0323" in contenu
