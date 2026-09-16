# Ventes DVF sur plusieurs parcelles — 35

**Généré le** 2026-09-16 par `make dvf-multi-parcel-profile` — ticket [H7](../backlog/H7-mutations-multi-parcelles.md).
**Non recompté.** Aucun chiffre ne sort de ce fichier sans `recompte-preuve`.

Lu depuis les archives épinglées de DS-06, par le code de l'import : mêmes lots
dédupliqués, règle de complexité en vigueur (version 5) et règle de la version 4,
recopiée pour référence. Rien n'est écrit en base. Aucune mutation individuelle ici.

**Filtres communs.** Une mutation est un acte (`id_mutation`, ou la clé reconstruite de
l'archive DGFiP). Un lot bâti est une ligne à `type_local` renseigné, dédupliquée comme à
l'import. Le terrain cumulé compte une fois chaque triplet (parcelle, nature de culture,
surface). Le prix au m² est le prix de l'acte rapporté à la surface bâtie du lot unique ;
aucune nature de mutation n'est filtrée ici. Une valeur foncière nulle compte comme
absente (196 actes de l'archive, aucun sur 2021-2025). La nature de culture n'est pas
convertie depuis l'archive DGFiP : son tableau n'existe que pour 2021-2025, en lignes,
et le terrain cumulé de l'archive se compte par (parcelle, surface). Les tranches de
terrain sont fermées à gauche, ouvertes à droite ; les demi-unités vont au pair.

## Critère d'admission retenu

Écrit avant le code, à partir des tableaux ci-dessous (H7, choix 3).

- **Ce qui est admis** : une mutation dont le prix est présent et qui porte **un seul lot
  bâti distinct, avec surface**, quel que soit le nombre de parcelles. Le prix va à ce
  lot, le terrain venant avec — la règle déjà appliquée à une vente sur une parcelle.
- **Ce qui ne l'est pas** : zéro ou plusieurs lots chiffrables, surface absente, prix
  absent — comme en version 4, avec le motif le plus précis, testé avant les parcelles.
- **Pourquoi sans seuil de terrain.** Les candidates portent plus de terrain et un prix
  au m² brut plus bas que les ventes admises. Mais à commune et année égales, leur ratio
  médian au prix de la commune est proche de celui des admises : l'écart brut vient du
  lieu, pas du terrain annexé. Une vente sur une parcelle est déjà admise quelle que soit
  sa surface de terrain ; en exiger une des candidates serait inventer un seuil.
- **Limite du contrôle.** Il ne couvre que les couples commune-année d'au moins
  15 ventes admises, soit environ la moitié des candidates : les communes où la règle
  rend le plus de ventes sont celles où l'absence de dérive ne se mesure pas encore.
  L'argument y tient par cohérence avec les ventes sur une parcelle, pas par mesure.
- **Ce qui change pour le baromètre** : des ventes rurales en plus, là où le support de
  BAR-001 et BAR-002 manque ; une dispersion un peu plus large du prix au m², visible
  dans le premier quartile du ratio.

## Release `DS-06@2019-04-archive`

**179 573** mutations ; **45 052** `multiple_parcels` (25,1 %).

### Toutes les mutations, par motif en version 4

| Motif | Mutations | Part |
|---|---:|---:|
| allocatable | 84 747 | 47,2 % |
| multiple_parcels | 45 052 | 25,1 % |
| multiple_priced_lots | 35 589 | 19,8 % |
| no_priced_lot | 9 778 | 5,4 % |
| surface_missing | 3 578 | 2,0 % |
| price_missing | 829 | 0,5 % |

### Les `multiple_parcels`, par nombre de lots bâtis distincts

| Lots bâtis | Mutations | Part |
|---|---:|---:|
| 1 | 19 770 | 43,9 % |
| 0 | 16 778 | 37,2 % |
| 2 | 5 982 | 13,3 % |
| 3 | 1 540 | 3,4 % |
| 4 | 568 | 1,3 % |
| 5 et plus | 414 | 0,9 % |

### Les `multiple_parcels`, par nombre de parcelles

| Parcelles | Mutations | Part |
|---|---:|---:|
| 2 | 24 607 | 54,6 % |
| 3 | 8 854 | 19,7 % |
| 5 et plus | 7 201 | 16,0 % |
| 4 | 4 390 | 9,7 % |

### Les `multiple_parcels` à un seul lot bâti, par type de local

| Type | Mutations | Part |
|---|---:|---:|
| Maison | 17 803 | 90,1 % |
| Local industriel. commercial ou assimilé | 1 055 | 5,3 % |
| Dépendance | 501 | 2,5 % |
| Appartement | 411 | 2,1 % |

### Nature de culture des lignes de terrain des `multiple_parcels`

| Nature | Lignes de terrain | Part |
|---|---:|---:|
| — | — | — |

### Les `multiple_parcels` de la version 4, par motif en version 5

| Motif en version 5 | Mutations | Part |
|---|---:|---:|
| multiple_priced_lots | 25 144 | 55,8 % |
| allocatable | 19 000 | 42,2 % |
| surface_missing | 770 | 1,7 % |
| no_priced_lot | 89 | 0,2 % |
| multiple_parcels | 49 | 0,1 % |

### Candidates et ventes déjà admises, côte à côte

*Admises* : un seul lot bâti, une seule parcelle, prix alloué en version 4.
*Candidates* : un seul lot bâti avec surface, plusieurs parcelles, prix présent.

| Type | Population | Ventes | Sans terrain | Terrain Q1 | Terrain médiane | Terrain Q3 | Prix au m² Q1 | Médiane | Q3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Maison | admises, une parcelle | 38 129 | 1 211 | 351 | 522 | 771 | 1 447 € | 1 937 € | 2 526 € |
| Maison | candidates, plusieurs parcelles | 17 803 | 1 | 598 | 1 190 | 2 754 | 1 092 € | 1 565 € | 2 143 € |
| Appartement | admises, une parcelle | 13 830 | 13 735 | 78 | 142 | 260 | 1 743 € | 2 500 € | 3 391 € |
| Appartement | candidates, plusieurs parcelles | 411 | 44 | 49 | 141 | 394 | 1 564 € | 2 333 € | 2 931 € |

| Terrain cumulé (Maison) | Admises | Part | Prix au m² médian | Candidates | Part | Prix au m² médian |
|---|---:|---:|---:|---:|---:|---:|
| moins de 500 m² | 16 907 | 44,3 % | 2 126 € | 3 438 | 19,3 % | 1 753 € |
| 500 à 1 000 m² | 13 227 | 34,7 % | 1 891 € | 4 277 | 24,0 % | 1 612 € |
| 1 000 à 2 500 m² | 4 569 | 12,0 % | 1 678 € | 5 222 | 29,3 % | 1 512 € |
| 2 500 à 10 000 m² | 1 967 | 5,2 % | 1 562 € | 3 556 | 20,0 % | 1 489 € |
| 10 000 m² et plus | 248 | 0,7 % | 1 532 € | 1 309 | 7,4 % | 1 588 € |
| aucun terrain déclaré | 1 211 | 3,2 % | 1 802 € | 1 | 0,0 % | 3 529 € |

Contrôle par commune et année (Maison) : prix au m² rapporté à la médiane des ventes admises de la même commune la même année, pour les couples d'au moins 15 ventes admises. Un ratio de 1 veut dire « au prix de sa commune ».

| Population | Avec référence | Sans référence | Ratio Q1 | Médiane | Q3 |
|---|---:|---:|---:|---:|---:|
| admises, une parcelle | 28 902 | 9 227 | 0,85 | 1,00 | 1,16 |
| candidates, plusieurs parcelles | 9 317 | 8 486 | 0,76 | 0,97 | 1,18 |

## Release `DS-06@2026-09-13`

**133 066** mutations ; **33 973** `multiple_parcels` (25,5 %).

### Toutes les mutations, par motif en version 4

| Motif | Mutations | Part |
|---|---:|---:|
| allocatable | 49 820 | 37,4 % |
| multiple_priced_lots | 34 430 | 25,9 % |
| multiple_parcels | 33 973 | 25,5 % |
| no_priced_lot | 11 301 | 8,5 % |
| surface_missing | 2 742 | 2,1 % |
| price_missing | 800 | 0,6 % |

### Les `multiple_parcels`, par nombre de lots bâtis distincts

| Lots bâtis | Mutations | Part |
|---|---:|---:|
| 0 | 12 634 | 37,2 % |
| 1 | 10 671 | 31,4 % |
| 2 | 7 694 | 22,6 % |
| 3 | 2 198 | 6,5 % |
| 4 | 449 | 1,3 % |
| 5 et plus | 327 | 1,0 % |

### Les `multiple_parcels`, par nombre de parcelles

| Parcelles | Mutations | Part |
|---|---:|---:|
| 2 | 17 768 | 52,3 % |
| 3 | 6 813 | 20,1 % |
| 5 et plus | 5 932 | 17,5 % |
| 4 | 3 460 | 10,2 % |

### Les `multiple_parcels` à un seul lot bâti, par type de local

| Type | Mutations | Part |
|---|---:|---:|
| Maison | 9 255 | 86,7 % |
| Local industriel. commercial ou assimilé | 880 | 8,2 % |
| Dépendance | 445 | 4,2 % |
| Appartement | 91 | 0,9 % |

### Nature de culture des lignes de terrain des `multiple_parcels`

| Nature | Lignes de terrain | Part |
|---|---:|---:|
| terres | 30 441 | 29,4 % |
| sols | 27 603 | 26,7 % |
| prés | 14 104 | 13,6 % |
| terrains a bâtir | 10 872 | 10,5 % |
| jardins | 7 620 | 7,4 % |
| landes | 3 547 | 3,4 % |
| terrains d'agrément | 3 109 | 3,0 % |
| taillis simples | 1 590 | 1,5 % |
| vergers | 1 442 | 1,4 % |
| futaies résineuses | 840 | 0,8 % |
| eaux | 779 | 0,8 % |
| peupleraies | 511 | 0,5 % |
| futaies feuillues | 414 | 0,4 % |
| taillis sous futaie | 407 | 0,4 % |
| carrières | 67 | 0,1 % |
| futaies mixtes | 58 | 0,1 % |
| herbages | 57 | 0,1 % |
| bois | 48 | 0,0 % |
| chemin de fer | 48 | 0,0 % |
| oseraies | 1 | 0,0 % |

### Les `multiple_parcels` de la version 4, par motif en version 5

| Motif en version 5 | Mutations | Part |
|---|---:|---:|
| multiple_priced_lots | 23 208 | 68,3 % |
| allocatable | 10 049 | 29,6 % |
| surface_missing | 622 | 1,8 % |
| no_priced_lot | 55 | 0,2 % |
| multiple_parcels | 39 | 0,1 % |

### Candidates et ventes déjà admises, côte à côte

*Admises* : un seul lot bâti, une seule parcelle, prix alloué en version 4.
*Candidates* : un seul lot bâti avec surface, plusieurs parcelles, prix présent.

| Type | Population | Ventes | Sans terrain | Terrain Q1 | Terrain médiane | Terrain Q3 | Prix au m² Q1 | Médiane | Q3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Maison | admises, une parcelle | 22 232 | 760 | 337 | 500 | 701 | 1 916 € | 2 523 € | 3 231 € |
| Maison | candidates, plusieurs parcelles | 9 255 | 0 | 506 | 1 023 | 2 515 | 1 442 € | 2 072 € | 2 821 € |
| Appartement | admises, une parcelle | 4 290 | 4 249 | 73 | 122 | 192 | 2 600 € | 3 840 € | 5 000 € |
| Appartement | candidates, plusieurs parcelles | 91 | 1 | 45 | 117 | 284 | 1 971 € | 3 205 € | 4 338 € |

| Terrain cumulé (Maison) | Admises | Part | Prix au m² médian | Candidates | Part | Prix au m² médian |
|---|---:|---:|---:|---:|---:|---:|
| moins de 500 m² | 10 702 | 48,1 % | 2 731 € | 2 267 | 24,5 % | 2 289 € |
| 500 à 1 000 m² | 7 643 | 34,4 % | 2 442 € | 2 261 | 24,4 % | 2 136 € |
| 1 000 à 2 500 m² | 2 150 | 9,7 % | 2 171 € | 2 399 | 25,9 % | 1 973 € |
| 2 500 à 10 000 m² | 833 | 3,7 % | 2 000 € | 1 687 | 18,2 % | 1 940 € |
| 10 000 m² et plus | 144 | 0,6 % | 1 852 € | 641 | 6,9 % | 2 090 € |
| aucun terrain déclaré | 760 | 3,4 % | 2 181 € | 0 | 0,0 % | — |

Contrôle par commune et année (Maison) : prix au m² rapporté à la médiane des ventes admises de la même commune la même année, pour les couples d'au moins 15 ventes admises. Un ratio de 1 veut dire « au prix de sa commune ».

| Population | Avec référence | Sans référence | Ratio Q1 | Médiane | Q3 |
|---|---:|---:|---:|---:|---:|
| admises, une parcelle | 16 076 | 6 156 | 0,86 | 1,00 | 1,14 |
| candidates, plusieurs parcelles | 4 593 | 4 662 | 0,78 | 0,98 | 1,18 |
