# B1 — Terminer l'audit BAN DS-05 et prononcer un verdict

**Version :** v0.3 · **Taille :** M · **État :** Terminé
**Dépend de :** [BUG-03](./BUG-03-quarantaine-par-attribut.md) · **Bloque :** B3, C1

## Contexte à charger

- `pipelines/src/immo_pipelines/spatial/importer.py`
- `pipelines/scripts/import_ban_release.py`
- `contracts/datasets/DS-05/releases/2026-06-17-35.json`
- `docs/data/spatial-sources-audit.md` (§DS-05)
- `Makefile` (cible `ban-import`)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DS-05 est la dernière brique manquante du référentiel spatial et la dépendance déclarée de v0.4
(« Bloquée — démonstration adresse dépendante de DS-05 »). Tout est en place sauf le verdict :

| Élément | État |
|---|---|
| Manifeste versionné avec URL résolue, taille, SHA-256 | ✅ [`2026-06-17-35.json`](../../contracts/datasets/DS-05/releases/2026-06-17-35.json) |
| Reproductibilité du téléchargement | ✅ vérifiée le 4 septembre 2026, checksum conforme |
| Importeur, quarantaine, métriques d'appariement | ✅ [`importer.py`](../../pipelines/src/immo_pipelines/spatial/importer.py) |
| Verdict d'acceptation | ❌ bloqué par le contrôle des identifiants conflictuels |
| Revue manuelle stratifiée | ❌ → [B4](./B4-revue-manuelle-appariements.md) |

L'archive n'est pas en cause : elle est intègre et reproductible. C'est la **règle d'acceptation**
qui est inapplicable, d'où la dépendance à BUG-03.

## Travail à réaliser

1. Appliquer la décision de BUG-03 dans l'importeur et le contrat.
2. Exécuter l'import réel complet sur le 35 avec `import_ban_release.py 2026-06-17 --department 35`,
   sur une base propre, et relever les compteurs produits.
3. Contrôler les relations `cad_parcelles` contre la géométrie Cadastre active, selon les paliers
   déjà implémentés : `covered` → confiance 0,99 ; `within_ten_meters` → 0,95 ; au-delà → ambigu
   à 0,80. Vérifier que ces paliers viennent d'une mesure et non d'un choix — sinon les recalibrer
   depuis la distribution observée sur les 326 161 relations déclarées.
4. Produire la distribution `certain / ambiguous / rejected / unmatched` pour les relations
   adresse ↔ parcelle et adresse ↔ bâtiment.
5. Prononcer un verdict par release : `accepted`, `rejected`, ou `display_only`.
6. Consigner le verdict dans l'audit et activer la release seulement si elle est acceptée.

## Point de vigilance sur `display_only`

Le statut « affichage seulement » doit avoir une conséquence technique vérifiable, pas seulement
documentaire : une release `display_only` peut alimenter la recherche et la carte, mais **ne peut
pas** fonder une feature entrant dans un score. Si ce comportement n'est pas déjà distingué de
`accepted` dans le filtrage des releases par l'API, c'est à implémenter ici — sinon le statut est
une étiquette sans effet.

## Tests obligatoires

- import puis réimport de la même archive : identifiants internes stables, aucune duplication ;
- un `cad_parcelles` pointant une parcelle absente du référentiel actif produit une relation
  rejetée avec motif, jamais une relation silencieusement ignorée ;
- une adresse sans position (cf. BUG-03) n'entre dans aucune relation spatiale ;
- une release `display_only` ne produit aucune feature de score ;
- l'API ne renvoie aucune adresse issue d'une release non activée.

## Critères d'acceptation

- verdict explicite et daté pour `DS-05@2026-06-17` sur le 35 ;
- tous les compteurs du rapport sont reproductibles depuis l'archive checksumée ;
- aucun palier de confiance ne subsiste sans justification par la distribution observée ;
- les cas ambigus sont exclus de la publication et le restent après réimport.

## Preuves à produire

- section DS-05 mise à jour dans [`spatial-sources-audit.md`](../data/spatial-sources-audit.md) ;
- section « Audit BAN » réécrite dans
  [`spatial-reference-35-report.md`](../data/spatial-reference-35-report.md), en intégrant BUG-01 ;
- sortie JSON de l'import archivée dans `docs/data/`.

## Résolution — 4 septembre 2026

Verdict : **`display_only`** pour `DS-05@2026-06-17` sur le 35. Les adresses alimentent la
recherche et la carte ; les relations parcellaires ne fondent aucune feature de score tant que
[B4](./B4-revue-manuelle-appariements.md) n'a pas calibré les paliers de confiance.

Import réel exécuté sur base propre : cadastre importé, accepté, publié, référentiel spatial
propagé (332 communes, 1 333 327 parcelles), puis import BAN. Les trois SHA-256 DS-01 et tous les
volumes de l'acceptation v0.2 sont reproduits sur volume vierge.

### Réponses aux étapes du ticket

| Étape | Résultat |
|---|---|
| 2 · compteurs de l'import réel | 437 679 / 437 441 / 0 / 238, identiques aux valeurs prédites par le décompte de [BUG-01](./BUG-01-chiffres-audit-ban.md) — sa limite est levée |
| 3 · paliers de confiance | **Non justifiés par la mesure.** La densité croît en traversant 10 m et culmine entre 20 et 50 m. Les valeurs 0,99 / 0,95 / 0,80 sont des probabilités que la géométrie seule n'estime pas → B4 |
| 4 · distribution | `certain` 272 695 · `ambiguous` 49 479 · `rejected` 3 760, total 325 934. Par commune : 248 209 / 1 759 / 2 685 / 184 788 = 437 441 |
| 5 · verdict | `display_only`, daté, motivé |
| 6 · activation | Release publiée en `display_only`, exclue de `meta.analysis_dataset_release` |

