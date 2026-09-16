# BUG-18 — Un terrain à plusieurs natures de culture est prié sur la surface d'une seule

**Version :** dette transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/src/immo_pipelines/market_data/dvf.py, pipelines/tests/test_dvf_allocation.py, docs/data/dvf-quality-35.md
**Dépend de :** H7 · **Bloque :** —
**Découvert par :** recompte de H7, 16 septembre 2026 (« la dédup par parcelle rend allouable une
parcelle vendue seule avec deux cultures ; ce choix n'est écrit nulle part »)
**DoD :** preuve dans `docs/data/dvf-quality-35.md`, recomptée

## Contexte à charger

- `SPEC.md` §13.7, §13.9 — ces sections seulement
- `pipelines/src/immo_pipelines/market_data/dvf.py`
- `docs/backlog/H7-mutations-multi-parcelles.md`, section « Résultat »

## Constat

`geo-dvf` publie une ligne par (bien, nature de culture). Une parcelle vendue seule, en « terres »
et en « prés », donne deux lignes de terrain aux surfaces différentes. La déduplication des lots
les fusionne en un lot — c'est juste : c'est un seul bien — mais **garde la surface de la première
ligne seulement**, et le prix de l'acte lui est rapporté.

Mesuré en base, version 5 : **1 228** ventes de terrain sur 2021-2025 et **1 733** sur 2014-2020
portent un prix alloué sur une surface partielle ; la surface réelle de la parcelle vendue est en
médiane **2,17** et **2,14** fois plus grande. Leur prix au m² est donc surévalué d'autant.

Le baromètre n'en est pas touché : il ne lit que les maisons et appartements. Le sont la
distribution des prix de terrain de `dvf-quality-35.md` et les comparables de terrain des
features `MKT`.

## Choix retenus

- **Surface d'un lot de terrain** : la somme des surfaces de ses natures de culture distinctes
  sur la même parcelle — triplet (parcelle, nature, surface). Un bien bâti garde sa surface bâtie.
- **Stockage** : la ligne qui porte le prix reçoit la surface totale et la méthode
  `single_land_lot_all_cultures` quand le lot compte plusieurs cultures ; la surface par culture
  reste dans les propriétés brutes de chaque ligne. Aucun prix n'est réparti entre cultures : ce
  serait l'inventer.
- **Archive DGFiP** : la nature de culture n'y est pas convertie ; deux cultures de même surface
  sur une parcelle y comptent une fois. Écrit dans le rapport.
- **Transformation version 6**, réimport des deux releases DS-06 ; le baromètre régénéré doit
  garder son empreinte.

## Critères d'acceptation

- un terrain à deux cultures porte la surface des deux ;
- le baromètre garde l'empreinte `9faf338138a6758e` ;
- la distribution des prix de terrain de `dvf-quality-35.md` est recalculée et recomptée ;
- `make check` vert.

## Résultat — 16 septembre 2026

- Transformation DVF **version 6** ; les deux releases DS-06 réimportées (133 066 actes 2021-2025,
  179 573 actes 2014-2020, toutes lignes `v6:`).
- **2 961** lignes `single_land_lot_all_cultures` (1 228 + 1 733), toutes de type Terrain, chacune
  à au moins deux cultures, dont la surface égale la somme recomptée. Aucune ligne de terrain à
  prix plein n'a deux cultures réelles.
- Distribution des prix de terrain : médiane **61 €** (64 € en version 5) sur 19 775 lots, dont
  1 171 corrigés ; maisons, appartements et locaux inchangés.
- Baromètre régénéré : empreinte `9faf338138a6758e` inchangée.
- Recompte `recompte-preuve` : tous les chiffres confirmés ; les formulations de périmètre
  (1 228 hors filtre du tableau, culture de référence, actes sans parcelle) sont précisées dans
  le rapport.
- Écart de formulation au constat : les actes sans parcelle (45 et 151 lignes) rapprochent leurs
  cultures par acte, non par parcelle ; aucun ne mêle de parcelles.
