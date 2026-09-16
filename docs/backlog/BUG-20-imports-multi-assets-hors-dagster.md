# BUG-20 — DVF, DPE, GPU, Géorisques et INSEE s'importent encore par script

**Version :** dette transverse · **Taille :** L · **État :** Terminé
**Nature :** implémentation
**Dépend de :** BUG-19 · **Bloque :** —
**Touche :** pipelines/src/immo_pipelines/assets/, pipelines/src/immo_pipelines/definitions.py, pipelines/tests/, docs/data/mvp-dod-traceability.md
**DoD :** preuve sans objet — changement d'orchestration, aucun chiffre publié ; la matérialisation réelle est consignée dans le ticket
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

## Choix retenus — 16 septembre 2026

Pris par l'agent sur délégation du porteur.

- **Un asset par source, qui exécute le script existant** en sous-processus, avec les arguments
  de la partition, et transmet sa sortie au journal Dagster. Ces cinq scripts portent chacun
  leur idempotence, leur purge de version et leur reprise, testées et éprouvées sur la base
  réelle ; les déplacer dans le paquet (environ 2 000 lignes) pour les appeler en fonction
  n'apporterait rien au graphe et risquerait ce qui marche. Dagster Pipes n'apporte rien non plus
  sans instrumenter les scripts. Un code de sortie non nul fait échouer la matérialisation.
- **Partitions** : release × département pour toutes, une dimension release dynamique par asset.
  Une release Géorisques est une famille (`<famille>--<date>`) : la famille est dans la clé de
  release, pas dans une dimension de plus.
- **Assets** : `ds06_dvf_release`, `ds07_dpe_release`, `ds13_dpe_new_release` (le même script,
  `--source`), `ds08_gpu_release`, `ds09_georisques_release`, `ds14_census_release`,
  `ds15_equipment_release`, `ds16_attraction_release` (le même script, source en argument).
- **GPU** : la matérialisation porte la mention que la source n'a ni checksum ni archive ; une
  rematérialisation reprend le lot depuis la base, elle ne reproduit pas un état.
- Les options de vérification des scripts (`--year`, `--limit`, `--only`, `--snapshot`) restent à
  la ligne de commande.

## Critères d'acceptation

- aucune source réelle ne s'importe plus hors du graphe d'assets ;
- `docs/data/mvp-dod-traceability.md` peut passer la ligne « pipelines partitionnés » à validé.

## Résultat — 16 septembre 2026

- `immo_pipelines.assets.script_sources` : huit assets, un par source, partitionnés release ×
  département, qui exécutent le script de la source depuis la racine du projet ; la sortie passe
  au journal Dagster et ses dernières lignes en métadonnée ; un code non nul fait échouer.
- **Sur l'instance Dagster du poste**, 35 : `ds06_dvf_release` (2026-09-13 et 2019-04-archive),
  `ds07_dpe_release` (2026-09-14-extract), `ds13_dpe_new_release` (2026-09-16-extract),
  `ds09_georisques_release` (cavity--2026-09-14), `ds14_census_release` (rp-2023),
  `ds15_equipment_release` (bpe-2025), `ds16_attraction_release` (aav2020-geo2025) : huit
  matérialisations réussies, chacune « déjà importé par … » avec le run existant.
- **`ds08_gpu_release` n'a pas été matérialisé** : le script ne s'arrête pas sur une release
  déjà importée, il reprend le lot (152 documents sur 184) et téléchargerait les 32 restants
  depuis une source sans checksum. Sa commande est testée ; sa première matérialisation réelle
  sera la reprise du lot.
- Tests : une source par asset et son script présent ; commandes conformes aux lignes de
  commande ; sortie en métadonnée ; échec propagé ; exécution depuis la racine.
- `mvp-dod-traceability.md` : « pipelines partitionnés » passe à validé, avec ses deux limites
  (35 seulement, GPU non reproductible).
- Aucune source réelle ne s'importe plus hors du graphe d'assets ; les scripts restent l'entrée en
  ligne de commande et le lieu de la logique pour ces cinq sources.

