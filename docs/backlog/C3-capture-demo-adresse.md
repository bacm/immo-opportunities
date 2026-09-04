# C3 — Capture de démonstration adresse 35

**Version :** v0.4 · **Taille :** S · **État :** À faire
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
