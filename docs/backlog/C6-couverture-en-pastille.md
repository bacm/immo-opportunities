# C6 — La couverture du territoire devient une pastille dans la barre, sans clignotement

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** apps/web/
**Dépend de :** C5 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « il y a un flicker de données partielles au
niveau de ce bandeau, place-le ailleurs, à gauche de plan/orthophoto, avec une icône warning et un
tooltip au passage ».
**DoD :** preuve sans objet — aucun chiffre publié ; les tests e2e portent la preuve

## Contexte à charger

- `apps/web/src/App.tsx`, `apps/web/src/CoverageBanner.tsx`, `apps/web/tests/e2e/real-map.spec.ts`

## Choix retenus

- **Deux causes** : le bandeau s'insérait au-dessus de la grille et décalait la carte ; et la
  commune observée repassait à « aucune » pendant le chargement de chaque fiche, ce qui effaçait
  puis réaffichait le bandeau.
- **Pastille** dans la barre du haut, à gauche du choix de fond : icône (coche ou alerte), nom de
  la commune et état court. Le texte complet — sens de l'état, sources absentes nommées — est
  dans une infobulle, ouverte au survol **et au focus clavier** (`role="tooltip"`,
  `aria-describedby`), sans bibliothèque.
- **Commune observée gardée pendant un chargement** : elle ne change qu'une fois la nouvelle
  fiche chargée, et s'efface quand aucune fiche n'est ouverte. La pastille nomme toujours sa
  commune ; elle n'affirme donc jamais un état sans dire de quel territoire il s'agit.
- **Tests** : les tests de couverture survolent la pastille pour lire l'infobulle ; les
  affirmations restent les mêmes.

## Critères d'acceptation

- plus aucun bandeau au-dessus de la carte ;
- l'infobulle s'ouvre au survol et au focus ;
- passer d'une parcelle à une autre de la même commune ne fait pas disparaître la pastille ;
- `pnpm test:e2e` et `make check` verts.

## Vérification — 16 septembre 2026

- `pnpm test:e2e` : 18 réussis, 2 sautés par leur garde ; nouveau test : la pastille ne quitte
  jamais le DOM en passant d'une parcelle à un de ses bâtiments ; l'infobulle s'ouvre au focus ;
- `make check` vert.
