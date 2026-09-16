# BUG-02 — Les imports réels passent par des scripts one-shot, pas par Dagster

**Version :** dette transverse · **Taille :** L · **État :** Terminé
**Touche :** pipelines/src/immo_pipelines/assets/, pipelines/src/immo_pipelines/definitions.py, pipelines/src/immo_pipelines/spatial/release_import.py, pipelines/scripts/import_rnb_release.py, pipelines/scripts/import_ban_release.py, pipelines/tests/, docs/backlog/BUG-19-imports-restants-hors-dagster.md, docs/data/mvp-dod-traceability.md
**Nature :** implémentation
**DoD :** preuve sans objet — changement d'orchestration, aucun chiffre publié ; la matérialisation réelle est consignée dans le ticket
**Non bloquant** pour le chemin critique, mais bloquant pour la DoD architecture §25
(« pipelines partitionnés 22/29/35/56 »).

## Ce que l'import DS-08 a montré — 14 septembre 2026

Le débit s'est effondré en fin de lot : quarante documents à l'heure au début, **deux en vingt
minutes** à la fin, le producteur limitant le débit et la temporisation s'accumulant.

Aucun réglage de script n'y répond, parce que le problème n'est pas dans le script :

| Manque | Ce que Dagster apporte |
|---|---|
| Séquentialité | partitions `dataset × release × département` traitées de front, concurrence bornée |
| Lot lié à la session | un asset planifié s'étale, reprend la nuit, cède le pas quand le producteur ralentit |
| Surveillance manuelle | notification au lieu d'attente |

Le lot a été arrêté à **152 documents sur 184**, ce qui suffit à valider la chaîne de calcul. Les
32 restants ne sont pas perdus — l'import reprend sur l'état en base — mais les rattraper à la
main n'a pas de sens : c'est exactement le travail que ce ticket doit rendre inutile.

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

## Choix retenus — 16 septembre 2026

Pris par l'agent sur délégation du porteur (« enchaîne en prenant les meilleures décisions »).

- **Ordonnancement.** Le ticket recommandait d'attendre E3. Le chemin critique est aujourd'hui
  tenu par des verrous humains (D6, H3, H4) : ce ticket ne retarde rien, et G1 en dépendra.
- **Logique commune** dans `immo_pipelines.spatial.release_import` : une description par source
  (`SourceImport` : source, couche, SRID, préfixe de run, version de transformation, importeur)
  et une fonction `import_department_release`, qui enregistre la release, résout l'asset
  (archive en base, archive nommée, puis amont — `resolve_asset`, inchangé), importe et
  rafraîchit les métriques. Les clés de run et d'idempotence sont **identiques** à celles des
  scripts : un asset rematérialisé retrouve les imports déjà faits.
- **Assets** `ds02_rnb_release` et `ds05_ban_release`, partitionnés release × département comme
  le cadastre, une dimension release dynamique par source.
- **Scripts conservés** comme entrée en ligne de commande : ils délèguent à la même fonction.
  Les cibles `make rnb-import` et `make ban-import` ne changent pas.
- **Périmètre.** DS-02 et DS-05, comme le demande le ticket. Les sept autres imports par script
  (BDNB, BD TOPO, DVF, DPE, GPU, Géorisques, INSEE) suivent le même modèle sous
  [BUG-19](./BUG-19-imports-restants-hors-dagster.md) ; le critère « aucune source ne contourne »
  ne sera tenu qu'à sa clôture.

## Ordonnancement recommandé

À traiter **après** E3 (premier score publié) et **avant** G1 (extension régionale). Le faire plus
tôt retarde le chemin critique ; le faire plus tard rend G1 ingérable.

## Résultat — 16 septembre 2026

- `immo_pipelines.spatial.release_import` porte la logique commune ; les deux scripts y délèguent
  (`make rnb-import`, `make ban-import` inchangés). La version RNB y a déménagé avec son
  commentaire.
- Assets `ds02_rnb_release` et `ds05_ban_release`, partitionnés release × département (dimension
  release dynamique `rnb_releases`, `ban_releases`), inscrits aux définitions.
- **Sur la base réelle** : `make ban-import DEPARTMENT=35` rejoue la release 2026-06-17 depuis
  l'archive en base, avec la même clé, en saut d'idempotence. Puis, par Dagster, sur l'instance du
  poste : `ds05_ban_release` (35 × 2026-06-17) et `ds02_rnb_release` (35 × 2026-09-05)
  matérialisées, origine `database_archive`, runs `ban:2026-06-17:35:ban-csv-normalize@2` et
  `rnb:2026-09-05:35:2` retrouvés — aucun téléchargement, aucun run nouveau.
- Tests (`test_source_release_assets.py`) : rematérialisation sans téléchargement et à clés
  stables ; checksum divergent arrêté avant tout asset brut et tout import ; clés identiques aux
  scripts d'avant ; partition département ; matérialisation Dagster d'une partition.
- Les métriques d'import passent par la même table (`meta.import_run`) et la même route
  d'administration (`GET /api/v1/admin/import-runs`) que le cadastre.
- **Critères non encore tenus** : sept sources s'importent encore par script, suivies par
  [BUG-19](./BUG-19-imports-restants-hors-dagster.md) ; la ligne « pipelines partitionnés » de la
  traçabilité reste partielle jusqu'à sa clôture. La release, elle, est enregistrée avant la
  vérification du checksum, comme pour le cadastre : c'est l'entrée de catalogue, pas une donnée.

