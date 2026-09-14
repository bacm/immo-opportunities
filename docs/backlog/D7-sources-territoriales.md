# D7 — DS-10 population et DS-11 équipements : les variables qui séparent les marchés

**Version :** v0.5 · **Taille :** L · **État :** À faire
**Dépend de :** D1 · **Bloque :** E6
**Demandé par :** conversation du 14 septembre 2026, à la clôture de D1

## Contexte

[D1](./D1-import-dvf-ds06.md) a renvoyé les **segments de marché** à
[E1](./E1-profiling-distributions.md), en laissant une mesure parlante : le prix au m² d'un
terrain va de **1 € à 181 € entre quartiles**, parce qu'il mêle terres agricoles et terrains à
bâtir. Un comparable tiré sans segment est un comparable faux.

`scoring.segment_definition` existe déjà, en `draft`, avec cinq segments — `rural`, `coastal`,
`periurban`, `medium_city`, `metropolitan` — et `thresholds: profiling_required`. Le mécanisme
attend ses variables.

La stratification de [B4](./B4-revue-manuelle-appariements.md) en a utilisé deux, faute de mieux :
la limite terre-mer de la BD TOPO pour le littoral, et les tercies du **nombre de parcelles par
commune** comme approximation de densité. La seconde est un proxy grossier : elle confond une
commune dense et une commune très découpée.

Ce ticket apporte les variables qui manquent.

## Ce que le produit possède déjà, et ce qu'il n'a pas

| Variable | État |
|---|---|
| Classification littorale | existe — limite terre-mer BD TOPO |
| Distance aux pôles urbains | **calculable** — géométries de communes en base |
| **Population communale** | **absente** — source à importer |
| **Équipements : commerces, écoles, santé** | **absentes** — source à importer |

## Travail à réaliser

1. **DS-10 — population et logements.** Recensement INSEE au niveau communal. Contrat, manifeste
   checksumé, import relançable, verdict d'acceptation motivé. Millésime figé, jamais un alias.
2. **DS-11 — équipements.** Base permanente des équipements de l'INSEE, ou les points d'intérêt
   de la BD TOPO si leur couverture est suffisante — à instruire, pas à présumer.
3. **Distance aux pôles** calculée depuis `reference.area`, sans nouvelle source.
4. Publier la distribution observée de chaque variable sur le 35, comme entrée de
   [E6](./E6-segmentation-observee.md).

## Points de vigilance

- **Ces variables décrivent une commune, pas une parcelle.** Les rattacher à une parcelle est une
  jointure administrative, pas une mesure : une commune n'est pas homogène, et une variable
  communale appliquée à une parcelle porte une incertitude qui doit rester visible.
- **Aucun seuil ici.** Ce ticket importe et mesure ; découper appartient à E6, sur distribution
  observée.
- **Une couverture partielle est un résultat.** Si la BPE ne couvre pas certaines communes, elles
  portent une variable absente avec motif, jamais une valeur imputée.

## Critères d'acceptation

- deux releases réelles, archivées, checksumées, importées et auditées sur le 35 ;
- verdict d'acceptation écrit pour chacune ;
- distributions publiées dans `docs/data/` ;
- aucune variable imputée, aucune moyenne de substitution.
