# Reconstituer la base locale du département 35

**Révisé le :** 15 septembre 2026 (H6). **Portée :** environnement Docker local uniquement.

Le dépôt versionne le code, les contrats et les preuves ; il ne versionne pas l'état de la base.
Une copie fraîche part d'une base vide. Ce document donne la séquence qui rétablit l'état sur
lequel les rapports de [`docs/data/`](../data/) ont été mesurés — les neuf datasets, les calculs
dérivés et les listes — et dit ce qu'elle ne peut pas rétablir sans l'archive MinIO.

Les volumes attendus sont indiqués. S'ils diffèrent, s'arrêter et comprendre l'écart : ils sont
l'objet de l'acceptation, pas un effet de bord. Les étapes marquées **à confirmer** n'ont pas été
rejouées de bout en bout depuis une base vide ; le premier rejeu complet doit les corriger ici.

Toutes les commandes `docker compose` ci-dessous s'entendent avec
`--env-file .env.example -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml`, ce que
les cibles `make` font déjà.

## 0. Infrastructure et schéma

```bash
make dev
make migrate
```

Prévoir 16 Go de RAM et 100 Go de disque : la base finale pèse 29 Go, MinIO 6 Go, les images et
temporaires le reste. PostGIS tourne en émulation x86 sur un Mac arm64 (`POSTGRES_PLATFORM`).

## 1. DS-01 Cadastre — import, acceptation, publication

Seul asset Dagster réel, partitionné `département × release`, manifeste
`contracts/datasets/DS-01/releases/2026-06-01-35.json` (checksums épinglés depuis le 7 septembre).

```bash
docker compose … run --rm dagster-code \
  dagster asset materialize --module-name immo_pipelines.definitions \
  --select cadastre_department_release --partition "35|2026-06-01"
docker compose … run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py accept DS-01@2026-06-01 --mode accepted
docker compose … run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py publish DS-01@2026-06-01 \
    --department 35 --actor "<vous>" --reason "Reconstitution locale"
```

Attendu : 1 333 327 parcelles, 332 communes ; à la publication,
`render_parcel_count: 1333327`, `render_building_count: 865335`, 2 min 11 s. Un
`render_parcel_count` nul signifie une carte vide (BUG-07).

## 2. DS-02 RNB et DS-05 BAN

Exigent un cadastre publié.

```bash
make rnb-import DEPARTMENT=35   # DS-02@2026-09-05, copie archivée nommée au manifeste
make ban-import DEPARTMENT=35   # 437 441 adresses, 325 934 relations adresse ↔ parcelle
```

**DS-02 n'est réimportable que depuis l'archive MinIO** : le producteur écrase
`files/RNB_35.csv.zip` sur place. Sans restauration de `raw-sources`, `asset_origin` vaut
`upstream` et l'import échoue dès que les octets amont ont changé (BUG-05). Puis :

```bash
docker compose … run --rm dagster-code python pipelines/scripts/cadastre_release.py accept DS-02@2026-09-05 --mode accepted
docker compose … run --rm dagster-code python pipelines/scripts/cadastre_release.py accept DS-05@2026-06-17 --mode display_only
# puis publish pour chacune, mêmes options qu'à l'étape 1
```

Attendu RNB, après BUG-09 (version de transformation 2) : ~741 k enregistrements, relations
bâtiment ↔ parcelle avec confiance mesurée, dont ~400 k à recouvrement < 10 % non plus déclarées
certaines. Les volumétries exactes sont dans `docs/data/spatial-sources-audit.md`.

## 3. DS-03 BDNB et DS-04 BD TOPO

```bash
make bdnb-import DEPARTMENT=35     # DS-03@2026-02-a ; 805 Mo d'archive → 2,7 Go de GeoPackage
make bdtopo-import DEPARTMENT=35   # DS-04@2026-06-15 ; 974 172 bâtiments, 391 217 tronçons ; 3,7 Go libres
```

Acceptation `display_only` pour les deux, puis publication, comme à l'étape 2. L'identité
BD TOPO ↔ RNB par `identifiants_rnb` est acceptée (60 cas sur 60) ; BDNB n'a aucun rattachement
RNB (BUG-13).

## 4. Bâtiments physiques, appariements, features morphologiques

```bash
make physical-buildings SOURCE=rnb DEPARTMENT=35        # 514 859 bâtiments physiques
make physical-buildings SOURCE=cadastre DEPARTMENT=35   # 517 615
make matching-refresh                                   # relations et métriques d'appariement
make morphology-features DEPARTMENT=35                  # LAND-001..007, LAND-009 sur 1 333 327 unités
```

Attendu : ~20 M de valeurs d'unité foncière dans `feature.feature_value` ; `LAND-008`,
`LAND-010` absentes avec motif. `BLD-*` et `REN-*` s'écrivent à l'étape 6. Rapports : `make matching-report`.

