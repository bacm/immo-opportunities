# Rapport du référentiel spatial — département 35

**Date :** 5 août 2026  
**État :** provisoire — RNB chargé, audit BAN en cours, BDNB et BD TOPO non chargées.

## Périmètre canonique

| Entité ou relation | Volume réel local | Source principale |
|---|---:|---|
| Communes | 332 | DS-01 |
| Parcelles | 1 333 327 | DS-01 |
| Property units mono-parcelle | 1 333 327 | DS-01 |
| Bâtiments RNB | 741 376 | DS-02 |
| Bâtiments RNB polygonaux | 737 512 | DS-02 |
| Bâtiments RNB ponctuels | 3 864 | DS-02 |
| Relations bâtiment–parcelle | 1 240 351 | DS-02 ↔ DS-01 |
| Bâtiments avec au moins une parcelle certaine, métriqués par commune | 737 333 | DS-02 ↔ DS-01 |
| Bâtiments sans parcelle, métriqués par commune | 3 607 | DS-02 ↔ DS-01 |

Les identités canoniques ne recopient pas les géométries cadastrales. Les vues
`reference.parcel_geometry` et `reference.property_unit_geometry` lisent la release DS-01 active,
ce qui garde le modèle viable lorsque le périmètre passera du département à la Bretagne puis à la
France.

## Qualité RNB

- 741 376 lignes sources normalisées, aucune quarantaine et aucun doublon de `rnb_id` ;
- 737 512 emprises polygonales et 3 864 identités ponctuelles sans polygone inventé ;
- 715 315 identifiants BDNB externes et 604 098 identifiants BD TOPO externes conservés ;
- 737 351 bâtiments disposent d'au moins un lien parcellaire explicite ;
- les taux d'appariement sont persistés pour chacune des 332 communes ;
- 403 bâtiments sans code commune et 33 portant un code absent du référentiel actif sont soumis à
  `rnb-commune-spatial@1`. Une commune n'est affectée que si le point représentatif est couvert par
  une unique géométrie communale active ; plusieurs candidates créent un match ambigu bloquant.

La somme des liens est supérieure au nombre de bâtiments liés : le maximum observé est de 37
parcelles pour un bâtiment. Cette cardinalité est modélisée nativement et n'est pas aplatie.

## Audit BAN

L'archive DS-05 du 17 juin 2026 contient 437 441 identifiants distincts et 326 161 relations
`cad_parcelles` déclarées. Avant publication :

- 8 identifiants sont répétés à l'identique, soit 225 lignes supplémentaires dédupliquées avec
  avertissement ;
- 217 identifiants conflictuels, représentant 230 lignes, sont intégralement mis en quarantaine ;
- chaque relation parcellaire est contrôlée contre la géométrie Cadastre active ;
- `covered = true` donne une confiance de 0,99 ; `within_ten_meters = true` donne 0,95 ; au-delà,
  la relation reste ambiguë à 0,80 et bloque la publication ;
- les clés BAN exactes observées dans le RNB créent des relations bâtiment–adresse certaines.

La release reste inactive tant que ses conflits d'identifiants et l'échantillon manuel stratifié
ne sont pas revus. L'API ne peut donc pas exposer ces adresses par accident.

## Features et valeurs manquantes

Le catalogue `morphology-v1` définit `LAND-001` à `LAND-010` et `BLD-001` à `BLD-003` avec source,
formule, transformation, unité, plage et règle de valeur manquante. Le moteur pur est couvert par
les tests unitaires, y compris les contradictions et l'exclusion des prédictions.

DS-03 et DS-04 ne disposant pas encore de release réelle acceptée, les features qui exigent leurs
attributs restent absentes avec un motif. Elles ne sont ni imputées ni remplacées par zéro. Les
identifiants BDNB et BD TOPO transportés par DS-02 ne valent pas observation de ces sources.

## Validation restante

- terminer et relever les métriques de l'import BAN ;
- importer des releases réelles et checksumées DS-03 et DS-04 ;
- produire la distribution finale `certain / ambiguous / rejected / unmatched` ;
- revoir manuellement un échantillon stratifié urbain, périurbain, rural et cas frontières ;
- accepter puis activer séparément chaque release ayant satisfait ses contrôles bloquants.
