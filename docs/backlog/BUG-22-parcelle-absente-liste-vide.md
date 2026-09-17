# BUG-22 — Les mutations et les DPE d'une parcelle inconnue rendent une liste vide

**Version :** dette transverse · **Taille :** S · **État :** À faire
**Nature :** implémentation · **Touche :** backend/src/immo/explorer.py, backend/src/immo/api/routes/explorer.py, backend/tests/test_real_map.py
**Dépend de :** — · **Bloque :** —
**Découvert par :** recompte d'A6, 17 septembre 2026

## Contexte à charger

- `SPEC.md` §13 — valeurs manquantes
- `backend/src/immo/api/routes/explorer.py`, routes `/parcels/{parcel_id}/transactions` et
  `/parcels/{parcel_id}/energy-assessments`
- `docs/data/demo-subset-35.md`, section « L'Explorer sur la démo »

## Constat

`/api/v1/parcels/{id}/transactions` et `/api/v1/parcels/{id}/energy-assessments` rendent `200 []`
pour une parcelle absente de la base, y compris un identifiant qui n'existe nulle part
(`parcel:cadastre:35999000ZZ9999`). La fiche de la même parcelle rend 404. « Aucune mutation » et
« parcelle inconnue » deviennent indiscernables : une absence de donnée se lit comme une absence
d'objet. Sur la démo d'A6, une parcelle hors des cinq communes montre 0 mutation là où la base
complète en a 3.

## Travail à réaliser

Rendre 404 quand la parcelle n'existe pas, comme la fiche ; garder `200 []` pour une parcelle
connue sans mutation ni DPE. Régénérer OpenAPI si la réponse 404 est déclarée.

## Critères d'acceptation

- parcelle inconnue : 404 sur les deux routes ;
- parcelle connue sans donnée : `200 []` ;
- tests automatisés ajoutés.
