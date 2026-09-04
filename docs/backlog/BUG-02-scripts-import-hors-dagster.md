# BUG-02 — Les imports réels passent par des scripts one-shot, pas par Dagster

**Version :** dette transverse · **Taille :** L · **État :** À faire
**Non bloquant** pour le chemin critique, mais bloquant pour la DoD architecture §25
(« pipelines partitionnés 22/29/35/56 »).

## Contexte à charger

- `pipelines/src/immo_pipelines/assets/cadastre.py` (modèle d'asset partitionné)
- `pipelines/scripts/import_ban_release.py`
- `pipelines/scripts/import_rnb_release.py`
- `pipelines/src/immo_pipelines/definitions.py`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Deux sources réelles sur trois s'importent hors du graphe d'assets :

| Import | Chemin actuel | Partitionné |
|---|---|---|
| DS-01 Cadastre | assets Dagster `pipelines/src/immo_pipelines/assets/cadastre.py` | oui |
| DS-02 RNB | script `pipelines/scripts/import_rnb_release.py` | non |
| DS-05 BAN | script `pipelines/scripts/import_ban_release.py` | non |

La traçabilité le note déjà : « partitions Dagster statiques — validé pour Cadastre ; manifests
autres sources absents ». Chaque nouvelle source importée par script aggrave la dette, et
l'extension régionale (G1) la rend intenable : 9 datasets × 4 départements = 36 exécutions
manuelles sans reprise ni observabilité.

## Conséquences concrètes

- pas de reprise après échec partiel : un import interrompu se relance depuis zéro ;
- pas de vue unifiée des `import-runs` pour l'administration (FR-012, G5) ;
- la fraîcheur des sources n'est pas observable au même endroit (G7) ;
- la partition `dataset × release × département` n'est pas matérialisée pour ces sources.

## Travail à réaliser

1. Extraire la logique commune des deux scripts : résolution du manifeste, téléchargement vérifié,
   archivage MinIO, enregistrement `raw_asset`, appel de l'importeur, métriques.
2. Créer les assets partitionnés `ds02_rnb_release` et `ds05_ban_release` sur la partition
   `dataset × release × département` déjà utilisée par le cadastre.
3. Conserver les scripts comme entrée en ligne de commande déléguant à l'asset, ou les supprimer.
4. Vérifier qu'une exécution partielle reprend sans retélécharger une archive déjà présente et
   vérifiée — le code actuel sait déjà le faire via `catalog.find_raw_asset`, ce comportement doit
   être préservé et testé.

## Tests obligatoires

- matérialisation d'une partition sur fixture, puis rematérialisation : aucun retéléchargement,
  identifiants internes stables ;
- un checksum divergent interrompt la matérialisation sans écrire en base ;
- les métriques d'import sont visibles via la même API que le cadastre.

## Critères d'acceptation

- aucune source réelle ne s'importe plus par un chemin qui contourne le catalogue ;
- la partition département existe pour toutes les sources importées ;
- `docs/data/mvp-dod-traceability.md` peut passer la ligne « pipelines partitionnés » à validé.

## Ordonnancement recommandé

À traiter **après** E3 (premier score publié) et **avant** G1 (extension régionale). Le faire plus
tôt retarde le chemin critique ; le faire plus tard rend G1 ingérable.
