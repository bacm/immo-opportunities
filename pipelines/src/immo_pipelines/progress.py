"""Rendre l'avancement d'un lot long lisible pendant qu'il tourne.

Un import départemental demande de trente minutes à deux heures. Sans repère, un lot silencieux
est indiscernable d'un lot bloqué — et l'inverse est vrai : une sortie ligne par ligne sur 184
documents noie l'information au lieu de la porter.

Le compromis retenu est une annonce par tranche de **10 %**, portant ce qu'on veut savoir pour
décider d'attendre ou d'intervenir :

    [DS-08] 30 % — 55/184 · 0 échec · 12 min écoulées · ~28 min restantes

L'estimation suppose un rythme constant, ce qui est faux quand un serveur limite le débit — le
GPU l'a fait sur la fin d'un lot. Elle est donnée pour cela : un écart entre l'estimation et le
réel est lui-même une information, pas une erreur à corriger.

Voir `ARCHITECTURE.md` §10.6.
"""

import sys
import time


class Progress:
    """Un compteur d'avancement qui ne parle qu'aux seuils.

    `label` identifie le lot dans une sortie partagée — le nom du dataset, par exemple. `total`
    peut être inconnu au départ et corrigé par `retotal` : certains catalogues ne disent leur
    volume qu'après filtrage.
    """

    def __init__(self, total: int, label: str, *, step: int = 10) -> None:
        self.total = max(total, 0)
        self.label = label
        self.step = step
        self.done = 0
        self.failed = 0
        self._announced = 0
        self._started = time.monotonic()

    def retotal(self, total: int) -> None:
        self.total = max(total, 0)

    def advance(self, *, failed: bool = False, detail: str = "") -> None:
        self.done += 1
        if failed:
            self.failed += 1
        if not self.total:
            return
        percent = self.done * 100 // self.total
        # Un seul message par palier franchi, meme si plusieurs le sont d'un coup sur un petit
        # lot. Le dernier palier est toujours annonce, quitte a doubler la ligne finale.
        if percent >= self._announced + self.step or self.done == self.total:
            self._announced = percent - percent % self.step
            self._emit(percent, detail)

    def _emit(self, percent: int, detail: str) -> None:
        elapsed = time.monotonic() - self._started
        parts = [
            f"[{self.label}] {percent} %",
            f"{self.done}/{self.total}",
            f"{self.failed} échec" + ("s" if self.failed > 1 else ""),
            f"{elapsed / 60:.0f} min écoulées",
        ]
        if self.done and self.done < self.total:
            remaining = elapsed / self.done * (self.total - self.done)
            parts.append(f"~{remaining / 60:.0f} min restantes")
        if detail:
            parts.append(detail)
        # `flush` : sans lui, Python bufferise quand la sortie n'est pas un terminal, et une
        # annonce d'avancement arriverait en bloc a la fin — soit exactement l'inverse du but.
        print(" · ".join(parts), flush=True, file=sys.stdout)
