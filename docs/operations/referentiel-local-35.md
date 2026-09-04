# Reconstituer le référentiel local du département 35

**Date :** 4 septembre 2026
**Portée :** environnement Docker local uniquement. Aucun de ces gestes ne concerne un
environnement partagé.

Le dépôt versionne le code, les contrats et les preuves ; il ne versionne pas l'état de la base.
Une copie fraîche du dépôt part donc d'une base vide, et l'API comme l'Explorer n'y montrent rien.
Ce document donne la séquence exacte qui rétablit l'état sur lequel les rapports de
[`docs/data/`](../data/) ont été mesurés.

Les volumes attendus sont indiqués à chaque étape. S'ils diffèrent, s'arrêter et comprendre
l'écart : ils sont l'objet de l'acceptation, pas un effet de bord.

## 0. Infrastructure et schéma

```bash
make dev
make migrate
```

## 1. DS-01 Cadastre — import

L'import est un asset Dagster partitionné `département × release`. Il lit le manifeste
`contracts/datasets/DS-01/releases/2026-06-01-35.json`, archive les trois couches dans MinIO,
normalise, puis calcule les métriques par commune.

```bash
docker compose --env-file .env.example \
  -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm dagster-code \
  dagster asset materialize --module-name immo_pipelines.definitions \
  --select cadastre_department_release --partition "35|2026-06-01"
```

Attendu : 1 333 327 parcelles, 332 communes, 996 métriques par commune.

> **Cette étape n'est pas épinglée.** Les trois couches du manifeste portent encore
> `"sha256": null` alors que les checksums sont mesurés et consignés dans
> [`DS-01-acceptance.md`](../data/DS-01-acceptance.md). Un réimport télécharge donc une archive
> qu'aucun checksum ne contraint. C'est une dette de v0.2, signalée dans les limites de
> [B1](../backlog/B1-audit-ban-ds05.md).

## 2. DS-01 — acceptation puis publication

Deux gestes distincts, et c'est voulu : l'acceptation est un jugement sur la qualité, la
publication est un déplacement de pointeur. Aucun des deux n'est automatique.

```bash
docker compose --env-file .env.example \
  -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py accept DS-01@2026-06-01 --mode accepted

docker compose --env-file .env.example \
  -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py publish DS-01@2026-06-01 \
    --department 35 --actor "<vous>" --reason "Reconstitution locale"
```

La publication propage le référentiel canonique dans sa propre transaction et imprime les volumes
obtenus :

```json
"spatial_reference": {"area_count": 332, "parcel_count": 1333327,
                      "property_unit_count": 1333327}
```

Elle traverse 1,33 M parcelles : 2 min 11 s mesurées sur le 35, ce n'est pas un blocage. Il n'y a
**aucun appel manuel** à `reference.refresh_cadastre_spatial_reference` à faire — c'était le cas
avant [BUG-04](../backlog/BUG-04-propagation-referentiel-spatial.md).

## 3. DS-02 RNB et DS-05 BAN

Les deux imports exigent un cadastre publié : ils apparient contre la géométrie de la release
DS-01 active.

```bash
make rnb-import DEPARTMENT=35   # 741 376 bâtiments, 1 240 351 relations bâtiment–parcelle
make ban-import DEPARTMENT=35   # 437 441 adresses, 325 934 relations adresse–parcelle
```

Publier ensuite BAN dans la portée que son audit lui reconnaît — `display_only`, et non
`accepted` : les paliers de confiance de ses relations parcellaires ne sont pas calibrés, voir
[l'audit spatial](../data/spatial-sources-audit.md).

```bash
docker compose --env-file .env.example \
  -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py accept DS-05@2026-06-17 --mode display_only
# puis publish, mêmes options qu'à l'étape 2, avec DS-05@2026-06-17
```

## Ce que la séquence ne rétablit pas

- **Aucun `OpportunitySnapshot`.** Les deux définitions de score restent en
  `publication_eligible: false` ; l'Explorer n'affichera aucun candidat. C'est l'état réel du
  produit, pas une panne locale.
- **DS-03, DS-04, DS-06 à DS-09** n'ont aucune release réelle : les features qui les exigent
  restent manquantes avec un motif.
- **Un rebuild d'image est nécessaire** après toute modification du code des pipelines : les
  images `dagster-code` et `migrate` embarquent le code, elles ne le montent pas.
