# BUG-20 — DVF, DPE, GPU, Géorisques et INSEE s'importent encore par script

**Version :** dette transverse · **Taille :** L · **État :** À faire
**Nature :** implémentation
**Dépend de :** BUG-19 · **Bloque :** —
**Touche :** pipelines/src/immo_pipelines/assets/, pipelines/src/immo_pipelines/definitions.py, pipelines/scripts/, pipelines/tests/
**Découvert par :** [BUG-19](./BUG-19-imports-restants-hors-dagster.md), 16 septembre 2026

## Contexte à charger

- `docs/backlog/BUG-02-scripts-import-hors-dagster.md`, section « Choix retenus »
- `pipelines/src/immo_pipelines/spatial/release_import.py`
- le script de la source traitée, et lui seul

## Constat

Cinq imports restent hors du graphe d'assets, chacun avec une forme que la fonction commune ne
couvre pas :

| Source | Script | Ce qui diffère |
|---|---|---|
| DS-06 DVF | `import_dvf_release.py` | un asset par millésime ; deux formats (geo-dvf, archive DGFiP) |
| DS-07, DS-13 DPE | `import_dpe_release.py` | extrait épinglé par pagination (`pin_dpe_release.py`), deux sources |
| DS-08 GPU | `import_gpu_release.py` | 184 documents sans checksum, lot qui reprend depuis la base |
| DS-09 Géorisques | `import_georisques_release.py` | une release par famille, épinglage séparé |
| DS-14 à DS-16 INSEE | `import_territorial_release.py` | maille communale, trois sources |

## Travail à réaliser

1. Pour chaque source, décider la partition (département, famille, millésime) et l'écrire dans
   « Choix retenus ».
2. Un asset par source ; les scripts délèguent ; clés de run et d'idempotence inchangées.
3. GPU : un asset qui reprend depuis l'état en base, sans promettre de reproductibilité que la
   source ne donne pas.

## Critères d'acceptation

- aucune source réelle ne s'importe plus hors du graphe d'assets ;
- `docs/data/mvp-dod-traceability.md` peut passer la ligne « pipelines partitionnés » à validé.
