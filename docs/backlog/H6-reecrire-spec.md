# H6 — Réécrire SPEC.md autour de l'intelligence de marché et du radar

**Version :** transverse · **Taille :** M · **État :** À faire
**Nature :** implémentation · **Touche :** SPEC.md, docs/versions/README.md
**Dépend de :** H3 · **Bloque :** —
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)
**DoD :** test sans objet — documentation de référence ; preuve sans objet — la spécification est son propre livrable

## Contexte à charger

- `docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md`
- `docs/data/entretiens-professionnels-35.md` (sortie de H3)
- `docs/audit-critique-2026-09-15.md` §3, §10 (écarts spec / réalité) et §14
- `SPEC.md` en entier — c'est le seul ticket qui l'exige

## Pourquoi après H3, et pas avant

`SPEC.md` n'a jamais été amendé en 128 commits alors qu'il est source de vérité n°1 et que la
promesse a changé. Le réécrire avant d'avoir rencontré un professionnel reviendrait à spécifier une
seconde fois sans client. ADR-016 tient lieu de spécification provisoire jusqu'à ce ticket.

## Travail à réaliser

Réécrire, pas amender. Sections à refondre : §1 résumé, §2 vision et promesse, §3 utilisateurs, §5
hypothèses (H1 à H6 remplacées par celles que H3 a réellement mesurées), §6 périmètre (V5 et V2
inclus ; V0 retiré ; V1, V3, V4 en « stratégies futures » avec leur condition d'ouverture), §7
stratégies (rénovation-revente retirée du MVP, motif : décote 3-4 % mesurée), §13 données (DS-10
Sitadel, DS-11 MAJIC PM, DS-12 BODACC réservés ; collision DS-10 résolue), §16 architecture (la
plateforme gelée est décrite comme existante et suspendue, pas comme cible), §18 (les conditions
de H4 reportées), §21 roadmap (celle d'ADR-016), §22 monétisation (les prix déclarés en H3), §26
DoD (une DoD du baromètre et une DoD du radar, pas une DoD de plateforme).

Ce qui ne bouge pas : §13.6 (pas de propriétaire personne physique), §18.1 (minimisation), les
règles non négociables de `CLAUDE.md`.

## Critères d'acceptation

- `SPEC.md` porte une version 1.0 datée, un statut autre que « draft » ;
- chaque section refondue cite le fichier de `docs/data/` ou de `docs/decisions/` qui la fonde ;
- `make doc-budget` vert ;
- `docs/versions/README.md` reflète l'ordre d'ADR-016 et ne déclare plus v0.6 « bloquée » avec
  neuf tickets clos.
