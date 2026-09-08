# C3 — Capture de démonstration adresse 35

**Version :** v0.4 · **Taille :** S · **État :** Terminé
**Dépend de :** C1, C2 · **Bloque :** clôture de v0.4

## Contexte à charger

- `docs/versions/v0.4-real-map.md`
- `apps/web/tests/e2e/real-map.spec.ts`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

La démonstration attendue de v0.3 et v0.4 est explicite : « rechercher une adresse réelle, afficher
sa parcelle, ses bâtiments et leurs sources, puis comparer un appariement certain à un cas ambigu ».

C'est la première preuve visuelle que la chaîne fonctionne de bout en bout sur des données réelles.
Elle doit être archivée dans `docs/data/`, pas seulement montrée une fois.

## Contenu attendu

Séquence de captures sur une adresse réelle du 35, avec pour chacune la date, la release affichée
et l'environnement :

1. recherche d'une adresse réelle et recentrage ;
2. fiche de l'entité : parcelle, bâtiments, sources et dates de chaque valeur ;
3. un appariement **certain** avec sa méthode et sa confiance ;
4. un appariement **ambigu**, montrant que l'ambiguïté est visible et non masquée ;
5. une valeur absente avec son motif (FR-007) ;
6. les trois états de couverture de [C2](./C2-zone-non-couverte.md).

## Résultat au 8 septembre 2026

Sept captures archivées dans [`docs/data/captures/`](../data/captures/), commentées dans
[`real-map-address-demo-35.md`](../data/real-map-address-demo-35.md). Aucune fixture : le script
`apps/web/tests/e2e/demo-capture.spec.ts` n'intercepte aucune route, et il est exclu de
`pnpm test:e2e` pour ne s'exécuter que délibérément, par `pnpm --filter @immo/web capture:demo`.

Les deux adresses sont choisies pour ce qu'elles montrent de difficile, pas parce qu'elles
« marchent bien » : l'une porte **à la fois** un appariement certain à 0,99 et un ambigu à 0,80
vers deux parcelles différentes ; l'autre est une des 216 adresses réelles dont la position a été
retenue par la quarantaine de [BUG-03](./BUG-03-quarantaine-par-attribut.md).

| Élément attendu | Couvert |
|---|---|
| 1. recherche et recentrage | oui, capture 02 — liste sans sélection implicite |
| 2. fiche, entités liées, sources | oui, captures 03 et 05 |
| 3. appariement certain avec méthode et confiance | oui, capture 05 |
| 4. appariement ambigu, visible et non masqué | oui, capture 05 — section distincte |
| 5. valeur absente avec motif (FR-007) | oui, capture 07 |
| 6. les trois états de couverture de C2 | **partiellement** — voir ci-dessous |

## Ce que la démonstration a révélé

**La carte est vide au cadrage par défaut.** `parcels` déclare `minzoom 13` : rien ne se rend
au-dessus du département. Ce n'est pas un défaut mais l'ADR MapLibre appliqué — aucun GeoJSON
régional. Les captures fixent donc `z=16.00` dans l'URL, et cela méritait d'être écrit quelque
part : la première capture produite montrait une carte vide, ce qui aurait pu passer pour une
panne.

## Ce qui n'est pas couvert, et pourquoi

**Seul l'état `partial` de C2 est démontrable sur données réelles.**

- `covered` exigerait que DS-02 soit publiée, donc [B4](./B4-revue-manuelle-appariements.md) ;
- `not_covered` exigerait une commune chargée sans aucune source active. `reference.area` ne
  contient que les 332 communes du 35, toutes couvertes : une commune du 22 renvoie 404. Ce cas
  ne se vérifiera qu'à [G1](./G1-extension-22-29-56.md).

Les deux états sont implémentés et couverts par des tests end-to-end à routes simulées. Une
capture de ces états serait une capture de simulation, donc elle ne vaudrait pas preuve — le
ticket l'interdit explicitement, et elle n'est pas produite.

**v0.4 peut être passée à `Terminée`** pour ce que ses tickets couvrent, mais la démonstration de
couverture complète attend B4. C'est une décision de clôture de version, pas de ticket.

## Points de vigilance

- Aucune capture ne doit provenir d'un environnement de fixture. Si une donnée de démonstration
  apparaît, elle doit être identifiée comme telle — mais alors la capture ne vaut pas preuve.
- Ne pas choisir uniquement une adresse « qui marche bien » : le cas ambigu et le cas absent sont
  la partie intéressante de la démonstration.
- Les captures doivent mentionner la release exacte, sinon elles ne sont pas rejouables.

## Critères d'acceptation

- captures archivées dans `docs/data/` avec leur contexte ;
- les six éléments ci-dessus sont couverts ;
- la démonstration est reproductible depuis les releases citées ;
- v0.4 peut être passée à `Terminée`.

## Preuve à produire

`docs/data/real-map-address-demo-35.md` et les captures associées.
