# Audit DS-06 à DS-09 — données métier

**Périmètre :** département 35  
**Date de l'audit :** 6 août 2026  
**Statut :** contrats et garde-fous techniques validés sur fixtures ; aucune release réelle n'est
encore acceptée ou publiable.

## Verdict par source

| Source | Release réelle archivée | Tests de contrat | Verdict actuel |
|---|---:|---:|---|
| DS-06 DVF+ | non | oui | **rejeté pour publication** — release et profiling réel absents |
| DS-07 DPE ADEME | non | oui | **rejeté pour publication** — release et contrôle d'appariement réels absents |
| DS-08 GPU/CNIG | non | oui | **rejeté pour publication** — documents opposables et profils validés absents |
| DS-09 Géorisques | non | oui | **rejeté pour publication** — releases par famille de risque absentes |

Le verdict « rejeté pour publication » ne porte pas sur la qualité intrinsèque de la source. Il
indique qu'aucun fichier réel, immuable et checksumé n'est présent pour exécuter les contrôles
d'acceptation. Une source sans verdict `accepted` dans `meta.dataset_release` produit des features
absentes avec le motif `source_not_accepted`.

## Garanties testées

### DS-06 — DVF+

- une transaction postérieure au snapshot est exclue et un résultat déjà sélectionné qui fuit le
  futur fait échouer le calcul ;
- une mutation multi-parcelles ou multi-locaux sans prix alloué par bien n'est jamais convertie en
  prix au m² ;
- chaque candidat conserve distance, segment, date, type, surface, transformation de prix et motif
  d'inclusion ou d'exclusion ;
- les segments ne mélangent pas silencieusement les marchés urbains, ruraux, littoraux ou
  touristiques ;
- médiane pondérée, quartiles, dispersion, récence, liquidité et tendance restent absents quand le
  support statistique requis manque.

### DS-07 — DPE

- seuls les diagnostics déposés, non simulés, non annulés et antérieurs au snapshot sont éligibles ;
- le dernier diagnostic directement rattaché au bâtiment est retenu ;
- plusieurs diagnostics seulement rattachés à la même adresse produisent `ambiguous_match` ;
- l'absence de diagnostic est neutre et ne crée ni signal de vacance ni signal de dégradation ;
- la classe, la consommation, l'âge, les caractéristiques déclarées et la confiance d'appariement
  gardent la référence du diagnostic choisi.

### DS-08 — GPU

- le document doit être publié, opposable et valide à la date du snapshot ;
- un zonage absent, périmé ou sans zone représentative reste absent avec un motif ;
- les chevauchements matériels sans gagnant clair sont ambigus ;
- un profil de règles n'est utilisable que s'il a été validé pour la version exacte du document ;
- `URB-004` n'est calculé que si toutes les règles indispensables sont structurées et validées ;
- aucun texte libre de règlement n'est interprété automatiquement.

### DS-09 — Géorisques

- la granularité `point`, `zone`, `parcel` ou `commune` est obligatoire et persistée ;
- une observation communale reste dans `commune_context_only` et ne devient jamais une exposition
  parcellaire ;
- zéro intersection n'est produit que lorsque la couverture fine concernée est connue ;
- les distances aux sites pollués et cavités ne sont calculées qu'avec une géométrie et une
  couverture déclarée.

## Couverture et fraîcheur

La migration ajoute `meta.dataset_coverage_metric`, unique par release et commune, avec compte de
lignes, compte apparié, couverture, observation la plus fraîche et date de mesure. L'endpoint
`GET /api/v1/market-data/coverage?commune_code=35000` expose séparément une métrique nulle et une
métrique absente.

## Étapes nécessaires pour accepter une release

1. Archiver chaque actif source exact et son SHA-256 dans un manifeste de release.
2. Exécuter un import idempotent et conserver son rapport de quarantaine.
3. Produire les distributions par commune et comparer au millésime précédent.
4. Réaliser une revue manuelle stratifiée des comparables, appariements DPE, zones GPU et risques.
5. Enregistrer le verdict `accepted`, `display_only` ou `rejected`, puis seulement activer le
   pointeur atomique de la release.
