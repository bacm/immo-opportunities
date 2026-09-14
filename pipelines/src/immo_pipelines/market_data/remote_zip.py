"""Lire quelques membres d'un ZIP distant sans le télécharger — D2, DS-08.

Les archives CNIG du Géoportail de l'urbanisme sont massives et leur contenu utile est minuscule.
Mesuré le 14 septembre 2026 sur les 23 PLUi dont l'emprise touche le 35 : **36,9 Go au total**,
jusqu'à 4,6 Go pour une seule archive — pour environ **1,7 Mo de couches structurées** chacune.
Le reste est le règlement, le PADD et les orientations d'aménagement, en PDF, que ce ticket n'a
pas le droit d'interpréter.

Télécharger 36,9 Go pour en extraire quelques dizaines de Mo serait absurde, et le serait encore
plus à l'échelle de la France.

Le format ZIP permet de l'éviter : son répertoire central est **à la fin** du fichier. On lit donc
la queue de l'archive pour connaître la liste et la position de ses membres, puis on ne va
chercher que ceux dont on a besoin. Le serveur du GPU annonce `accept-ranges: bytes` et répond
206 aux requêtes partielles.

`zipfile.ZipFile` accepte n'importe quel objet fichier disposant de `read`, `seek` et `tell` :
il suffit donc d'en fournir un qui traduise les lectures en requêtes de plage HTTP.
"""

import urllib.request
from typing import IO

# Le CDN qui sert les archives du GPU repond 403 a l'agent par defaut de urllib. Se nommer est
# de toute facon la bonne pratique : un producteur doit pouvoir identifier qui le sollicite.
USER_AGENT = "immo-opportunities/0.1 (import DS-08 GPU ; contact via le depot)"


class RemoteFile:
    """Un fichier en lecture seule, servi par requêtes de plage HTTP.

    Un tampon est conservé autour de la dernière lecture : `zipfile` lit le répertoire central par
    petits morceaux successifs, et une requête HTTP par en-tête de membre rendrait l'ouverture
    aussi coûteuse que le téléchargement qu'on cherche à éviter.
    """

    # 256 Kio : assez pour couvrir le repertoire central d'une archive de plusieurs milliers de
    # membres en une ou deux requetes, assez peu pour ne rien telecharger d'inutile.
    CHUNK = 262_144

    # Le GPU sert des archives de plusieurs gigaoctets et une lecture de couche peut demander
    # plusieurs dizaines de secondes. Un delai court fait echouer l'epinglage au milieu, ce qui
    # est arrive au 115e document sur 182.
    TIMEOUT = 300

    def __init__(self, url: str, *, timeout: int = TIMEOUT) -> None:
        self.url = url
        self.timeout = timeout
        self._position = 0
        self._buffer = b""
        self._buffer_start = -1
        self.size = self._length()

    def _length(self) -> int:
        """La taille, par une requête d'un seul octet.

        Un `HEAD` serait plus direct mais ne survit pas à la redirection du GPU, qui renvoie
        403 sur la ressource finale. Un `Range: bytes=0-0` la traverse, et son en-tête
        `Content-Range` donne la taille totale. On en profite pour retenir l'URL effective :
        les requêtes suivantes évitent ainsi de repasser par la redirection.
        """
        request = urllib.request.Request(
            self.url, headers={"Range": "bytes=0-0", "User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            if response.status != 206:
                raise RuntimeError(
                    f"{self.url} a répondu {response.status} à une requête de plage : le serveur "
                    "ignore l'en-tête Range et renverrait l'archive entière."
                )
            self.url = response.url
            content_range = response.headers.get("Content-Range", "")
            if "/" not in content_range:
                raise RuntimeError(
                    f"{self.url} ne renvoie pas de Content-Range exploitable : {content_range!r}."
                )
            return int(content_range.rsplit("/", 1)[1])

    def _fetch(self, start: int, end: int) -> bytes:
        request = urllib.request.Request(
            self.url,
            headers={"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            if response.status != 206:
                raise RuntimeError(
                    f"{self.url} a répondu {response.status} à une requête de plage : le serveur "
                    "ignore l'en-tête Range et renverrait l'archive entière."
                )
            return response.read()

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            amount = self.size - self._position
        if amount <= 0:
            return b""
        end = min(self._position + amount, self.size)
        buffered = 0 <= self._buffer_start <= self._position and end <= self._buffer_start + len(
            self._buffer
        )
        if not buffered:
            start = self._position
            stop = min(max(end, start + self.CHUNK), self.size) - 1
            self._buffer = self._fetch(start, stop)
            self._buffer_start = start
            if len(self._buffer) < end - start:
                # Le serveur a renvoye moins que la plage demandee. Sans cette garde la lecture
                # serait silencieusement tronquee, et `zipfile` recevrait un en-tete incomplet
                # avec un message qui n'en designe pas la cause.
                raise RuntimeError(
                    f"{self.url} a renvoyé {len(self._buffer)} octets pour la plage "
                    f"{start}-{stop} : lecture tronquée."
                )
        offset = self._position - self._buffer_start
        data = self._buffer[offset : offset + (end - self._position)]
        self._position = end
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._position = offset
        elif whence == 1:
            self._position += offset
        else:
            self._position = self.size + offset
        return self._position

    def tell(self) -> int:
        return self._position

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        self._buffer = b""


def open_remote(url: str, *, timeout: int = RemoteFile.TIMEOUT) -> IO[bytes]:
    """Ouvrir une archive distante comme un fichier, sans la rapatrier."""
    return RemoteFile(url, timeout=timeout)  # type: ignore[return-value]
