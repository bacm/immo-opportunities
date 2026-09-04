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

## Limite amont

La recherche commune et parcelle utilise les données réelles actives. La recherche d'adresse est
implémentée mais filtre volontairement les adresses dont la release DS-05 n'est pas acceptée. La
démonstration « adresse du 35 » ne pourra donc être validée qu'après résolution des contrôles
bloquants BAN documentés dans le rapport du référentiel spatial.
