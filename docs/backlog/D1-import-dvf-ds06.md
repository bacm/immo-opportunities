# D1 — DS-06 DVF+ : archive, import relançable, comparables explicables

**Version :** v0.5 · **Taille :** XL · **État :** À faire
**Dépend de :** B5 · **Bloque :** D2, D5, E1

> Avec [B1](./B1-audit-ban-ds05.md), c'est la moitié du chemin critique. Sans DVF+, aucune feature
> de marché, donc aucun des deux scores.

## Contexte à charger

- `contracts/datasets/DS-06/v1.json`
- `contracts/features/market-data-v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `pipelines/tests/test_market_data_features.py`
- `docs/data/market-data-sources-audit.md` (§DS-06)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

L'audit métier est net : « DS-06 DVF+ — release réelle archivée : non — **rejeté pour publication**,
release et profiling réel absents ». Le moteur, lui, est livré et testé sur fixtures :
sélection de comparables explicable, exclusion des fuites temporelles, refus des mutations complexes
non décomposables.

Ce ticket apporte la **donnée réelle** à un moteur qui l'attend.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Une mutation complexe non décomposable est une transaction valide dont le prix unitaire est
> inutilisable : elle relève de ce troisième état, pas d'un rejet de la transaction.

## Travail à réaliser

### 1. Release archivée et reproductible

- résoudre l'URL exacte du millésime DVF+ retenu — jamais un alias `latest` ;
- relever taille et SHA-256, écrire `contracts/datasets/DS-06/releases/<release>-35.json` ;
- archiver dans MinIO avant tout import.

### 2. Import relançable

- reprise sans retéléchargement quand l'archive est déjà archivée et vérifiée ;
- idempotence : réimport de la même archive sans duplication de transaction ;
- quarantaine motivée pour toute ligne non exploitable.

### 3. Rattachement des transactions

- rattacher chaque mutation aux parcelles et biens du référentiel spatial issu de v0.3 ;
- mesurer et publier le taux de rattachement par commune, avec les non rattachés et leur motif.

### 4. Mutations complexes — le point le plus sensible

Une mutation multi-parcelles ou multi-locaux sans prix alloué par bien **ne doit jamais** produire
un prix au m². Le moteur le garantit déjà sur fixtures ; il faut mesurer la part réelle de ces
mutations dans le 35 et la publier. Si cette part est importante, elle limite mécaniquement la
couverture des comparables — c'est un résultat à documenter, pas à contourner.

### 5. Comparables explicables

Pour chaque comparable, conserver : distance, segment, date, type, surface, transformation de prix,
et **motif d'inclusion ou d'exclusion**. Les exclus sont aussi importants que les inclus : c'est ce
qui rend la sélection auditable (FR-010).

### 6. Segments de marché

Les segments initiaux ne doivent pas mélanger marchés urbains, ruraux, littoraux et touristiques.
Leurs frontières viennent de la donnée observée, pas d'un découpage administratif choisi.

### 7. Métriques de marché

`MKT-001` à `MKT-005` et `MKT-101` à `MKT-105`. Médiane pondérée, quartiles, dispersion, récence,
liquidité et tendance restent **absents** quand le support statistique requis manque — et le seuil
de support minimal vient du profiling, pas d'une valeur choisie.

## Points de vigilance

- **Fausse précision de prix** : risque déclaré de v0.5. Une médiane calculée sur trois transactions
  n'est pas une médiane exploitable ; le support minimal doit être mesuré et le manque assumé.
- **Fuite temporelle** : aucune transaction postérieure au snapshot ne peut entrer dans un
  comparable. Le moteur le teste déjà ; le vérifier sur données réelles.
- Une commune rurale peut n'avoir aucun comparable exploitable. C'est un résultat légitime, il doit
  se traduire par une feature absente motivée et une confiance réduite, pas par un repli sur la
  moyenne départementale.

## Tests obligatoires

- non-régression sur fixture du millésime importé ;
- mutation multi-parcelles sans allocation : aucun prix unitaire produit ;
- mutation multi-locaux : décomposition ou refus explicite ;
- transaction postérieure au snapshot exclue, et échec du calcul si elle est sélectionnée ;
- comparables inclus et exclus tous porteurs d'un motif ;
- segments non mélangés ;
- métrique sans support statistique : absente avec motif, jamais estimée ;
- réimport idempotent.

## Critères d'acceptation

- release réelle, immuable, checksumée, importée et auditée sur le 35 ;
- verdict documenté remplaçant « rejeté pour publication » ;
- taux de rattachement et part de mutations complexes publiés par commune ;
- distributions réelles des features MKT disponibles pour [E1](./E1-profiling-distributions.md) ;
- aucune valeur de prix produite sans sa chaîne de transformation.

## Preuves à produire

- manifeste `contracts/datasets/DS-06/releases/<release>-35.json` ;
- section DS-06 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/dvf-quality-35.md` : rattachement, mutations complexes, distributions,
  couverture des comparables par commune.
