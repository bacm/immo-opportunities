"""Lire quelques membres d'un ZIP distant sans le rapatrier — D2, DS-08.

Les archives CNIG du GPU sont massives et leur contenu utile minuscule : 36,9 Go pour les 23 PLUi
dont l'emprise touche le 35, dont environ 1,7 Mo de couches structurées chacun. Le reste est du
PDF que ce ticket n'a pas le droit d'interpréter.

Mesuré le 14 septembre 2026 : l'archive de Blois Agglopolys fait **4,56 Go**, son répertoire se lit
en **1,1 seconde**, et ses couches géographiques pèsent **13,92 Mo** compressées.

Ces tests n'atteignent pas le réseau : ils substituent la couche de transport pour éprouver ce qui
peut casser en silence — la logique de tampon, et le refus d'un serveur qui ignore les plages.
"""

import io
import zipfile

import pytest

from immo_pipelines.market_data.remote_zip import RemoteFile


class _FauxDistant(RemoteFile):
    """Le même objet, servi depuis des octets locaux, avec le compte des requêtes."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.requests: list[tuple[int, int]] = []
        self.url = "memory://archive.zip"
        self.timeout = 1
        self._position = 0
        self._buffer = b""
        self._buffer_start = -1
        self.size = len(payload)

    def _fetch(self, start: int, end: int) -> bytes:
        self.requests.append((start, end))
        return self._payload[start : end + 1]


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc/ZONE_URBA.dbf", b"zones" * 2000)
        archive.writestr("doc/reglement.pdf", b"texte reglementaire" * 50_000)
        archive.writestr("doc/DOC_URBA.dbf", b"document" * 1000)
    return buffer.getvalue()


def test_un_membre_se_lit_sans_lire_toute_l_archive() -> None:
    """C'est la raison d'être du module : le PDF ne doit jamais être téléchargé."""
    payload = _archive()
    distant = _FauxDistant(payload)
    with zipfile.ZipFile(distant) as archive:  # type: ignore[arg-type]
        contenu = archive.read("doc/ZONE_URBA.dbf")

    assert contenu == b"zones" * 2000
    octets = sum(end - start + 1 for start, end in distant.requests)
    assert octets < len(payload), (
        f"{octets} octets demandés pour une archive de {len(payload)} : la lecture partielle "
        "n'apporte rien si elle rapatrie tout."
    )


def test_le_tampon_evite_une_requete_par_petite_lecture() -> None:
    """Sans tampon, chaque en-tête de membre coûterait un aller-retour."""
    distant = _FauxDistant(_archive())
    with zipfile.ZipFile(distant) as archive:  # type: ignore[arg-type]
        archive.namelist()
    assert len(distant.requests) <= 3, f"{len(distant.requests)} requêtes pour lire un répertoire"


def test_une_lecture_au_dela_de_la_fin_ne_deborde_pas() -> None:
    distant = _FauxDistant(b"0123456789")
    distant.seek(8)
    assert distant.read(100) == b"89"
    assert distant.read(1) == b""


def test_un_serveur_qui_ignore_les_plages_est_refuse() -> None:
    """Un serveur qui répond 200 renverrait l'archive entière : mieux vaut échouer que payer."""

    class _SansPlage(_FauxDistant):
        def _fetch(self, start: int, end: int) -> bytes:
            raise RuntimeError("a répondu 200 à une requête de plage")

    distant = _SansPlage(_archive())
    with pytest.raises(RuntimeError, match="plage"):
        distant.read(10)
