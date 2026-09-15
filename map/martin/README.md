# Martin

Rôle PostgreSQL `martin`, membre de `tiles_ro` : `USAGE` sur `tiles` et `EXECUTE` sur trois
fonctions, `tiles.parcels`, `tiles.buildings`, `tiles.opportunities`. Aucun `SELECT` direct sur les
tables de rendu, auto-publication désactivée, testé par
`backend/tests/test_real_map_migration_contract.py`.

Routes `/tiles/v1/{parcels,buildings,opportunities}/{z}/{x}/{y}.mvt` réécrites par Caddy en
production et par Vite en développement — deux implémentations de la même règle.

**Aucune authentification devant Martin.** `tiles.opportunities` expose `score`,
`confidence_level` et `property_unit_id` ; le `forward_auth` prévu par l'architecture initiale
n'existe pas. Sans conséquence tant qu'aucun score n'est publié ; bloquant avant.