## 5. DS-06 DVF — douze millésimes

```bash
make dvf-import DEPARTMENT=35           # DS-06@2026-09-13 : geo-dvf Etalab 2021 à 2025
make dvf-archive-import DEPARTMENT=35   # DS-06@2019-04-archive : DGFiP 2014 à 2020 (D8)
```

Attendu : 284 699 mutations, 668 315 lots, 65,5 % sans prix allouable (`dvf-quality-35.md`).
Verdict `display_only` — **à confirmer** : la commande `accept` de `cadastre_release.py` avec
`DS-06@2026-09-13 --mode display_only`, ou le verdict porté par le rapport de qualité.

## 6. DS-07 DPE — extrait épinglé

L'ADEME ne publie aucun fichier daté : l'extrait est constitué par pagination d'API, puis épinglé.
**L'extrait du 14 septembre n'est reproductible à l'identique que depuis l'archive MinIO.** Sans
elle, `make dpe-pin RELEASE=<date> DEPARTMENT=35` constitue un nouvel extrait, donc une nouvelle
release, avec des volumes différents.

```bash
make dpe-import DEPARTMENT=35   # DS-07@2026-09-14-extract : 231 416 lignes, 208 086 diagnostics
make dpe-report DEPARTMENT=35   # docs/data/dpe-matching-35.md : 59,04 % rattachés au bâtiment
make building-features DEPARTMENT=35   # BLD-001..003, REN-001..008 absentes par bâtiment physique
```

`make building-features` vient après les releases BDNB, BD TOPO, BAN et DPE, qu'il cite, et après
`make physical-buildings` : reconstruire les bâtiments physiques supprime leurs features en
cascade. Attendu : 5 663 449 lignes, 514 859 bâtiments RNB × 11 features (BUG-13).

## 7. DS-08 GPU

```bash
make gpu-import DEPARTMENT=35   # DS-08@2026-09-14 : 184 documents, lot arrêté à 152
make urban-features DEPARTMENT=35   # URB-001..005 ; 16 min ; URB-005 vaut zéro partout
```

**DS-08 n'a ni checksum ni archive** : le manifeste porte 184 assets à `sha256: null`, et le
script streame les ZIP distants. Un rejeu peut donner un état différent sans que rien ne le
signale. Le débit s'effondre en fin de lot (deux documents par vingt minutes) ; le lot reprend
depuis l'état en base. Attendu : 21 136 zones, 424 022 contraintes, 300 communes.

## 8. DS-09 Géorisques — dix familles

Une release par famille, `<famille>--2026-09-14`. Les familles servies par fichier national
(argiles) ou par le GPU (servitudes) sont épinglées séparément :

```bash
make georisques-pin-clay RELEASE=2026-09-14 DEPARTMENT=35 ARCHIVE=<AleaRG_Fxx_L93.zip>   # 823 Mo décompressés
make georisques-pin-sup  RELEASE=2026-09-14 DEPARTMENT=35
for f in cavity clay flood-atlas gaspar-risks industrial-installation landslide natural-disaster radon soil-pollution sup; do
  make georisques-import RELEASE="$f--2026-09-14" DEPARTMENT=35
done
make georisques-report DEPARTMENT=35
```

**À confirmer** : l'ordre pin puis import par famille, et le nom exact de la release attendu par
`georisques-import`. Attendu : 10 824 observations, 339 communes ; aucune zone inondable typée ;
quatre servitudes en `403` persistant.

## 9. Rapports métier

```bash
make market-data-quality DEPARTMENT=35   # docs/data/market-data-quality-35.md
```

## 10. Listes exploratoires et kit terrain

```bash
make exploratory-candidates COMMUNE=35051   # 692 éligibles, 33 remis
make biens-en-vente COMMUNE=35051           # 18 signal, 163 baseline ; extrait DPE du 2026-09-07
make field-test-kit COMMUNE=35051
```

## Ce que la séquence ne rétablit pas

- **Les octets de DS-02 et l'extrait DS-07** sans restauration de `raw-sources`. MinIO est le seul
  chemin durable ; `scripts/backup-platform` le sauvegarde en entier, sur la machine sauvegardée.
  Une copie de `raw-sources` hors de ce poste est le minimum, non fait.
- **L'état exact de DS-08** : sans checksum, un rejeu n'est pas comparable.
- **Aucun `OpportunitySnapshot`** : le moteur de score n'a pas d'appelant, et aucune définition de
  score n'est fondée sur un profiling (`SPEC.md` §11.3). C'est l'état réel du produit.
- **Le baromètre** (H1) n'existe pas encore ; quand il existera, `make market-barometer` sera
  l'étape 11.
- **Un rebuild d'image** (`make rebuild`) est nécessaire après toute modification de
  `pipelines/` ou de `contracts/` : les images les embarquent. Vérifier qu'aucun lot ne tourne :
  le rebuild recrée PostgreSQL.
