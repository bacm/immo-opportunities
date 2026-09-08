# Réglage PostgreSQL

**Date :** 7 septembre 2026
**Portée :** le service `postgres` de la stack Compose, développement et VPS.

L'image `postgis/postgis` livre le `postgresql.conf` généré par `initdb`, dont les valeurs
visent une base de quelques centaines de méga-octets. La base du seul département 35 pèse
**14 Go**. Aucun réglage n'existait dans le dépôt : ni dans `compose.yaml`, ni dans
`infra/ansible/`.

Ce document consigne ce qui a été mesuré, **et ce qui ne l'a pas été**.

## Ce qui était en place

| Paramètre | Valeur livrée | Origine |
|---|---|---|
| `shared_buffers` | 128 Mo | `postgresql.conf` d'initdb |
| `work_mem` | 4 Mo | défaut |
| `maintenance_work_mem` | 64 Mo | défaut |
| `effective_cache_size` | 4 Go | défaut |
| `random_page_cost` | 4 | défaut, calibré pour un disque mécanique |
| `effective_io_concurrency` | 1 | défaut |
| `max_wal_size` | 1 Go | `postgresql.conf` d'initdb |

## Le levier réel : `work_mem`

Agrégat sur `meta.entity_observation_link`, 1,4 M lignes, `work_mem` réglé par session pour
isoler son seul effet :

| `work_mem` | Lots | Débordement disque | Temps |
|---|---:|---:|---:|
| 4 Mo — le défaut | 17 | **68 Mo écrits** | 1 520 ms |
| 64 Mo | 1 | aucun | **475 ms** |

**3,2× plus rapide, et 68 Mo d'écritures temporaires supprimées.** C'est le mécanisme qui
ralentissait les requêtes d'agrégation des importeurs : le hachage ne tenait pas en mémoire et
partait sur disque.

## Ce qui n'a rien donné de mesurable

**`shared_buffers`.** Le diagnostic était pourtant net — un parcours de
`meta.entity_source_observation` rapportait `shared hit=119 read=515925`, soit 99,98 % du travail
hors du cache de PostgreSQL. Mais après passage à 2 Go, les temps sont inchangés :

| Requête | Avant | Après |
|---|---:|---:|
| Jointure spatiale parcelles × commune | 4,6 – 7,9 ms | 4,6 – 5,3 ms |
| Résolution communale par `ST_Covers`, 20 000 points | 81 – 145 ms | 55 – 182 ms |
| Agrégat sur 974 k observations avec `ST_Area` | 1 138 – 1 557 ms | 1 127 – 2 118 ms |

La raison : sur le poste de développement, le cache de pages du système absorbait déjà ces
lectures à vitesse mémoire. La comptabilité `read` de PostgreSQL ne distingue pas une lecture
disque d'une lecture depuis le cache OS.

**Le réglage est conservé malgré l'absence de gain mesuré ici**, et c'est un pari assumé : sur le
VPS, PostgreSQL partage 16 Go avec quinze autres conteneurs — 2,4 Go au repos — et le cache OS
n'aura pas la marge qu'il a sur un poste dédié. Un cache applicatif nul y coûterait, alors qu'il ne
coûte rien ici.

**`maintenance_work_mem`.** Construction d'un index GiST sur 300 000 géométries : 334 ms à 64 Mo
contre 293 ms à 1 Go, soit 12 %. Marginal à cette échelle. Conservé pour les reconstructions
d'index et `VACUUM` sur la Bretagne entière, où le volume sera trois fois supérieur.

## Ce qui n'est pas mesuré, et pourquoi

`random_page_cost`, `effective_io_concurrency`, `max_wal_size` et `checkpoint_timeout` sont réglés
sur la foi du matériel et de la charge, sans mesure isolée :

- `random_page_cost` à 1,1 et `effective_io_concurrency` à 200 décrivent un NVMe, pas le disque
  mécanique que les défauts supposent. Leur effet est un choix de plan, qui ne se voit que sur des
  requêtes où l'index et le parcours séquentiel sont proches — aucune de nos trois requêtes témoins
  n'est dans ce cas.
