# A11 — Une décision se reconnaît à ce que le choix engage, pas au silence de `SPEC.md`

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** CLAUDE.md
**Dépend de :** A10 · **Bloque :** —
**DoD :** test sans objet — consigne d'agent, aucun script ne la contrôle ; preuve sans objet — aucun chiffre
**Demandé par :** conversation du 16 septembre 2026

## Contexte à charger

- `CLAUDE.md`, sections « Toute modification passe par un ticket » et « Boucle et arrêt »
- ADR-015 (ce qui arrête la boucle)

## Pourquoi ce ticket existe

`CLAUDE.md` posait : « Ce que `SPEC.md` ne tranche pas n'est pas une implémentation mais une
décision : ADR ou amendement de `SPEC.md`, sous ticket, avant le code », et en faisait une
condition d'arrêt de la boucle. `SPEC.md` décrit un produit, pas un nom de fonction, un découpage
de module ou une requête : prise au mot, la règle fait de presque chaque ligne une décision et
arrête la boucle à chacune. Une règle inapplicable est une règle ignorée.

## Choix retenus

- **Le critère porte sur ce que le choix engage.** Est une décision — ADR ou amendement de
  `SPEC.md`, sous ticket, avant le code, et arrêt de la boucle — un choix qui :
  - change ce qui est publié (définition d'une mesure, filtre, seuil, source, unité) ;
  - touche un interdit de `SPEC.md` §13 ou §18, ou le périmètre gelé ;
  - ajoute une dépendance, une table ou un service ;
  - est coûteux à défaire (schéma, contrat publié, donnée importée).
- **Tout le reste est un choix d'implémentation** : l'agent le tranche, l'écrit dans « Choix
  retenus » du ticket, et continue.
- La condition d'arrêt renvoie à ce critère au lieu de « une décision que `SPEC.md` ne tranche
  pas ».
- **Inchangés** : ticket avant la première ligne, « aucune bibliothèque sans ADR », gel de la
  plateforme.

## Critères d'acceptation

- `CLAUDE.md` ne contient plus « ne tranche pas » comme critère de décision ;
- le critère est écrit une fois, la condition d'arrêt y renvoie ;
- `make check`, `make backlog-check`, `make ticket-check` verts.
