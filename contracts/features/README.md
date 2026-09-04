# Contrats de features

Chaque feature déclare son code, sa stratégie, ses datasets, sa formule, son unité, sa plage valide, son comportement hors plage et sa politique `required`, `optional` ou `confidence_only`.

Les premières définitions morphologiques sont livrées dans
[`morphology-v1.json`](./morphology-v1.json) par `v0.3-spatial-reference`. Une valeur absente
porte un motif explicite ; elle ne devient jamais zéro. `BLD-001` à `BLD-003` ciblent un
bâtiment résolu, les features `LAND-*` une `PropertyUnit`.

Le catalogue [`market-data-v1.json`](./market-data-v1.json) versionne `MKT-001` à `MKT-005`,
`MKT-101` à `MKT-105`, `REN-001` à `REN-008`, `URB-001` à `URB-005`, `RISK-001` à
`RISK-004` et `RISK-101`. Il interdit notamment les DPE simulés, l'interprétation libre des
règlements et la conversion d'un risque communal en exposition parcellaire.
