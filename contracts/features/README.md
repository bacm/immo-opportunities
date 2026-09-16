# Contrats de features — non lus par le code

Chaque feature déclare code, stratégie, datasets, formule, unité, plage valide, comportement hors
plage et politique `required` / `optional` / `confidence_only`.

[`morphology-v1.json`](./morphology-v1.json) couvre `LAND-*` et `BLD-*` ;
[`market-data-v1.json`](./market-data-v1.json) couvre `MKT-*`, `REN-*`, `URB-*` et `RISK-*`.

**Ces fichiers ne sont lus par aucun code.** Les plages, exigences et motifs de manquant sont
réimplémentés à la main dans `market_data/features.py` ; rien ne détecterait une divergence
(audit §8.4). Une valeur absente porte un motif explicite et ne
devient jamais zéro : cette règle, elle, est appliquée dans le code.
