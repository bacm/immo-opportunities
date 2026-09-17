# BUG-21 — Les lots d'une même vente reviennent dans un ordre variable

**Version :** dette transverse · **Taille :** S · **État :** À faire
**Nature :** implémentation · **Touche :** backend/src/immo/explorer.py, backend/tests/test_real_map.py
**Dépend de :** — · **Bloque :** —
**Découvert par :** recompte d'A6, 17 septembre 2026

## Contexte à charger

- `backend/src/immo/explorer.py`, la requête des mutations d'une parcelle
- `docs/data/demo-subset-35.md`, section « L'Explorer sur la démo »

## Constat

`/api/v1/parcels/{id}/transactions` trie par `mutation_date DESC, source_identifier`. Deux lots
d'une même vente partagent ces deux clés : leur ordre change d'un appel à l'autre, sur la base
complète comme sur la démo (35238000DK0446, mutation `v6:2024-429971`). Une liste qui change
d'ordre sans que la donnée change se lit comme une donnée qui change, et empêche toute comparaison
de réponses sans tri préalable.

## Travail à réaliser

Ajouter une clé de tri unique au lot, puis un test sur le texte de la requête.

## Critères d'acceptation

- deux appels successifs rendent la même liste, dans le même ordre ;
- test automatisé ajouté.
