# D5 — Rapports qualité, couverture et fraîcheur par commune

**Version :** v0.5 · **Taille :** M · **État :** À faire
**Dépend de :** D1, D2, D3, D4 · **Bloque :** D6, E1

## Contexte à charger

- `backend/src/immo/market_data.py`
- `backend/src/immo/api/routes/market_data.py`
- `contracts/features/market-data-v1.json`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Les endpoints existent déjà (`/api/v1/market-data/coverage`) et la DoD de v0.5 coche
« Couverture et fraîcheur visibles par commune ». Ce qui manque, ce sont les **mesures réelles** :

```text
- [ ] Imports relançables et rapports qualité produits.
- [ ] Features candidates profilées.
```

## Contenu attendu

### Par source et par commune

| Grandeur | Détail |
|---|---|
| Couverture | part des unités disposant d'une valeur, avec le volume |
| Fraîcheur | date de la donnée la plus récente, et âge au moment du rapport |
| Complétude par feature | valeurs présentes / absentes, **ventilées par motif d'absence** |
| Contradictions | valeurs divergentes entre sources, non arbitrées |

### Par feature candidate

Distribution observée de `MKT-001..005`, `MKT-101..105`, `REN-001..008`, `URB-001..005`,
`RISK-001..004`, `RISK-101` : volume, quantiles, valeurs extrêmes, part absente par motif.

## Points de vigilance

- **La ventilation des motifs d'absence est le cœur du rapport.** `source_not_accepted`,
  « donnée inexistante pour cette unité », « support statistique insuffisant » et
  « appariement ambigu » ont des conséquences différentes sur le scoring. Les agréger en un seul
  taux d'absence rendrait E1 impossible à conduire correctement.
- Les features non supportées dans une commune doivent être **désactivées explicitement**, pas
  affichées comme absentes sans distinction.
- Le rapport doit exposer les cas défavorables : une commune où rien n'est calculable est une
  information utile pour le pilote.
- Aucune valeur agrégée ne doit être publiée sans son volume sous-jacent.

## Tests obligatoires

- le rapport se régénère par une commande, sans intervention manuelle ;
- la somme des valeurs présentes et des absences par motif égale le volume total, par commune ;
- une source non acceptée produit `source_not_accepted` sur toutes ses features, sans exception ;
- une feature désactivée sur une commune n'apparaît pas comme absente pour cause de donnée manquante.

## Critères d'acceptation

- couverture et fraîcheur publiées par source et par commune ;
- distributions de toutes les features candidates publiées ;
- motifs d'absence ventilés ;
- v0.5 peut cocher « Imports relançables et rapports qualité produits » et
  « Features candidates profilées ».

## Preuves à produire

- rapport `docs/data/market-data-quality-35.md` ;
- mise à jour de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- entrée pour [E1](./E1-profiling-distributions.md).
