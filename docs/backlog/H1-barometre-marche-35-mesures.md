# H1 — Baromètre du marché du 35 : les mesures, reproductibles et recomptées

**Version :** V5 · baromètre · **Taille :** L · **État :** À faire
**Nature :** implémentation · **Touche :** pipelines/scripts/market_barometer.py, pipelines/tests/test_market_barometer.py, Makefile, docs/data/barometre-marche-35.md, docs/data/barometre-marche-35/
**Dépend de :** A7 · **Bloque :** H2
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)

## Contexte à charger

- `docs/data/pistes-analyse-marche-35.md` (sections 2, 5.1, 5.2 et les SQL de `pistes-analyse-marche-35/`)
- `docs/data/dpe-signal-vente-35.md` (limites, et l'écart de comptage 14 532 / 9 754)
- `docs/data/dvf-quality-35.md` (prix non allouable, doublons de versions de transformation)
- `pipelines/scripts/market_listing_candidates.py` (comment E8f nomme sa cohorte et son filtre)
- `.claude/skills/recompte-preuve/SKILL.md`

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket produit

Un script `make market-barometer DEPARTMENT=35` qui régénère `docs/data/barometre-marche-35.md`
et un répertoire de tableaux CSV, à partir des seules tables `observation.transaction`,
`observation.energy_assessment` et du référentiel spatial. **Aucune source nouvelle, aucun
score, aucune parcelle nommée** : toutes les mesures sont agrégées par commune, EPCI ou
département, avec leur support.

## Les mesures

Toutes existent déjà sous forme de sondages « non recomptés » dans `pistes-analyse-marche-35.md`
§5. Ce ticket les rend reproductibles, les nomme, et les recompte.

| Mesure | Granularité | Ce qu'elle dit au professionnel |
|---|---|---|
| Volumes et prix médians au m², maisons et appartements | EPCI × année, commune × année si support | le marché tel qu'il est |
| Plus-value nette de marché par prix d'entrée (ventes répétées) | département, EPCI si support | où est la marge d'un marchand |
| Décote ou surcote par étiquette DPE, contrôle commune × année | département, EPCI si support | ce que vaut réellement une passoire |
| Délai dépôt DPE → acte, quartiles | commune (support ≥ 200), EPCI | délai de vente observé |
| Taux de mutation à 12 mois après premier DPE, par cohorte annuelle | commune (support ≥ 200), EPCI, département | la température du marché |
| Courbe de conversion mensuelle, cohorte la plus récente couverte | département, EPCI | quand un bien mis en vente part |
| Effet de l'extension de surface bâtie sur le prix total et au m² | département | ce que rapporte un agrandissement |
| Part des mutations sans prix allouable, part des DPE non rattachés | commune | ce que le baromètre ne voit pas |

## Règles

- **Le filtre de chaque cohorte est écrit dans la sortie**, en clair : relations bâtiment ↔ parcelle
  retenues, premier DPE par parcelle ou par bâtiment, types de bâtiment exclus. C'est la leçon de
  l'écart 14 532 / 9 754 : un effectif sans son filtre n'est pas reproductible.
- **Un taux ne paraît jamais sans son effectif**, et un seuil de support n'est pas un seuil
  inventé : il est déclaré comme paramètre du script et affiché.
- **Les DPE d'appartement générés depuis un DPE d'immeuble sont exclus** des mesures de conversion
  (0,6 %, mesuré), et l'exclusion est comptée.
- **La réforme DPE du 1er janvier 2026** (coefficient électricité) est une rupture de série : les
  mesures par étiquette distinguent avant et après, ou portent la réserve en toutes lettres.
- **DVF s'arrête au 31 décembre 2025** : aucune cohorte dont les douze mois ne sont pas couverts
  n'entre dans un taux à douze mois.
- Aucune valeur manquante n'est convertie en zéro ; une commune sans support apparaît « sans
  support » avec son effectif.

## Ce que ce ticket ne fait pas

- Il ne publie aucune parcelle ni aucune adresse. Le radar nominatif est H5, derrière H4.
- Il n'estime la valeur d'aucun bien non vendu (E7 reste suspendu).
- Il n'introduit ni modèle hédonique ni pondération : contrôle commune × année seulement, comme
  dans les sondages.

## Critères d'acceptation

- `make market-barometer` régénère le rapport à l'identique sur la même base (graine et filtres
  écrits) ;
- tests : chaque mesure a un test sur fixture minimale, dont un cas « support insuffisant » et un
  cas « cohorte non couverte par DVF » ;
- `recompte-preuve` a été passé sur le rapport avant `Terminé`, et l'écart 14 532 / 9 754 de
  `dpe-signal-vente-35.md` est soit expliqué, soit remplacé par l'effectif du filtre écrit ;
- `make check` vert.
