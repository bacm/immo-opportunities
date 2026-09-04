# G3 — Carte Bretagne entière et zones non publiables signalées

**Version :** v0.8 · **Taille :** M · **État :** À faire
**Dépend de :** G1 · **Bloque :** G8

## Contexte à charger

- `apps/web/src/RealMap.tsx`
- `map/` (configuration Martin)
- `docs/data/real-map-performance.md`
- `scripts/benchmark-mvt`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le sélecteur 22/29/35/56 et le gate régional sont implémentés : « technique validée, données
absentes ». Ce ticket les alimente en données réelles et vérifie la tenue à l'échelle régionale.

## Travail à réaliser

1. Étendre les tuiles Martin à l'ensemble de la Bretagne, avec les candidats publiés par
   département.
2. Signaler visuellement les zones non publiables selon la matrice de [G2](./G2-matrice-acceptation.md),
   de façon distincte des zones sans candidat — reprise de la logique de [C2](./C2-zone-non-couverte.md)
   à l'échelle régionale.
3. Mesurer les performances aux niveaux de zoom régionaux : latence de génération des tuiles,
   volume transféré, réactivité de la synchronisation carte ↔ liste.
4. Vérifier qu'aucun GeoJSON régional n'est chargé dans MapLibre — interdit explicite. Les
   géométries passent par les tuiles vectorielles.
5. Vérifier que les tuiles ne portent que des attributs de rendu, sans donnée privée
   (cohérence avec [F3](./F3-isolation-organisations.md)).

## Points de vigilance

- Le passage de 1 département à 4 multiplie les volumes : le cadastre seul dépasse les 1,3 million
  de parcelles du 35. Les seuils de simplification et de niveau de zoom doivent être mesurés, pas
  supposés.
- Une zone non publiable doit rester **navigable** : l'utilisateur peut y consulter le cadastre et
  comprendre pourquoi aucun score n'y est publié.
- Ne pas ajouter de bibliothèque frontend pour ce ticket : `App.tsx`, CSS custom et MapLibre.

## Tests obligatoires

- rendu régional aux zooms usuels sans dégradation mesurable ;
- zone non publiable visuellement distincte d'une zone sans candidat ;
- aucun GeoJSON régional chargé ;
- aucun attribut privé dans les tuiles ;
- latence mesurée et comparée aux mesures du 35.

## Critères d'acceptation

- carte régionale fonctionnelle sur les départements retenus ;
- zones non publiables signalées et explicables ;
- mesures de performance publiées ;
- interdits d'architecture respectés.

## Preuve à produire

Mise à jour de [`real-map-performance.md`](../data/real-map-performance.md) avec les mesures
régionales, et captures dans `docs/data/`.
