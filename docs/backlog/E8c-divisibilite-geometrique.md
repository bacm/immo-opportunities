# E8c — Mesurer la divisibilité par la forme du terrain libre, pas par sa surface

**Version :** v0.6 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/tests/test_exploratory_candidates.py, docs/data/exploratory-candidates/
**Dépend de :** E8b · **Bloque :** E9
**Découvert par :** seconde relecture manuelle, 15 septembre 2026

## Contexte à charger

- `docs/backlog/E8b-usage-du-bati.md`
- `pipelines/src/immo_pipelines/spatial/features.py` (`LAND-007` seulement)
- `docs/data/exploratory-candidates-35051.md`

Ne rien charger d'autre sans nécessité démontrée.

## Le constat

Après [E8b](./E8b-usage-du-bati.md), la liste ne contient plus que du résidentiel individuel, et le
motif de rejet devient unique : **« la maison est trop centrée pour déparcelliser »**. Quatre cas
sur six le portent — `35051000AZ0112`, `35051000ZT0176`, `35051000ZS0175`, `35051000YA0032` — et un
cinquième, `35051000ZS0176`, l'aggrave d'une emprise trop grande au milieu du terrain.

## Un défaut de classement, et une mesure qui manquait

### `LAND-007` était classée à l'envers

`LAND-007 = distance(union(bâtiments), boundary(unité))` est la distance **minimale** du bâti à la
limite parcellaire. Le classement de [E8](./E8-liste-exploratoire-terrain.md) l'ordonnait en
**décroissant** : il remontait donc en tête les maisons les plus éloignées de toute limite, c'est-à-
dire **les plus centrées** — exactement l'inverse de ce que la division demande. Défaut simple, à
corriger sans discussion.

### La surface libre ne dit rien de la divisibilité

`LAND-004 = LAND-001 - LAND-002` mesure une **aire**. Une maison plantée au centre laisse un anneau
libre de grande aire, connexe, et inutilisable. Mesuré sur les onze parcelles relues : le plus grand
morceau libre d'un seul tenant représente **75 % à 91 %** de la parcelle, rejetées et retenues
confondues. La mesure ne sépare rien.

Ce qu'il faut est une mesure de **forme** : peut-on inscrire un lot dans la partie libre ?
`ST_MaximumInscribedCircle` sur le terrain libre, bâti tamponné du recul, donne sur le même
échantillon une plage de **7,3 m à 15,6 m** — et les quatre « trop centrée » sont à 7,3, 8,6, 8,9
et 9,2.

### `usage_1` se contredit avec `nature`

`35051000AT0066` — un parking d'entreprise — porte `usage_1 = Résidentiel` **et**
`nature = « Industriel, agricole ou commercial »`. BD TOPO classe 100 431 bâtiments sous cette
nature. Le filtre d'usage de E8b ne la lit pas ; il doit la lire.

## Ce que ce ticket n'est pas en mesure de faire, et le dit

Deux motifs de rejet relevés n'ont **aucune source dans le dépôt** :

- **« le tout est déjà goudronné »** — couverture du sol. OCS GE est cité en `SPEC.md` §27, non
  importé, sans contrat DS-*.
- **« il y a une piscine sur le terrain »** — BD TOPO n'importe que la couche bâtiment ; les
  constructions surfaciques n'y sont pas.

Ces deux limites sont publiées dans le rapport. Les deviner depuis la morphologie serait inventer.

`35051000ZS0176` reste par ailleurs un **cas manqué assumé** : rayon inscriptible 11,5 m, usage et
nature résidentiels, un logement. Rien dans les sources disponibles ne porte le jugement « maison
trop grande et plein milieu » qui l'a fait rejeter. Il est consigné comme tel plutôt qu'écarté par
un seuil taillé sur lui.

## Travail à réaliser

1. Inverser le sens de `LAND-007` dans le classement.
2. Calculer, pour les seules unités ayant passé les filtres d'attribut, le rayon du plus grand
   cercle inscriptible dans la partie libre — bâti tamponné du recul, `ST_Dump` des composantes.
3. Classer sur ce rayon plutôt que sur `LAND-004`, et exiger un rayon minimal déclaré arbitraire.
4. Écarter les bâtiments dont `nature` est explicitement non résidentielle.
5. Afficher la distance de la partie libre à la voirie **comme preuve**, sans filtrer dessus :
   sur l'échantillon relu elle ne sépare que `AT0066`, que `nature` écarte déjà.
6. Publier les deux limites sans source, et le cas manqué.

## Tests obligatoires

- une parcelle au bâti collé à une limite est mieux classée qu'une parcelle au bâti centré, à
  surface libre égale ;
- une `nature` non résidentielle écarte, `Indifférenciée` n'écarte pas ;
- un rayon inscriptible absent — géométrie manquante — reste absent avec son motif, jamais zéro ;
- `LAND-007` est bien ordonnée en croissant.

## Critères d'acceptation

- le classement ne remonte plus les maisons centrées ;
- le rayon inscriptible est calculé sur le vivier éligible seulement, et publié par candidat ;
- les motifs sans source sont écrits dans le rapport ;
- le cas manqué `35051000ZS0176` est consigné, pas neutralisé par un seuil ad hoc ;
- les seuils de E8 restent inchangés.

## Preuve à produire

`docs/data/exploratory-candidates-35051.md`, régénéré : rayon inscriptible et distance à la voirie
par candidat, limites sans source, cas manqué consigné.
