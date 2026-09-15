# A7 — Ouvrir la série H dans les outils du backlog, et aligner les documents de pilotage sur ADR-016

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** scripts/backlog-status, scripts/check-commit-ticket, scripts/tests/test_backlog_status.py, scripts/tests/test_commit_ticket.py, ARCHITECTURE.md, CLAUDE.md, docs/backlog/README.md
**Dépend de :** — · **Bloque :** H1, H2, H3, H4, H5, H6
**Demandé par :** décision du 15 septembre 2026 — [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)
**DoD :** preuve sans objet — outillage de process, le test suffit

## Contexte à charger

- `docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md`
- `scripts/backlog-status` (constantes `ID_RE` et `SECTIONS`)
- `scripts/check-commit-ticket` (les deux expressions d'identifiant)
- `CLAUDE.md` section « État » et « Le chemin critique tient en une phrase »

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi ce ticket existe

ADR-016 redéfinit le produit et ouvre une série de tickets `H`. Or les identifiants de tickets
sont bornés à `[A-G]` dans deux scripts : un ticket `H1` serait absent du tableau généré et son
commit refusé par `make ticket-check` — le défaut muet que BUG-15 et BUG-16 ont déjà rencontré
deux fois. Le même commit aligne les trois documents qui disent au prochain agent quoi faire :
`CLAUDE.md` (dont l'état date du 13 septembre et désigne D1, terminé, comme le plus important),
`ARCHITECTURE.md` §23 (index des ADR) et le chemin critique de `docs/backlog/README.md`.

## Travail à réaliser

1. `ID_RE` passe de `[A-G]` à `[A-H]` dans `scripts/backlog-status` et dans les deux expressions
   de `scripts/check-commit-ticket` ; une section « H — Intelligence de marché » est ajoutée à
   `SECTIONS`.
2. Un test par script vérifie qu'un identifiant `H1` est reconnu et qu'un `I1` ne l'est pas.
3. `ARCHITECTURE.md` §23 reçoit la ligne ADR-016.
4. `CLAUDE.md` : la section « État » est réécrite à la date du jour, le chemin critique désigne
   H1, l'ordre d'exécution est celui d'ADR-016.
5. `docs/backlog/README.md` : le chemin critique en prose est réécrit ; le tableau est régénéré.

## Critères d'acceptation

- `make backlog` affiche les tickets H et `make backlog-check` est vert ;
- `make ticket-check` accepte un sujet `H1 — …` ;
- `make check` vert ;
- `CLAUDE.md` ne mentionne plus D1 comme priorité ni v0.4 comme version active.
