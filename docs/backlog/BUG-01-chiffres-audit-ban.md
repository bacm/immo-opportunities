# BUG-01 — Volumétries BAN erronées dans le rapport spatial 35

**Version :** v0.3 · **Taille :** S · **État :** À faire
**Fichier concerné :** [`docs/data/spatial-reference-35-report.md`](../data/spatial-reference-35-report.md)

## Contexte à charger

- `docs/data/spatial-reference-35-report.md`
- `pipelines/src/immo_pipelines/spatial/importer.py` (compteurs)
- `pipelines/tests/test_ban.py`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

La section « Audit BAN » du rapport annonce :

> - 8 identifiants sont répétés à l'identique, soit **225 lignes supplémentaires** dédupliquées avec
>   avertissement ;
> - 217 identifiants conflictuels, représentant **230 lignes**, sont intégralement mis en quarantaine ;

Les deux chiffres sont faux. Le second est en plus ambigu : 230 est le nombre de lignes *en excès*,
pas le nombre de lignes mises en quarantaine, qui est le double environ.

## Mesures de référence

Recomptées sur l'archive `adresses-35.csv.gz` dont le SHA-256 correspond au manifeste épinglé
(`22160b6d…ccc3d0`), avec `iter_ban_records` du dépôt :

| Grandeur | Rapport actuel | Mesure réelle |
|---|---:|---:|
| Lignes normalisées | non indiqué | 437 679 |
| Identifiants distincts | 437 441 | 437 441 ✅ |
| Relations `cad_parcelles` déclarées | 326 161 | 326 161 ✅ |
| Identifiants répétés à l'identique | 8 | 8 ✅ |
| Lignes en excès dues aux répétitions exactes | 225 ❌ | **8** |
| Identifiants conflictuels | 217 | 217 ✅ |
| Lignes portant un identifiant conflictuel | 230 ❌ | **447** |
| Lignes en excès dues aux conflits | non indiqué | 230 |

Contrôle de cohérence : 437 679 − 437 441 = 238 lignes en excès = 8 (répétitions exactes) + 230
(conflits). Le rapport a donc attribué aux répétitions exactes un nombre qui ne correspond à rien
de mesuré, et présenté le surplus des conflits comme leur volume total.

## Travail à réaliser

1. Corriger les deux phrases de la section « Audit BAN ».
2. Ajouter les grandeurs manquantes : lignes normalisées, lignes en quarantaine, part en
   pourcentage, nombre de communes concernées (82 sur 332).
3. Distinguer explicitement, partout dans le rapport, « lignes concernées » et « lignes en excès ».
4. Vérifier que les compteurs persistés par `BanImporter` portent des noms qui rendent cette
   confusion impossible (`conflicting_row_count` compte-t-il le total ou l'excès ?) et corriger
   le libellé si nécessaire.

## Tests obligatoires

- un test de l'importeur fige les compteurs attendus sur une fixture contenant à la fois une
  répétition exacte et un conflit, et vérifie l'invariant
  `source_count = normalized_count + quarantine_count + deduplicated_count` ;
- le test échoue si `deduplicated_count` et `quarantine_count` sont intervertis.

## Critères d'acceptation

- toute grandeur citée dans le rapport est reproductible depuis l'archive checksumée ;
- aucun chiffre du rapport n'est sans définition explicite ;
- l'invariant de conservation des lignes est testé, pas seulement écrit.

## Preuve à produire

Rapport corrigé, avec la commande ou le test permettant de régénérer chaque chiffre.
