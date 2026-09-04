# E1 — Profiler les distributions réelles du 35 et figer les transformations

**Version :** v0.6 · **Taille :** L · **État :** À faire
**Dépend de :** D6 · **Bloque :** E2, E3, E4, E5

## Contexte à charger

- `contracts/scoring/feature-registry-v1.json`
- `contracts/scoring/division-extension-v1.json`
- `contracts/scoring/renovation-resale-v1.json`
- `pipelines/src/immo_pipelines/scoring/engine.py`
- `docs/data/scoring-v0.6-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

C'est l'étape qui transforme un moteur en produit. Le moteur est livré et testé ; ses paramètres
sont volontairement non figés :

> Les définitions restent volontairement non publiables. Restent nécessaires : distributions
> réelles, transformations figées issues du profiling, backtest régional, ablations et résultats
> par segment.

**Règle non négociable :** aucun seuil territorial inventé. Les percentiles et les profils viennent
du profiling observé. Un seuil choisi « parce qu'il paraît raisonnable » invalide le score entier.

## Entrées

- distributions morphologiques de [B5](./B5-features-morphologiques.md) ;
- distributions métier de [D5](./D5-rapports-qualite-metier.md) ;
- limites établies par les revues manuelles [B4](./B4-revue-manuelle-appariements.md) et
  [D6](./D6-revue-manuelle-metier.md).

## Travail à réaliser

1. Produire, pour chaque feature du registre `scoring-features-v1`, sa distribution réelle sur le
   35 : volume exploitable, quantiles, asymétrie, valeurs extrêmes, part absente **par motif**.
2. Choisir la transformation de chaque feature à partir de cette distribution : normalisation par
   percentile, seuils, bornes. Documenter la justification de chaque choix.
3. Décider la **politique** de chaque feature : `required`, `optional` ou `confidence_only`.
   Une feature dont la couverture réelle est trop faible ne peut pas être `required` — sinon elle
   rend la majorité des unités inéligibles.
4. Vérifier l'absence de double comptage : les sources se recoupent (BDNB recopie des sources
   primaires, DVF alimente plusieurs métriques). Chaque valeur contribue **au plus une fois**.
5. Mesurer la corrélation entre features retenues : deux signaux fortement corrélés qui contribuent
   séparément gonflent artificiellement un score.
6. Figer les transformations et seuils dans les contrats de scoring, versionnés.
7. Segmenter : les distributions urbaines, périurbaines, littorales et rurales du 35 sont
   différentes. Un percentile départemental unique écraserait ces différences. Décider et
   documenter si les transformations sont départementales ou par segment.

## Points de vigilance

- **Risque déclaré :** optimiser les poids sur un échantillon trop faible. Si le volume exploitable
  après filtrage est insuffisant sur un segment, la conclusion est de ne pas publier ce segment.
- Le profiling ne doit pas être conduit sur les mêmes données que le backtest de
  [E4](./E4-backtest-baseline.md), sous peine de mesurer sa propre calibration.
- Une feature dont la distribution réelle est dégénérée — quasi constante, ou absente à 90 % — doit
  être écartée, pas rattrapée par une transformation agressive.
- Les motifs d'absence comptent : une feature absente parce que la source n'est pas acceptée doit
  bloquer différemment d'une feature absente parce que la donnée n'existe pas.

## Tests obligatoires

- toute transformation référencée dans une définition de score existe dans le profiling publié ;
- un seuil sans justification par une distribution fait échouer la validation du contrat ;
- une feature `required` dont la couverture est inférieure au minimum retenu fait échouer la
  validation ;
- le calcul est reproductible : mêmes données, mêmes définitions, même résultat.

## Critères d'acceptation

- distribution réelle publiée pour chaque feature du registre ;
- transformation et politique justifiées et versionnées dans les contrats ;
- absence de double comptage vérifiée et documentée ;
- corrélations mesurées et publiées ;
- décision documentée sur la segmentation des transformations.

## Preuves à produire

- rapport `docs/data/scoring-profiling-35.md` ;
- contrats [`division-extension`](../../contracts/scoring/division-extension-v1.json) et
  [`renovation-resale`](../../contracts/scoring/renovation-resale-v1.json) mis à jour et versionnés ;
- mise à jour de [`scoring-v0.6-report.md`](../data/scoring-v0.6-report.md).