- `max_wal_size` à 4 Go et `checkpoint_timeout` à 15 min visent les imports en masse, qui génèrent
  beaucoup de WAL. Le mesurer proprement demande de rejouer un import complet, ce qui n'a pas été
  fait : les durées d'import de cette session ne sont pas comparables entre elles, l'une ayant
  téléchargé 805 Mo et l'autre lu l'archive locale.

Ces quatre valeurs sont donc des **hypothèses documentées**, pas des résultats.

## Les statistiques comptent plus que le réglage

Découvert le 8 septembre 2026 en réalisant [B3](../backlog/B3-rapport-appariements.md), et de
loin l'effet le plus violent observé sur cette base.

Après insertion de 566 248 relations adresse ↔ bâtiment, la métrique par commune qui les lit a
tourné **4 h 44 sans aboutir**. Statistiques rafraîchies, la même requête rend en **2,2 s**. Le
planificateur ignorait les lignes fraîchement insérées — il estimait 5 000 lignes là où il y en
avait 437 441, un facteur 87 — et choisissait un plan catastrophique.

Autovacuum finit par le faire, mais son seuil par défaut — 10 % des lignes — le déclenche bien
après la requête qui suit immédiatement l'insertion. Or c'est précisément l'enchaînement de tous
les imports : insérer en masse, puis lire.

**`ANALYZE` exige d'être propriétaire de la table, et `pipeline_rw` ne l'est pas** : il se
contente d'un avertissement et saute la table. `pipelines/scripts/refresh_spatial_matching.py`
endosse donc `migration_owner`, dont le rôle de connexion est déjà membre, dans ce script de
maintenance et nulle part ailleurs.

**Ce qui reste à faire :** les trois autres importeurs — cadastre, BAN, RNB — n'analysent pas
après leur import. Ils sont exposés au même défaut, et le lent `UPDATE` de 20 minutes rencontré
pendant [B2b](../backlog/B2b-import-bdtopo-ds04.md) en venait probablement. Le corriger demande de
rejouer chaque import pour le vérifier, ce qui n'a pas été fait ici — à rattacher à
[BUG-02](../backlog/BUG-02-scripts-import-hors-dagster.md), dont le passage à Dagster est
l'occasion naturelle d'y placer un `ANALYZE` de fin d'asset.

## Où le réglage vit

Dans `compose.yaml`, en arguments `-c` du service `postgres`, chacun surchargeable par variable
d'environnement. `scripts/check-compose-config` — appelé par `make config`, donc par `make check` —
échoue si l'un des paramètres mesurés disparaît de la configuration rendue.

```bash
# Sur un hôte plus petit que 16 Go, dans le fichier d'environnement :
POSTGRES_SHARED_BUFFERS=1GB        # 25 % de la RAM
POSTGRES_EFFECTIVE_CACHE_SIZE=4GB  # 75 % de la RAM
```

`work_mem` s'applique **par nœud de tri ou de hachage et par connexion**. À 64 Mo avec
`max_connections` à 100, le pire cas théorique dépasse la RAM de l'hôte. Ce n'est pas un risque
réel pour cette charge — moins de dix connexions applicatives, et les imports sont séquentiels —
mais c'est la valeur à revoir en premier si le nombre de connexions augmente.

## Dimensionnement de l'hôte

Mesuré le 7 septembre 2026, département 35 seul, DS-01 à DS-05 importées.

| Poste | Mesuré |
|---|---:|
| Base PostgreSQL | 14 Go |
| Archives immuables MinIO | 1,7 Go |
| Images Docker de la stack | 5,2 Go |
| RAM au repos, 16 conteneurs | 2,4 Go |

DS-06 à DS-09 ne sont pas encore importées, et le pic d'un import atteint 3,7 Go temporaires.

| | MVP sur le 35 | Pilote Bretagne, v0.8 |
|---|---|---|
| vCPU | 4 | 8 |
| RAM | 8 Go | 16 Go |
| Disque | 80 Go NVMe | 200 Go NVMe |

Aucune limite mémoire n'est déclarée sur les conteneurs : un import qui dérape peut faire
intervenir l'OOM killer sur n'importe quel service. C'est une dette d'exploitation ouverte, à
traiter avec [G6](../backlog/G6-exploitation-restauration.md).
