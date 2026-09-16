# BUG-19 — Sept imports réels passent encore par des scripts, hors du graphe d'assets

**Version :** dette transverse · **Taille :** L · **État :** À faire
**Nature :** implémentation
**Dépend de :** BUG-02 · **Bloque :** —
**Touche :** pipelines/src/immo_pipelines/assets/, pipelines/src/immo_pipelines/definitions.py, pipelines/scripts/, pipelines/tests/
**Découvert par :** [BUG-02](./BUG-02-scripts-import-hors-dagster.md), 16 septembre 2026

## Contexte à charger

- `docs/backlog/BUG-02-scripts-import-hors-dagster.md`, sections « Choix retenus » et « Résultat »
- `pipelines/src/immo_pipelines/spatial/release_import.py`
- le script de la source traitée, et lui seul

## Constat

BUG-02 a mis RNB et BAN dans le graphe d'assets, sur une fonction commune. Restent par script :
BDNB (`import_bdnb_release.py`), BD TOPO (`import_bdtopo_release.py`), DVF
(`import_dvf_release.py`), DPE (`import_dpe_release.py`), GPU (`import_gpu_release.py`),
Géorisques (`import_georisques_release.py`) et INSEE (`import_territorial_release.py`). Tant
qu'ils y restent, la partition département n'existe pas pour ces sources et G1 demandera des
exécutions manuelles.

## Travail à réaliser

1. Pour chaque script, décrire la source par un `SourceImport`, ou étendre la fonction commune si
   la source a plusieurs couches ou une résolution propre (DPE épinglé par pagination, GPU sans
   checksum).
2. Un asset partitionné release × département par source ; les scripts délèguent.
3. Clés de run et d'idempotence inchangées.

## Critères d'acceptation

- aucune source réelle ne s'importe plus hors du graphe d'assets ;
- `docs/data/mvp-dod-traceability.md` peut passer la ligne « pipelines partitionnés » à validé.
