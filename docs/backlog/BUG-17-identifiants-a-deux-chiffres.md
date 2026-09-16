# BUG-17 — Un ticket numéroté au-delà de 9 est refusé par `ticket-check` et ignoré comme dépendance

**Version :** dette transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** scripts/check-commit-ticket, scripts/backlog-status, scripts/tests/test_commit_ticket.py, scripts/tests/test_backlog_status.py
**Dépend de :** — · **Bloque :** —
**DoD :** preuve sans objet — outillage de process, le test suffit
**Découvert par :** ouverture de A10, 16 septembre 2026

## Contexte à charger

- `scripts/check-commit-ticket` (`ID_RE` et l'expression sur les noms de fichiers)
- `scripts/backlog-status` (`ID_RE`)
- `docs/backlog/BUG-16-suffixes-de-tickets-limites.md` (même famille de défaut)

## Pourquoi ce ticket existe

Les deux expressions d'identifiant écrivent `[A-H]\d[a-z]?` : un seul chiffre. Le sujet
`A10 — …` est refusé par `make ticket-check`, et une ligne `**Dépend de :** A10` serait ignorée
sans bruit par `make backlog`, comme BUG-15 et BUG-16 l'ont déjà vu pour d'autres bornes.

## Choix retenus

- `\d` devient `\d+` dans les trois expressions ; aucune autre borne n'est touchée.
- Un test par script : `A10` reconnu, `A10` comme dépendance conservée.
- Corrigé en passant : `test_les_identifiants_connus_viennent_du_backlog` supposait que `A9`
  n'existait pas ; il existe depuis A9 et `make check` était rouge depuis ce commit sans bruit.
  Le témoin devient `A99`.

## Critères d'acceptation

- `make ticket-check` accepte `A10 — …` ; les tests de `scripts/tests/` passent ; `make check` vert.
