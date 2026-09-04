# BUG-01 — Volumétries BAN erronées dans le rapport spatial 35

**Version :** v0.3 · **Taille :** S · **État :** Terminé
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

## Résolution — 4 septembre 2026

Section « Audit BAN » de [`spatial-reference-35-report.md`](../data/spatial-reference-35-report.md)
réécrite, chaque grandeur étant désormais mesurée et non plus recopiée.

`census_ban_archive` ([`spatial/ban.py`](../../pipelines/src/immo_pipelines/spatial/ban.py)) compte
une archive BAN sans base de données, dans l'ordre où l'import classe les identifiants.
`make ban-census ARCHIVE=…` refuse de s'exécuter si le fichier ne correspond pas au checksum du
manifeste ; sa sortie est archivée dans [`ban-census-35.json`](../data/ban-census-35.json).

| Grandeur | Rapport initial | Mesure retenue |
|---|---:|---:|
| Lignes lues | non indiqué | 437 679 |
| Lignes en excès dues aux répétitions exactes | 225 ❌ | 8 |
| Lignes portant un identifiant à attribut contradictoire | 230 ❌ | 447 (230 en excès) |
| Communes concernées | non indiqué | 82 sur 332 |

Trois défauts trouvés au-delà des deux chiffres annoncés :

1. La quarantaine intégrale des 217 identifiants conflictuels décrite par le rapport n'a plus
   cours depuis [BUG-03](./BUG-03-quarantaine-par-attribut.md) : l'identité est conservée, seul
   l'attribut est retiré. La correction des seuls chiffres aurait laissé une description fausse.
2. Le contrôle `exact_duplicate_ban_record` observait `deduplicated_row_count`, soit 238 lignes,
   alors que la source n'en contient que 8 en double : les 230 autres ne deviennent identiques
   qu'après le retrait de l'attribut contradictoire. Les doublons sont maintenant mesurés avant
   cette phase, et les 230 lignes publiées dans le détail de `ambiguous_ban_attribute`.
3. L'invariant de conservation était écrit trois fois dans le SQL sans être nommé. Il est
   désormais calculé une fois (`accounted_row_count`) et vérifié à la construction du décompte.

Compteurs de l'importeur renommés pour porter leur unité : `source_row_count`,
`normalized_row_count`, `quarantined_row_count`, `deduplicated_row_count`,
`conflicting_identity_row_count` (lignes) et `conflicting_identity_identifier_count`
(identifiants, comme `ambiguous_attribute_identifier_count`).

Le décompte publie aussi les compteurs que l'import **doit** produire
(`expected_normalized_rows`, `expected_quarantined_rows`, `expected_deduplicated_rows`) :
leur confrontation aux compteurs réellement persistés est un contrôle d'acceptation pour
[B1](./B1-audit-ban-ds05.md).

### Tests

| Test | Couvre |
|---|---|
| `test_census_separates_rows_concerned_from_rows_in_excess` | les deux unités figées sur une archive où elles diffèrent |
| `test_census_predicts_import_counters_that_cannot_be_swapped` | compteurs attendus à des valeurs distinctes : une interversion échoue |
| `test_census_refuses_counters_that_lose_source_rows` | l'invariant de conservation est exécuté, pas seulement écrit |

### Limite

Le comportement SQL de l'importeur reste non couvert, faute de banc d'essai PostgreSQL. Le
décompte mesure l'archive et prédit les compteurs ; il ne prouve pas que l'import les produit.
Cette vérification relève de B1.
