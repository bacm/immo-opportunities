# Versions d’implémentation

Ce dossier découpe le MVP défini dans [`SPEC.md`](../../SPEC.md) en incréments verticaux livrables.

Ces numéros désignent des **versions d’implémentation**, pas des versions de la spécification produit. `SPEC.md` reste la source de vérité pour le périmètre produit, les exigences `FR-*`, les datasets `DS-*`, les features et les règles de conformité. [`ARCHITECTURE.md`](../../ARCHITECTURE.md) reste la source de vérité pour les choix techniques et les ADR.

## Règles de suivi

- Une seule version peut être `En cours`.
- Une version ne commence que lorsque ses dépendances obligatoires sont terminées.
- Un item n’est terminé que si son test et son élément de preuve existent.
- Une version terminée devient immuable. Toute correction ultérieure est documentée dans la version active.
- Les décisions qui modifient une ADR nécessitent une nouvelle note ADR.
- Les données simulées doivent rester explicitement identifiées et ne peuvent satisfaire un critère lié aux données réelles.

États possibles : `À faire`, `En cours`, `Bloquée`, `Terminée`, `Abandonnée`.

Le code livré en avance sur une dépendance ne vaut pas avancement : une version dont les critères
dépendent d'une donnée absente reste `Bloquée` avec son motif, jamais `En cours`. La seule version
`En cours` au 4 septembre 2026 est **v0.3 — Référentiel spatial**.

## Tableau de suivi

| Version | État | Dépend de | Résultat principal |
|---|---|---|---|
| [v0.1 — Foundation](./v0.1-foundation.md) | Bloquée (CI GitHub) | — | Socle backend et data exécutable |
| [v0.2 — Cadastre 35](./v0.2-cadastre-35.md) | Terminée | v0.1 | Première release réelle importée et auditée |
| [v0.3 — Référentiel spatial](./v0.3-spatial-reference.md) | En cours | v0.2 | Parcelles, bâtiments et adresses résolus |
| [v0.4 — Carte réelle](./v0.4-real-map.md) | Bloquée (DS-05) | v0.3 | Explorer connecté à PostGIS et Martin |
| [v0.5 — Données métier](./v0.5-market-data.md) | Bloquée (v0.3) | v0.3 | Marché, énergie, urbanisme et risques disponibles |
| [v0.6 — Scoring](./v0.6-scoring.md) | Bloquée (profiling v0.5) | v0.5 | Deux classements explicables et reproductibles |
| [v0.7 — MVP connecté](./v0.7-connected-mvp.md) | Bloquée (publication v0.6) | v0.4, v0.6 | Workflow utilisateur complet et multi-tenant |
| [v0.8 — Pilote Bretagne](./v0.8-brittany-pilot.md) | Bloquée (données 35 et terrain) | v0.7 | Couverture régionale et validation professionnelle |

## Passage d’une version à la suivante

Pour clôturer une version :

1. Exécuter tous les contrôles indiqués dans sa section « Tests obligatoires ».
2. Ajouter les liens vers les rapports, captures, métriques ou sorties dans « Preuves de livraison ».
3. Vérifier la démonstration attendue sur un environnement propre.
4. Cocher toute la Definition of Done.
5. Passer la version à `Terminée` ici et la suivante à `En cours`.

## Références transversales

- [Roadmap produit](../../SPEC.md#21-plan-de-validation-et-roadmap)
- [Definition of Done du MVP](../../SPEC.md#26-definition-of-done-du-mvp)
- [Séquence d’implémentation](../../ARCHITECTURE.md#24-séquence-dimplémentation)
- [Definition of Done architecture](../../ARCHITECTURE.md#25-definition-of-done-architecture-mvp)
