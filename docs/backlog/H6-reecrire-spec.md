# H6 — Réviser toute la documentation de référence autour d'ADR-016

**Version :** transverse · **Taille :** L · **État :** Terminé
**Nature :** implémentation · **Touche :** SPEC.md, ARCHITECTURE.md, CLAUDE.md, README.md, DEPLOYMENT.md, explo.md, docs/archive/, docs/versions/, docs/operations/referentiel-local-35.md, docs/backlog/NICE-backlog.md, docs/backlog/README.md, docs/data/README.md, docs/data/mvp-dod-traceability.md, contracts/README.md, contracts/features/README.md, contracts/scoring/README.md, map/README.md, map/martin/README.md, map/sql/README.md
**Dépend de :** A7 · **Bloque :** —
**Demandé par :** décision du 15 septembre 2026 — « on doit revoir toute la doc qui n'est pas de l'historique »
**DoD :** test sans objet — documentation de référence ; preuve sans objet — la documentation est son propre livrable

## Contexte à charger

- `docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md`
- `docs/audit-critique-2026-09-15.md` §3, §7 à §13 (écarts entre documents et réalité)
- le document à réviser, en entier

## À corriger au passage — relevé par H1

`SPEC.md` §7.3 justifie l'exclusion des DPE d'appartement générés depuis un DPE d'immeuble par
« 0,6 % de conversion, mesuré ». Le recompte de [H1](./H1-barometre-marche-35-mesures.md)
n'a retrouvé ce chiffre sous aucun filtre ; hérité de `pistes-analyse-marche-35.md` §1.4, il n'y
porte aucun filtre écrit. La mesure reproductible est **0,4 % sur 277 parcelles**, cohortes 2021
à 2024, filtre écrit dans `docs/data/barometre-marche-35.md`. L'exclusion reste justifiée ; c'est
le chiffre qui change.

## Ce que ce ticket distingue

**Documentation de référence** : ce qui dit ce que le produit est, ce que le dépôt contient et
comment on y travaille. Elle doit être vraie au jour de sa lecture. C'est elle qui est révisée.

**Historique** : rapports datés de `docs/data/`, décisions de `docs/decisions/`, tickets clos,
versions clôturées, audit. Ils disent ce qui était vrai à leur date. On n'y touche pas.

## Ce qui change

- `SPEC.md` est **réécrit** autour de V5 et V2, en version 1.0 **provisoire jusqu'au verdict de
  H3** : la plateforme gelée y est décrite comme existante et suspendue, pas comme cible ; la
  rénovation-revente sort du MVP ; DS-10 à DS-12 sont réservés à Sitadel, MAJIC PM et BODACC ;
  les hypothèses sont celles que H3 mesure.
- `ARCHITECTURE.md` décrit ce qui existe (scripts, PostGIS, documents) et ce qui est gelé, avec
  ses défauts connus, au lieu d'une cible jamais atteinte ; la stack déclarée redevient la stack
  réelle.
- `CLAUDE.md`, `README.md`, `DEPLOYMENT.md`, `docs/versions/`, `docs/operations/referentiel-local-35.md`,
  `docs/backlog/NICE-backlog.md`, les README de `contracts/` et `map/` sont alignés.
- `explo.md` devient `docs/archive/explo-2026-08.md` : c'est un brainstorm d'août, pas une
  référence.
- `docs/data/mvp-dod-traceability.md` est marqué instantané historique d'une DoD remplacée.

## Critères d'acceptation

- aucun document de référence ne désigne D1, v0.4, E3 ou un `OpportunitySnapshot` comme
  prochaine étape ;
- aucun document de référence ne décrit comme existant ce qui n'existe pas (MUI, TanStack,
  Celery, WAL-G, Vitest, Orval, tests d'intégration PostGIS, registre d'images) ;
- `make doc-budget`, `make backlog-check` et `make check` verts ;
- H3 relit `SPEC.md` à sa clôture : ce qui y est provisoire le dit en tête de section.
