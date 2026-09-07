# BUG-06 — PostgreSQL tourne avec le `postgresql.conf` d'initdb

**Version :** dette transverse · **Taille :** S · **État :** Terminé
**Dépend de :** — · **Bloque :** —
**Découvert par :** question de dimensionnement VPS, 7 septembre 2026

## Contexte à charger

- `compose.yaml`, service `postgres`
- `scripts/check-compose-config`
- `docs/operations/postgresql-tuning.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Aucun réglage PostgreSQL n'existait dans le dépôt : ni dans `compose.yaml`, ni dans
`infra/ansible/`. Le serveur tournait avec le `postgresql.conf` généré par `initdb`, dont les
valeurs visent une base de quelques centaines de méga-octets, sur une base de **14 Go** pour le
seul département 35.

Diagnostic initial : un parcours de `meta.entity_source_observation` rapportait
`shared hit=119 read=515925`, soit 99,98 % du travail hors du cache de PostgreSQL.

## Ce qui a été mesuré

**Le levier réel était `work_mem`, pas `shared_buffers`.** Agrégat sur 1,4 M lignes, paramètre
réglé par session pour isoler son effet :

| `work_mem` | Lots | Débordement disque | Temps |
|---|---:|---:|---:|
| 4 Mo — le défaut | 17 | 68 Mo | 1 520 ms |
| 64 Mo | 1 | aucun | 475 ms |

3,2× plus rapide. C'est ce qui ralentissait les requêtes d'agrégation des importeurs.

**`shared_buffers` n'a donné aucun gain mesurable** malgré le diagnostic : le cache de pages du
système absorbait déjà ces lectures sur le poste de développement. Le réglage est conservé comme
un pari documenté pour le VPS, où PostgreSQL partage 16 Go avec quinze autres conteneurs.

`maintenance_work_mem` : 12 % sur une construction d'index GiST. Marginal à cette échelle.

Quatre paramètres restent des **hypothèses non mesurées**, et le document le dit :
`random_page_cost`, `effective_io_concurrency`, `max_wal_size`, `checkpoint_timeout`.

## Ce qui a été fait

1. Réglage en arguments `-c` du service `postgres` dans `compose.yaml`, chaque valeur
   surchargeable par variable d'environnement, documentée dans `.env.example`.
2. `scripts/check-compose-config` échoue si l'un des paramètres mesurés disparaît de la
   configuration rendue. Appelé par `make config`, donc par `make check`.
3. Preuve et limites consignées dans
   [`docs/operations/postgresql-tuning.md`](../operations/postgresql-tuning.md), avec le
   dimensionnement d'hôte mesuré.

## Critères d'acceptation

- ✅ le réglage vit dans le dépôt et non dans la mémoire de l'opérateur ;
- ✅ chaque valeur est soit mesurée, soit déclarée comme hypothèse ;
- ✅ un contrôle automatique échoue si le réglage disparaît.

## Ce qui reste ouvert

Aucune limite mémoire n'est déclarée sur les conteneurs : un import qui dérape peut faire
intervenir l'OOM killer sur n'importe quel service. À traiter avec
[G6](./G6-exploitation-restauration.md).
