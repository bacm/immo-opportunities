# C1 — Recherche adresse réelle FR-001 sur données BAN acceptées

**Version :** v0.4 · **Taille :** M · **État :** À faire
**Dépend de :** B1 · **Bloque :** C2, C3, clôture de v0.4

## Contexte à charger

- `apps/web/src/RealMap.tsx`
- `apps/web/src/api.ts`
- `backend/src/immo/api/routes/spatial.py`
- `backend/src/immo/spatial.py`
- `pipelines/src/immo_pipelines/spatial/ban.py` (`normalize_address_label`)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.4 est bloquée sur un seul point :

```text
- [ ] Recherche et fiches entités connectées — commune et parcelle validées, adresse en attente de DS-05.
```

La recherche par commune et par parcelle fonctionne déjà sur données réelles. Seul le volet adresse
attend l'acceptation de DS-05. Ce ticket est donc une **activation**, pas une construction.

## Exigence produit

FR-001 — recherche par adresse, commune ou parcelle. Une recherche d'adresse doit :

1. recentrer la carte sur l'adresse trouvée ;
2. afficher les entités liées : parcelle, bâtiments, avec leurs sources ;
3. produire une **URL partageable** restituant le même état.

## Travail à réaliser

1. Brancher la recherche d'adresse sur les adresses issues de releases acceptées ou `display_only`,
   jamais sur une release non activée.
2. Vérifier le comportement de la recherche textuelle sur `normalized_label` : le module BAN
   normalise déjà en supprimant accents et ponctuation. Mesurer si `pg_trgm` suffit sur 437 441
   adresses avant d'envisager quoi que ce soit d'autre — voir [NICE](./NICE-backlog.md) N13.
3. Traiter les adresses **sans position** issues de BUG-03 : elles doivent apparaître dans les
   résultats de recherche avec une mention explicite d'absence de localisation, et ne pas recentrer
   la carte silencieusement sur un point arbitraire.
4. Restituer l'état complet dans l'URL : entité sélectionnée, cadrage, filtres actifs.
5. Rester cohérent avec le frontend existant : `App.tsx`, CSS custom, MapLibre. Aucune bibliothèque
   nouvelle introduite pour ce ticket.

## Points de vigilance

- Une adresse trouvée mais sans parcelle rattachée est un cas normal, pas une erreur : elle
  s'affiche avec la relation manquante et son motif (FR-007).
- Le recentrage ne doit pas masquer une ambiguïté : plusieurs résultats plausibles se présentent
  comme une liste, pas comme une sélection automatique du premier.
- Aucune donnée de fixture ne doit subsister dans le chemin de recherche.

## Tests obligatoires

- recherche d'une adresse réelle du 35 : recentrage, entités liées, sources affichées ;
- adresse sans position : présente dans les résultats, non localisée, motif visible ;
- adresse ambiguë : liste de résultats, aucune sélection implicite ;
- URL partageable : rouvrir l'URL restitue le même état ;
- aucune adresse issue d'une release non activée n'apparaît ;
- test Playwright du parcours recherche → fiche.

## Critères d'acceptation

- FR-001 démontrable sur une adresse réelle du 35, sans fixture ;
- URL partageable fonctionnelle ;
- absences visibles et motivées ;
- performance de recherche mesurée et documentée.

## Preuves à produire

- test end-to-end dans la suite existante ;
- mesure de latence ajoutée à [`real-map-performance.md`](../data/real-map-performance.md) ;
- capture de démonstration → [C3](./C3-capture-demo-adresse.md).
