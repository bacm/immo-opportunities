# BUG-19 — BDNB et BD TOPO s'importent encore par script, hors du graphe d'assets

**Version :** dette transverse · **Taille :** M · **État :** Terminé
**Nature :** implémentation
**Dépend de :** BUG-02 · **Bloque :** —
**Touche :** pipelines/src/immo_pipelines/assets/, pipelines/src/immo_pipelines/spatial/release_import.py, pipelines/src/immo_pipelines/cadastre/archive.py, pipelines/scripts/import_bdnb_release.py, pipelines/scripts/import_bdtopo_release.py, pipelines/src/immo_pipelines/definitions.py, pipelines/tests/, docs/backlog/BUG-20-imports-multi-assets-hors-dagster.md, docs/backlog/BUG-02-scripts-import-hors-dagster.md, docs/data/mvp-dod-traceability.md
**DoD :** preuve sans objet — changement d'orchestration, aucun chiffre publié ; la matérialisation réelle est consignée dans le ticket
**Découvert par :** [BUG-02](./BUG-02-scripts-import-hors-dagster.md), 16 septembre 2026

## Contexte à charger

- `docs/backlog/BUG-02-scripts-import-hors-dagster.md`, sections « Choix retenus » et « Résultat »
- `pipelines/src/immo_pipelines/spatial/release_import.py`
- le script de la source traitée, et lui seul

## Constat

BUG-02 a mis RNB et BAN dans le graphe d'assets, sur une fonction commune. Sept imports restaient
par script. Deux d'entre eux ont la même forme — une release, un département, une archive, un
membre à extraire : BDNB (`import_bdnb_release.py`) et BD TOPO (`import_bdtopo_release.py`).

## Choix retenus — 16 septembre 2026

- Ce ticket traite **BDNB et BD TOPO**. Les cinq autres (DVF, DPE, GPU, Géorisques, INSEE) ont
  plusieurs assets par release, une maille non départementale ou une résolution propre ; ils
  passent sous [BUG-20](./BUG-20-imports-multi-assets-hors-dagster.md), qui décidera de leur
  forme.
- `SourceImport` gagne une étape d'extraction facultative : le membre nommé par le manifeste est
  extrait, puis l'archive supprimée (805 Mo et 529 Mo qui saturaient le disque du conteneur).
  `extract_zip_member` rejoint `extract_seven_zip_member` dans `cadastre.archive`.
- Assets `ds03_bdnb_release`, `ds04_bdtopo_release` ; clés de run inchangées ; scripts conservés,
  avec leur rapport de fin (`report`, `method_rates`).

## Critères d'acceptation

- BDNB et BD TOPO s'importent par un asset partitionné release × département ;
- une partition déjà importée se rematérialise sans retéléchargement ni nouveau run.

## Résultat — 16 septembre 2026

- `SourceImport.extract` : le membre épinglé est extrait, l'archive supprimée avant l'import.
  `BDNB` et `BDTOPO` décrits ; assets `ds03_bdnb_release` et `ds04_bdtopo_release` inscrits aux
  définitions ; les deux scripts délèguent et gardent leur rapport de fin.
- **Sur l'instance Dagster du poste** : `ds03_bdnb_release` (35 × 2026-02-a) en 18 s et
  `ds04_bdtopo_release` (35 × 2026-06-15) en 43 s, origine `database_archive`, runs
  `bdnb:2026-02-a:35:bdnb-open-normalize@1` et `bdtopo:2026-06-15:35:bdtopo-normalize@1`
  retrouvés en saut d'idempotence — aucun téléchargement, aucun run nouveau.
- Tests : clés et extracteurs des deux sources ; le membre extrait est importé et l'archive a
  disparu au moment de l'import ; les quatre assets sont partitionnés par département.
- Débloque [BUG-20](./BUG-20-imports-multi-assets-hors-dagster.md), relu : les cinq sources
  restantes y sont décrites.

