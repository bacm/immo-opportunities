# B5 — Calculer LAND-001..010 et BLD-001..003 sur releases acceptées

**Version :** v0.3 · **Taille :** M · **État :** À faire
**Dépend de :** B4 · **Bloque :** C1, D1, clôture de v0.3

## Contexte à charger

- `contracts/features/morphology-v1.json`
- `pipelines/src/immo_pipelines/spatial/features.py`
- `pipelines/tests/test_spatial_features.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le catalogue [`morphology-v1`](../../contracts/features/morphology-v1.json) et le moteur pur sont
livrés et testés : `LAND-001` à `LAND-010`, `BLD-001` à `BLD-003`, chacun avec source, formule,
transformation, unité, plage et règle de valeur manquante. La DoD de v0.3 coche déjà
« Features morphologiques testées ».

Ce qui manque n'est pas le code : c'est le **calcul sur des données réelles acceptées**, avec
provenance intacte. Aujourd'hui, les features dépendant de DS-03 et DS-04 restent absentes avec
motif, ce qui est correct mais ne prouve rien sur le calcul réel.

## Travail à réaliser

1. Matérialiser les features sur les releases effectivement acceptées à l'issue de B1, B2a, B2b.
2. Pour chaque feature et chaque unité, persister : valeur, unité, **provenance** (release et champ
   source), transformation appliquée, et le cas échéant **motif d'absence**.
3. Produire la distribution observée de chaque feature : volume calculé, volume absent par motif,
   quantiles, valeurs hors plage contractuelle.
4. Traiter les valeurs hors plage comme des anomalies à investiguer, jamais à écrêter silencieusement.
5. Désactiver explicitement, commune par commune, les features non supportées faute de source
   acceptée sur ce territoire.

## Points de vigilance

- **Le motif d'absence est aussi important que la valeur.** Une feature absente parce que la source
  n'est pas acceptée (`source_not_accepted`) n'a pas le même sens qu'une feature absente parce que
  la donnée n'existe pas pour cette parcelle. Le scoring en aval traitera ces cas différemment.
- Aucune imputation, aucune moyenne de commune, aucun zéro de substitution.
- La provenance doit permettre de remonter à la release exacte : c'est ce qui rendra le score
  explicable en E3 et reproductible après changement de millésime.
- Les métriques de complétude et de contradiction servent **uniquement** à la confiance, jamais à
  la valeur elle-même.

## Tests obligatoires

- une feature calculée sur une release non acceptée est refusée par le moteur ;
- chaque valeur produite porte sa provenance ; une valeur sans provenance fait échouer le calcul ;
- une source contradictoire produit une contradiction tracée, pas une valeur choisie ;
- une valeur hors plage contractuelle est signalée, pas écrêtée ;
- recalcul à données et définitions identiques : résultats identiques au bit près.

## Critères d'acceptation

- les 13 features sont calculées ou explicitement absentes avec motif, sur l'ensemble du 35 ;
- la distribution réelle de chaque feature est publiée ;
- aucune valeur imputée ;
- les features désactivées le sont explicitement, par commune ;
- v0.3 peut être passée à `Terminée`, et v0.4 à `En cours`.

## Preuves à produire

- rapport `docs/data/morphology-features-35.md` : distributions, complétude, motifs d'absence ;
- mise à jour de [`spatial-reference-35-report.md`](../data/spatial-reference-35-report.md) ;
- clôture de v0.3 dans [`docs/versions/README.md`](../versions/README.md).

## Lien avec le scoring

Ces distributions sont la **première moitié** de l'entrée de [E1](./E1-profiling-distributions.md).
Les seuils du scoring viendront de là et des distributions métier de D5 — jamais d'une valeur
choisie a priori.
