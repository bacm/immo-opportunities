# A8 — Condenser `CLAUDE.md` sans perdre une consigne

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** CLAUDE.md
**Dépend de :** — · **Bloque :** —
**DoD :** test sans objet — document d'instructions, sans comportement exécutable · preuve sans objet — le diff est la preuve
**Demandé par :** conversation du 16 septembre 2026

## Contexte à charger

- `CLAUDE.md` en entier (c'est l'objet du ticket)
- `docs/backlog/README.md`, section « Chemin critique » (pour ne pas contredire l'état)

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi ce ticket existe

`CLAUDE.md` est chargé dans chaque prompt : 246 lignes, 14 Ko. Une partie de son volume est de
la justification (le pourquoi d'une règle, l'anecdote qui l'a motivée) ou une redite de
`docs/backlog/README.md` et d'ADR-016. Les consignes elles-mêmes tiennent en moitié moins.
Un document d'instructions plus court est mieux suivi, et coûte moins à chaque tour.

## Choix retenus

- Chaque règle, interdit, commande et verrou reste présent ; seule la justification longue est
  retirée quand un lien la porte déjà (audit, ADR-015, ADR-016).
- Le diagnostic de l'audit et les résultats négatifs/positifs du référentiel restent, en une
  ligne chacun : ils évitent de refaire un travail déjà tranché.
- Pas de plafond de lignes ajouté à `scripts/check-doc-budget` pour ce fichier, à la demande de
  l'auteur.
- La phrase « les cibles du baromètre arrivent avec H1 et H2 » est mise à jour : H1 est terminé,
  `make market-barometer` existe.

## Critères d'acceptation

- `CLAUDE.md` perd au moins un quart de ses octets (obtenu : 246 → 160 lignes, 14,4 → 10,4 Ko ; le reste est consigne) ;
- chaque règle de la version précédente se retrouve dans la nouvelle (vérification par relecture
  section par section) ;
- `make backlog-check` et `make ticket-check` verts.
