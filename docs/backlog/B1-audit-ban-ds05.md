# B1 — Terminer l'audit BAN DS-05 et prononcer un verdict

**Version :** v0.3 · **Taille :** M · **État :** À faire
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
