# D5 — Rapports qualité, couverture et fraîcheur par commune

**Version :** v0.5 · **Taille :** M · **État :** Terminé
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

## Résultat — 15 septembre 2026

**Preuve :** [`market-data-quality-35.md`](../data/market-data-quality-35.md), régénéré par
`make market-data-quality`.

Couverture, fraîcheur, complétude ventilée par motif et distributions publiées pour les quatre
sources. L'invariant que le ticket impose — présentes + absences par motif = volume total, par
feature — est **vérifié dans le rapport lui-même**, colonne par colonne, et non affirmé à côté.

### Ce que le rapport a trouvé et que les rapports par source ne pouvaient pas voir

**Deux imports métier n'écrivent aucun run.** Le défaut ne se lit qu'en comptant les runs par
source, ce qu'aucun rapport par source ne fait. `DS-08@2026-09-14` en reste `pending` : la porte
d'acceptation refuse une release sans import traçable, à juste titre. `DS-06@2026-09-13`, lui,
porte `display_only` **sans qu'aucun run ne l'appuie** — rien en base ne relie ses 133 066
transactions à un import identifié, daté et rejouable. Ouvert en
[BUG-14](./BUG-14-import-gpu-sans-trace.md).

**Un motif d'absence qui en dit un autre.** `compute_urban_features` émet `source_not_accepted`
pour signifier « aucune zone opposable ne couvre cette parcelle » — le RNU, ou une commune sans
document. 776 499 absences `URB-001` se lisent donc « DS-08 inutilisable » alors que 554 714
parcelles portent une valeur réelle. Le ticket pose que confondre les motifs rend E1 impossible à
conduire correctement ; c'en est le cas d'espèce. Même ticket.

**La correction a été commencée puis annulée, volontairement.** Relabelliser sans ajouter la
garde d'acceptation aurait livré une moitié de correctif : tant que `compute_urban_features` ne
vérifie aucun verdict, le bon motif au mauvais moment reste faux. BUG-14 porte les deux moitiés.

### Un écart de vocabulaire, publié sans être arbitré

Le BRGM cartographie l'exposition aux argiles sur 332 communes. GASPAR recense les risques
commune par commune et **n'écrit jamais « Retrait-gonflement des argiles »** sur le 35 : il écrit
« Tassements différentiels », sur 76 communes. Décréter l'équivalence serait la faute commise sur
le champ `ETAT` du CNIG pendant D2. Les deux vocabulaires sont publiés côte à côte ; les combler
demande la table du producteur, et c'est une entrée pour [E1](./E1-profiling-distributions.md).

### Ce qui n'est pas profilable, et pourquoi

`MKT-*` se calculent au moment du score à partir des comparables — leurs segments relèvent de E1.
`REN-*`, `RISK-*` et `BLD-*` attendent [BUG-13](./BUG-13-sujet-des-features-batiment.md) : le
sujet des features de bâtiment. Leurs distributions d'observations existent, dans les rapports par
source.

### Ce que v0.5 peut cocher, et ce qu'elle ne peut pas

« Couverture et fraîcheur visibles par commune » : **oui**. « Imports relançables et rapports
qualité produits » : **partiellement** — les rapports existent, deux imports sur quatre ne sont
pas traçables. « Features candidates profilées » : **partiellement** — `LAND-*` et `URB-*` le
sont, les familles de bâtiment attendent BUG-13.
