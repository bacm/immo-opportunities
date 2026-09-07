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

> **Épinglée depuis le 7 septembre 2026.** Les trois couches portaient `"sha256": null` : un
> réimport téléchargeait une archive qu'aucun checksum ne contraignait. Les checksums consignés
> dans [`DS-01-acceptance.md`](../data/DS-01-acceptance.md) ont été re-vérifiés contre le
> répertoire daté d'Etalab et inscrits au manifeste. Le répertoire est bien immuable : les trois
> valeurs sont identiques à celles du jour de l'acceptation. Un manifeste sans checksum est
> désormais refusé avant téléchargement — voir [BUG-05](../backlog/BUG-05-ds02-rnb-non-reproductible.md).

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
make rnb-import DEPARTMENT=35   # release DS-02@2026-09-05
make ban-import DEPARTMENT=35   # 437 441 adresses, 325 934 relations adresse–parcelle
```

> **DS-02 a changé de release.** `DS-02@2026-08-01` épinglait un alias mouvant et ses octets sont
> irrécupérables : le producteur écrase `files/RNB_35.csv.zip` sur place, ne conserve qu'une
> version S3 et n'expose aucun objet daté. Le manifeste du 1er août est conservé comme trace de
> ce qui avait été accepté, marqué `withdrawn`, et refusé à l'import. La release courante est
> `DS-02@2026-09-05`, dont le manifeste **nomme la copie archivée** : c'est elle, et non l'URL,
> qui porte la reproductibilité. Détail et décision dans
> [BUG-05](../backlog/BUG-05-ds02-rnb-non-reproductible.md).
>
> Les volumétries RNB de [l'ancien rapport](../data/spatial-reference-35-report.md) — 741 376
> bâtiments, 1 240 351 relations — portaient sur les octets du 1er août. Elles sont à re-mesurer
> sur la nouvelle release : c'est le travail de [B3](../backlog/B3-rapport-appariements.md).

Chaque import imprime désormais `asset_origin` : `upstream` quand les octets viennent du
producteur, `manifest_archive` quand ils viennent de la copie archivée nommée au manifeste,
`database_archive` quand l'archive était déjà enregistrée en base. Sur une plateforme
reconstituée sans restauration de MinIO, seul `upstream` est disponible — et pour DS-02 il
échouera dès que le producteur aura écrasé le fichier.

## 3 bis. DS-04 BD TOPO

L'import exige un cadastre publié et le RNB importé : il apparie contre l'identité bâtiment
canonique.

```bash
make bdtopo-import DEPARTMENT=35   # 974 172 bâtiments, 391 217 tronçons, 0 quarantaine
```

Attendu : `asset_origin` à `upstream` au premier import — 529 Mo téléchargés puis archivés — et
`database_archive` ensuite. L'archive `7z` est extraite dans un répertoire temporaire du
conteneur : prévoir 3,7 Go de disque libre, l'archive étant supprimée dès le GeoPackage extrait.

Puis acceptation et publication, dans la portée que l'audit reconnaît — `display_only`, les seuils
d'appariement géométrique n'étant pas calibrés :

```bash
docker compose --env-file .env.example \
  -f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm dagster-code \
  python pipelines/scripts/cadastre_release.py accept DS-04@2026-06-15 --mode display_only
# puis publish, mêmes options qu'à l'étape 2, avec DS-04@2026-06-15 --department 35
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
- **DS-03, DS-06 à DS-09** n'ont aucune release réelle : les features qui les exigent restent
  manquantes avec un motif. DS-04 est importé depuis le 7 septembre 2026, mais en `display_only` :
  ses 90 841 rattachements ambigus ne peuvent fonder aucune feature entrant dans un score.
- **Un rebuild d'image est nécessaire** après toute modification du code des pipelines **ou des
  contrats** : les images `dagster-code` et `migrate` embarquent `pipelines/` et `contracts/`,
  elles ne les montent pas. Un manifeste corrigé sur l'hôte reste invisible du conteneur tant que
  l'image n'est pas reconstruite.
- **L'archive MinIO n'est pas dans le dépôt.** Pour DS-02 elle est le seul chemin durable vers les
  octets acceptés : sans restauration de `raw-sources`, la release n'est réimportable que tant que
  le producteur sert encore les mêmes octets. `scripts/backup-platform` la sauvegarde en entier ;
  [G6](../backlog/G6-exploitation-restauration.md) en chronomètre la restauration.
