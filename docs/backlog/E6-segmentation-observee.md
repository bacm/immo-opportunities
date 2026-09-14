# E6 — Segmenter les marchés sur distribution observée, et mesurer ce que ça change

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Dépend de :** D7, E1 · **Bloque :** E2
**Demandé par :** conversation du 14 septembre 2026

## Contexte

`scoring.segment_definition` est en `draft` depuis le 4 septembre 2026 avec
`thresholds: profiling_required`. Cinq segments sont nommés — `rural`, `coastal`, `periurban`,
`medium_city`, `metropolitan` — et aucun n'a de frontière.

[D1](./D1-import-dvf-ds06.md) a montré pourquoi cela bloque : sans segment, le prix au m² d'un
terrain s'étend de **1 € à 181 € entre quartiles**, mêlant terres agricoles et terrains à bâtir.
Un comparable tiré sans segment est un comparable faux, et une médiane calculée dessus est une
fausse précision.

## Travail à réaliser

1. Placer les frontières des cinq segments sur la **distribution observée** des variables de
   [D7](./D7-sources-territoriales.md) — population, équipements, distance aux pôles,
   classification littorale. Jamais sur un découpage administratif ni sur une valeur choisie.
2. Passer `segment_definition` de `draft` à publiable, avec sa justification et sa version.
3. **Mesurer ce que la segmentation change**, et c'est le cœur du ticket : dispersion du prix au m²
   à l'intérieur d'un segment contre dispersion départementale. Une segmentation qui ne réduit pas
   la dispersion ne sert à rien et doit être rejetée plutôt qu'adoptée par principe.
4. Recalculer le support statistique par segment et non plus par commune — c'est l'enjeu réel :
   **152 communes seulement** atteignent 30 ventes de maison exploitables sur cinq ans, et un
   segment bien tracé doit en faire bénéficier les 180 autres.

## Ce que ce ticket ne doit pas faire

- **Prédire.** Segmenter regroupe des communes comparables pour y calculer des médianes
  **observées** ; cela ne produit aucune valeur là où il n'y a pas de transaction. La frontière
  est explicite et elle est traitée par [E7](./E7-decision-valorisation.md).
- **Sauver une commune sans données.** Une commune sans comparable exploitable dans son segment
  garde une feature absente motivée et une confiance réduite. D1 l'a déjà tranché.

## Critères d'acceptation

- frontières issues de distributions publiées, chacune justifiée par écrit ;
- réduction de dispersion mesurée et publiée, y compris si elle est faible ;
- support statistique par segment publié, avec le nombre de communes qui en bénéficient ;
- `segment_definition` versionnée et publiable.
