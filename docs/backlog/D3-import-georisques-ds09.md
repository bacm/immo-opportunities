# D3 — DS-09 Géorisques : granularité conservée

**Version :** v0.5 · **Taille :** L · **État :** À faire
**Dépend de :** D2 · **Bloque :** D5

## Contexte à charger

- `contracts/datasets/DS-09/v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md` (§DS-09)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Verdict actuel : « rejeté pour publication — releases par famille de risque absentes ».

**Règle structurante :** la granularité `point`, `zone`, `parcel` ou `commune` est obligatoire et
persistée. Une observation communale reste dans `commune_context_only` et **ne devient jamais** une
exposition parcellaire. C'est la garantie centrale de ce ticket.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Une observation communale est une observation valide dont l'exposition parcellaire est absente.

## Travail à réaliser

1. Traiter chaque famille de risque comme une **release distincte** : elles n'ont ni la même
   granularité, ni la même fraîcheur, ni le même producteur. Une release unique « Géorisques »
   masquerait ces différences.
2. Pour le 35, couvrir au minimum les familles pertinentes à la qualification : inondation,
   retrait-gonflement des argiles, submersion marine et recul du trait de côte sur le littoral,
   sites et sols pollués, installations classées, radon.
3. Épingler et checksumer chaque release par famille.
4. Importer les `RiskObservation` en persistant la granularité d'origine et la date de la donnée.
5. Rattacher spatialement selon la granularité disponible, sans jamais en inventer une plus fine.
6. Produire `RISK-001` à `RISK-004` et `RISK-101` avec, pour chaque valeur, la granularité de la
   source qui la fonde.

## Points de vigilance

- **Risque déclaré :** surinterpréter un risque. « La commune est concernée par un PPRI » et « la
  parcelle est en zone inondable » sont deux affirmations différentes ; la seconde exige une donnée
  zonale, pas communale.
- Zéro intersection n'est produit **que** lorsque la couverture fine concernée est connue. Sinon,
  l'absence de risque détecté est une absence d'information, pas une absence de risque.
- Le littoral breton rend la submersion et le recul du trait de côte structurants sur le 35 nord ;
  ces familles ne peuvent pas être traitées comme secondaires.
- Un risque n'est pas un signal négatif automatique pour le scoring : il peut être une contrainte
  chiffrable dans un scénario de rénovation. Le lien risque → score se décide en [E1](./E1-profiling-distributions.md),
  pas ici.

## Tests obligatoires

- une observation communale ne produit jamais d'exposition parcellaire ;
- l'absence de couverture fine produit une absence motivée, pas un zéro ;
- chaque valeur porte la granularité de sa source ;
- une famille de risque non importée désactive explicitement les features correspondantes ;
- réimport stable.

## Critères d'acceptation

- une release par famille, réelle, checksumée, auditée ;
- granularité persistée et vérifiable sur chaque observation ;
- verdict documenté par famille ;
- couverture publiée par commune et par famille ;
- distributions RISK disponibles pour E1.

## Preuves à produire

- manifestes `contracts/datasets/DS-09/releases/…` par famille ;
- section DS-09 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/georisques-coverage-35.md`.