### Six défauts corrigés

1. **Relation `cad_parcelles` non résoluble perdue en silence.** La jointure était interne : une
   référence absente du référentiel actif ne produisait aucune ligne, et `rejected_count` valait
   structurellement zéro. Elle produit désormais une relation `rejected` motivée, comptée par le
   contrôle `unresolved_cadastral_reference`.
2. **`set_acceptance` réservait de fait l'acceptation à DS-01.** Le contrôle de complétude par
   couches s'appliquait à toute source ; DS-05, qui n'en publie qu'une, était inacceptable par
   construction. Le contrôle suit maintenant le déclencheur SQL, qui le scope à DS-01, et une
   barrière générique exige au moins un import réussi.
3. **`catalog.publish` codait `'DS-01'` en dur.** `meta.publish_dataset_release` cherchant la
   release par `(id, data_source_id)` en `SELECT STRICT`, aucune release non cadastrale n'était
   publiable. La source vient désormais de la release.
4. **`display_only` était une étiquette sans effet.** `publication_mode` était persisté mais aucun
   des onze consommateurs ne le lisait. La vue `meta.analysis_dataset_release` nomme la frontière
   là où tout le filtrage de release a déjà lieu (migration `20260904_0017`).
5. **La quarantaine par attribut de BUG-03 n'avait jamais tourné.** Premier import réel :
   `IndeterminateDatatype`, `jsonb_build_object` étant variadique, un paramètre nu n'y a aucun
   type inférable. Corrigé par cast explicite.
6. **Trois clés étrangères vers `meta.entity_match` sans index**, dont son auto-référence
   `supersedes_match_id`. Retirer les relations d'un seul département n'aboutissait pas en dix
   minutes ; 6,5 s après indexation (migration `20260904_0018`). Tout rollback de release supprime
   des relations : c'est un prérequis de [G5](./G5-administration-bundle.md).

### Normalisation de `cad_parcelles`

BAN publie une partie de ces identifiants sur 15 caractères, l'ordinal de commune étant complété à
quatre chiffres : `350001000AE0125` pour l'IDU `35001000AE0125`. 158 866 des 326 161 références
déclarées portaient ce padding et disparaissaient donc toutes. Retirer le zéro en fait résoudre
158 066, soit 99,5 % contre le cadastre réel — un taux qu'une transformation fausse n'atteint pas.
Vérifié sur la source brute au checksum du manifeste : le padding vient de BAN, pas du parseur.

La forme brute reste dans `properties`, donc dans `meta.entity_source_observation`. La
transformation porte sa version, `ban-csv-normalize@2`, et cette version entre dans la clé
d'idempotence et l'identifiant de run — sans quoi un réimport après changement de code rendait
l'ancien résultat en se croyant à jour.

### Tests

| Test | Couvre |
|---|---|
| `test_ban_parcel_relations.py` (8) | jointure externe, deux motifs de rejet distingués, confiance nulle, `blocks_publication` compatible avec la contrainte, motif porté par la ligne, adresse sans position hors relation, rejets comptés, emplacement des paliers figé |
| `test_release_acceptance_gate.py` (6) | DS-05 acceptable sans les trois couches, barrière préservée pour DS-01, import réussi exigé de toute source, publication nommant la source de la release |
| `test_ban.py` (+6) | padding ramené à l'IDU, forme canonique intacte, longueur inattendue jamais devinée, seul un zéro de padding retiré, forme source préservée, volume mesuré depuis l'archive |
| `test_address_release_scope_contract.py` (4) | aucune adresse hors release DS-05 activée, scope départemental, `last_release_id`, la carte garde `display_only` |
| `test_analysis_release_scope_migration_contract.py` (4) | `display_only` exclu du périmètre d'analyse, vue et non copie du pointeur |
| `test_match_reference_indexes_migration_contract.py` (4) | les trois clés étrangères indexées, auto-référence comprise |

Vérifications sur données réelles, non automatisées faute de banc PostgreSQL dans `make check` :
216 adresses sans position et **0** relation spatiale ; réimport de la même archive →
`skipped_as_idempotent: true`, 325 934 relations inchangées, aucune duplication ; DS-05 présent
dans `meta.active_dataset_release` et absent de `meta.analysis_dataset_release`.

### Limites et suites

- Les paliers de confiance restent non calibrés. B4 est le préalable au passage en `accepted`.
- `reference.refresh_cadastre_spatial_reference` n'a aucun appelant applicatif : publier DS-01 ne
  peuple pas le référentiel spatial, l'appel reste manuel. À reprendre.
- Le manifeste `contracts/datasets/DS-01/releases/2026-06-01-35.json` porte encore
  `"sha256": null` sur ses trois couches alors que les valeurs sont mesurées et consignées. Un
  réimport DS-01 n'est donc pas épinglé. Hors périmètre B1, appartient à v0.2.
- Deux fichiers de tests préexistants n'étaient pas conformes à `ruff format` : `make check` était
  rouge avant cette intervention. Reformatés ici pour atteindre la DoD.
- Les relations `rejected` ne remontent pas dans l'API : `ACTIVE_MATCH_PREDICATE` exige un
  identifiant source actif des deux côtés, qu'une parcelle inexistante n'a pas. Conséquence
  assumée — le rejet vit dans l'audit, pas dans l'explorateur.
