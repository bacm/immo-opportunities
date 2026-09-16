# A9 — `CLAUDE.md` devient un document de routage et de méthode, sans état ni décision

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** CLAUDE.md
**Dépend de :** A8 · **Bloque :** —
**DoD :** test sans objet — document d'instructions · preuve sans objet — le diff est la preuve
**Demandé par :** conversation du 16 septembre 2026

## Contexte à charger

- `CLAUDE.md`
- `docs/backlog/README.md` § « Verdict d'état » et « Chemin critique » ; `SPEC.md` §6.4, §10, §11, §13 ; `docs/decisions/ADR-015` — pour vérifier que chaque contenu retiré a un propriétaire

## Pourquoi ce ticket existe

Après A8, `CLAUDE.md` porte encore l'état du projet, les acquis du 35, le chemin critique, la
liste hors périmètre et le contenu des ADR. Tout cela existe ailleurs avec un propriétaire
déclaré (README du backlog, `SPEC.md`, `docs/decisions/`), et périme vite : la section « État »
a été réécrite trois fois en deux jours. Un agent qui ajoute un job CI n'a pas besoin de la vision
produit ; il a besoin de savoir où chercher, ce qui s'ouvre avant d'écrire, et ce que le dépôt
refuse.

## Choix retenus

- `CLAUDE.md` = identité du projet en trois lignes, langue, table de routage par tâche, garde-fous
  transverses, processus (ticket, DoD, boucle, backlog, sous-agents), commandes de la boucle.
- Retirés, avec renvoi : état et chemin critique (README du backlog), acquis (SPEC §10), hors
  périmètre (SPEC §6.4), conditions de dégel (SPEC §11), détail des règles de données (SPEC §13),
  liste complète des commandes (`make help`).
- Conservés en une ligne chacun, parce qu'ils s'appliquent à tout changement et qu'un agent qui
  n'ouvre pas `SPEC.md` doit quand même les respecter : les chemins gelés, les règles de chiffres
  et de données, les interdits techniques, le recompte.

## Critères d'acceptation

- `CLAUDE.md` ne contient ni date d'état, ni chiffre du 35, ni liste hors périmètre ;
- chaque contenu retiré est atteignable par une ligne de la table de routage ;
- `make backlog-check`, `make invariants`, `make ticket-check` verts.
