# G1 — Étendre DS-01 à DS-09 aux départements 22, 29, 56

**Version :** v0.8 · **Taille :** XL · **État :** À faire
**Dépend de :** F2 · **Bloque :** G2, G3, G4, G8

## Contexte à charger

- `pipelines/src/immo_pipelines/definitions.py` (partitions)
- `pipelines/src/immo_pipelines/pilot/brittany.py`
- `docs/data/brittany-acceptance-matrix.md`
- `docs/backlog/BUG-02-scripts-import-hors-dagster.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le 35 sert de département de référence. La DoD MVP exige les **quatre** départements bretons :
« sources critiques des 4 départements importées, versionnées, auditées ».

C'est une répétition du travail des sections B et D sur trois territoires, avec une différence
majeure : elle doit passer par des pipelines partitionnés, pas par des exécutions manuelles.
9 datasets × 3 départements = 27 imports supplémentaires.

**Prérequis fortement recommandé :** [BUG-02](./BUG-02-scripts-import-hors-dagster.md). Sans assets
Dagster partitionnés, ce ticket devient ingérable et non reproductible.

## Décision ouverte

Le périmètre du pilote peut être réduit :

| Option | Avantage | Inconvénient |
|---|---|---|
| Quatre départements complets | DoD MVP satisfaite | charge maximale avant toute validation terrain |
| 35 + un second département contrasté | valide la généralisation à moindre coût | DoD MVP non atteinte, à assumer explicitement |

Le second département le plus informatif serait le 29 ou le 22 : littoral marqué et rural
dominant, donc les segments les plus fragiles identifiés en [E5](./E5-resultats-par-segment.md).

Cette décision doit être prise **avant** de commencer, et documentée.

## Travail à réaliser

1. Matérialiser la partition `dataset × release × département` pour toutes les sources.
2. Épingler une release par dataset et par département, avec URL résolue, taille et SHA-256.
3. Importer, auditer et prononcer un verdict **par département** — un verdict régional global
   masquerait les disparités.
4. Recalculer les métriques d'appariement, de couverture et de fraîcheur par territoire.
5. Rejouer le profiling : les distributions du 22, 29 et 56 ne sont pas celles du 35. Décider si
   les transformations restent départementales ou deviennent régionales, et le justifier.
6. Conduire une revue manuelle stratifiée réduite sur chaque nouveau département — pas une
   extrapolation depuis le 35.

## Points de vigilance

- **Ne pas présumer que ce qui marche sur le 35 marche ailleurs.** Le 35 est le département le plus
  urbain et le mieux couvert de Bretagne. Le 22 et le 56 sont plus ruraux, le 29 plus littoral.
  La couverture DVF, GPU et DPE y sera différente.
- Un département dont une source critique manque n'est **pas** couvert. Le déclarer couvert serait
  la faute la plus directement contraire à la DoD.
- Les seuils issus du profiling du 35 ne peuvent pas être appliqués tels quels sans vérification.

## Critères d'acceptation

- décision de périmètre documentée ;
- pour chaque département retenu : releases épinglées, importées, auditées, verdict par source ;
- métriques par territoire produites ;
- profiling rejoué et transformations justifiées ;
- aucun département déclaré couvert sans ses données critiques.

## Preuves à produire

- manifestes par dataset et par département ;
- rapports d'audit par département dans `docs/data/` ;
- mise à jour de [`brittany-acceptance-matrix.md`](../data/brittany-acceptance-matrix.md).
