# Martin

Martin se connecte avec le rôle PostgreSQL `martin`, membre de `tiles_ro`. Ce rôle possède uniquement `USAGE` sur le schéma `tiles` et `EXECUTE` sur les fonctions MVT explicitement publiées :

- `tiles.parcels(z, x, y)` ;
- `tiles.buildings(z, x, y)`.

Les routes publiques stables `/tiles/v1/parcels/{z}/{x}/{y}.mvt` et `/tiles/v1/buildings/{z}/{x}/{y}.mvt` sont réécrites vers ces sources Martin par Caddy (et par Vite en développement).

Les tables `tiles.*_render_v1` sont des copies de rendu en EPSG:3857, séparées des géométries d’analyse en EPSG:2154. Elles sont reconstruites avec `tiles.refresh_render_v1(department_code)` après publication d’une release cadastrale.

L’auto-publication des tables applicatives est interdite. Martin ne dispose d’aucun droit sur `reference`, `meta`, `app` ou `audit`, ni même de `SELECT` direct sur les tables de rendu.
