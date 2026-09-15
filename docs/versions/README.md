# Versions d'implémentation

Ce dossier découpe en incréments verticaux ce qui a été livré avant le 15 septembre 2026. Depuis
[ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md), le produit n'est plus la
plateforme que ces versions construisaient : il est porté par la série de tickets `H` du
[backlog](../backlog/README.md), sans numéro de version.

`SPEC.md` reste la source de vérité produit, `ARCHITECTURE.md` la source de vérité technique.

## Règles de suivi

- Une version terminée est immuable : ses fichiers sont de l'historique.
- Une version gelée conserve son fichier tel quel ; son en-tête dit qu'elle est gelée et par quoi.
- Un item n'est terminé que si son test et sa preuve existent.
- Les données simulées ne satisfont jamais un critère lié aux données réelles.

États : `À faire`, `En cours`, `Bloquée`, `Gelée`, `Terminée`, `Abandonnée`.

## Tableau de suivi

| Version | État | Résultat |
|---|---|---|
| [v0.1 — Foundation](./v0.1-foundation.md) | Terminée | socle backend, données, CI |
| [v0.2 — Cadastre 35](./v0.2-cadastre-35.md) | Terminée | DS-01 importé, accepté, publié |
| [v0.3 — Référentiel spatial](./v0.3-spatial-reference.md) | Terminée | parcelles, bâtiments physiques, adresses ; revue B4 ; résultats négatifs établis |
| [v0.4 — Carte réelle](./v0.4-real-map.md) | Terminée | Explorer connecté à PostGIS et Martin |
| [v0.5 — Données métier](./v0.5-market-data.md) | Gelée — DS-06 à DS-09 importés en `display_only` ; D6 et D7 suspendus | DVF, DPE, GPU, Géorisques sur le 35 |
| [v0.6 — Scoring](./v0.6-scoring.md) | Gelée par ADR-016 | moteur écrit, jamais appelé ; listes E8 et E8f produites |
| [v0.7 — MVP connecté](./v0.7-connected-mvp.md) | Gelée par ADR-016 | workflow et multi-tenant écrits, sans candidat |
| [v0.8 — Pilote Bretagne](./v0.8-brittany-pilot.md) | Gelée par ADR-016 | socle régional écrit, jamais déployé |
| Série H — baromètre et radar | En cours | [H1 à H6](../backlog/README.md#h--intelligence-de-marché-puis-radar-adr-016) |

## Clôture d'une version

1. Exécuter les contrôles de sa section « Tests obligatoires ».
2. Lier rapports, captures et sorties dans « Preuves de livraison ».
3. Cocher la Definition of Done.
4. Passer la version à `Terminée` ici.

## Références

- [Roadmap](../../SPEC.md#21-plan-et-roadmap)
- [Definition of Done](../../SPEC.md#26-definition-of-done)
- [Séquence d'implémentation](../../ARCHITECTURE.md#24-séquence-dimplémentation)
