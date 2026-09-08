# Rapport carte réelle — v0.4

**Date :** 5 août 2026  
**Territoire mesuré :** Ille-et-Vilaine, échantillon Rennes, zoom 15  
**État :** fonctions, API et parcours navigateur validés ; démonstration par adresse bloquée par la release DS-05 inactive.

## Volumes de rendu

| Couche | Entités EPSG:3857 | Zoom minimum | Attributs MVT |
|---|---:|---:|---|
| Parcelles | 1 333 327 | 13 | `id`, `cadastral_id`, `commune_code` |
| Bâtiments | 865 335 | 15 | `id`, `commune_code` |

Les tables `tiles.parcel_render_v1` et `tiles.building_render_v1` sont reconstruites depuis la
release DS-01 active. Elles séparent les géométries de rendu des géométries d'analyse EPSG:2154.
Martin ne possède aucun `SELECT` sur ces tables : les seules sources visibles dans son catalogue
sont les fonctions `parcels(z,x,y)` et `buildings(z,x,y)`.

## Mesures MVT

Commande reproductible :

```bash
make mvt-benchmark
```

Chaque phase appelle 20 tuiles distinctes autour de Rennes. « Froid » désigne le premier passage
sans cache HTTP ; « chaud » rejoue le même échantillon. Le système d'exploitation et PostgreSQL
peuvent conserver des pages entre deux campagnes.

| Couche | p95 premier passage | p95 second passage | Taille tuile centrale |
|---|---:|---:|---:|
| Parcelles | 6,0 ms | 3,7 ms | 79 934 octets |
| Bâtiments | 6,8 ms | 5,3 ms | 121 990 octets |

La liste API exacte sur une emprise rennaise contenant 100 unités mesure 1 839 ms au premier
appel, puis un p95 chaud de 337 ms sur les neuf appels suivants. Le NFR de 500 ms pour une liste
chaude est donc satisfait localement ; le premier appel reste à surveiller avant extension à la
Bretagne.

## Plans et buffers

Après remplacement du prédicat `CASE ... && envelope` par le prédicat indexable
`geom && ST_TileEnvelope(...)` :

| Fonction | Temps `EXPLAIN ANALYZE` | Buffers partagés | Avant optimisation |
|---|---:|---:|---:|
| `tiles.parcels(15,16231,11374)` | 273,8 ms | 1 041 | 99 983 |
| `tiles.buildings(15,16231,11374)` | 72,5 ms | 555 | 57 082 |

Les fonctions `SECURITY DEFINER` restent opaques comme un nœud `Result` dans le plan appelant ;
la chute des buffers et le benchmark HTTP confirment l'usage sélectif des index GiST.

## Sécurité et parcours

- `scripts/check-database-permissions` : `Database role isolation passed.` ;
- catalogue Martin : exactement `parcels` et `buildings` ;
- tuiles servies par Caddy, jamais par FastAPI ;
- Playwright : 1 test passé en 5,2 s, couvrant recherche parcelle, recentrage, navigation clavier,
  sélection, fiche, rechargement de l'URL, attribution et absence de GeoJSON cadastral régional ;
- OpenAPI généré dans `contracts/openapi/v1.json`, client généré dans
  `apps/web/src/generated/api.ts`.

## Recherche d'adresse — mesure du 8 septembre 2026, C1

La limite amont ci-dessous est levée : `DS-05@2026-06-17` est activée en `display_only`, et la
recherche porte sur les 437 441 adresses réelles du 35.

Latence de bout en bout, cinq mesures par requête, API locale sur données réelles :

| Requête | min | médiane | max |
|---|---:|---:|---:|
| `acigne` — nom de commune | 155 ms | 162 ms | 213 ms |
| `rue de la monnaie` | 756 ms | 795 ms | 820 ms |
| `1 rue de la gare` | 857 ms | 898 ms | 1 092 ms |

### Pourquoi une phrase coûte cinq fois plus qu'un mot

Le plan l'explique, et ce n'est pas un index manquant — `address_label_trgm` existe et est
utilisé :

```text
Bitmap Index Scan on address_label_trgm  rows=198606  (47 ms)
Bitmap Heap Scan on address              rows=1986    (730 ms)
  Rows Removed by Index Recheck: 196620
```

L'index trigramme retient **198 606 candidats sur 437 441**, soit 45 % de la table, dont 196 620
sont rejetés à la relecture. Une phrase courante comme « rue de la » partage ses trigrammes avec
presque toutes les adresses du département : la sélectivité de `pg_trgm` s'effondre sur les mots
fréquents, exactement là où l'utilisateur tape le plus.

### Ce que cette mesure tranche pour N13

[N13](../backlog/NICE-backlog.md) conditionne l'introduction d'Elasticsearch à cette mesure.
Elle est faite, et elle ne la justifie pas :

- l'ordre de grandeur reste sous la seconde, sur un poste partagé avec quinze conteneurs ;
- la cause est identifiée et ne relève pas d'un défaut de moteur : c'est la nature de `pg_trgm`
  sur des mots fréquents ;
- deux leviers internes existent avant d'envisager un moteur externe — relever
  `pg_trgm.similarity_threshold` au-delà de 0,3, qui réduirait mécaniquement les candidats, ou
  restreindre le préfiltre trigramme au nom de voie plutôt qu'au libellé complet.

Aucun des deux n'est appliqué ici : les appliquer changerait les résultats retournés, donc ce qui
est affiché à l'utilisateur, et cela mérite d'être décidé sur des cas réels plutôt que sur une
mesure de latence. **Le sujet reste ouvert, documenté, et ne bloque pas C1.**

### Parcours vérifié dans un navigateur

Playwright, 6 tests passés en 7,1 s, dont deux ajoutés par C1 : recherche d'adresse réelle avec
recentrage, liste de résultats sans sélection implicite, appariements visibles avec leur méthode
et leur décision, URL partageable restituant le même état après rechargement, et adresse sans
position affichée avec son motif sans que la carte se recentre.
