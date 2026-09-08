# Distribution des appariements spatiaux — département 35

**Date :** 2026-09-07
**Portée :** les cinq relations du référentiel spatial de v0.3, sur les 332 communes du 35.

Ce document est **généré**. Il ne se corrige pas à la main :

```bash
make matching-report DEPARTMENT=35
```

## Deux distinctions qui gouvernent la lecture

**« Non apparié » n'est pas « rejeté ».** Le premier est une absence de décision, le
second une décision motivée. Ils ne sont jamais additionnés.

**« Non couvert » n'est pas « taux nul ».** Une commune sans aucun enregistrement source
donne quatre classes à zéro ; une commune où la source est présente mais où rien
n'apparie donne un nombre de non appariés strictement positif. Les quatre classes à zéro
identifient donc exactement l'absence de couverture.

## Distribution en quatre classes, jamais trois

| Relation | certain | ambigu | rejeté | non apparié | total | communes non couvertes |
|---|---:|---:|---:|---:|---:|---:|
| Bâtiment ↔ Parcelle | 737 353 | 0 | 0 | 4 010 | 741 363 | 0 |
| Adresse ↔ Parcelle | 248 209 | 1 759 | 2 685 | 184 788 | 437 441 | 0 |
| Adresse ↔ Bâtiment | 393 355 | 0 | 0 | 44 086 | 437 441 | 0 |
| Bâtiment BD TOPO ↔ Bâtiment RNB | 692 621 | 90 841 | 0 | 17 711 | 801 173 | 0 |
| Groupe BDNB ↔ Bâtiment RNB | 422 194 | 104 823 | 0 | 19 284 | 546 301 | 0 |

Releases et algorithmes derrière ces chiffres :

| Relation | Release | Algorithme | Communes mesurées |
|---|---|---|---:|
| Bâtiment ↔ Parcelle | `DS-02@2026-09-05` | `rnb-plot-relation` | 332 |
| Adresse ↔ Parcelle | `DS-05@2026-06-17` | `ban-cad-parcelles` | 332 |
| Adresse ↔ Bâtiment | `DS-05@2026-06-17` | `rnb-ban-identifier` | 332 |
| Bâtiment BD TOPO ↔ Bâtiment RNB | `DS-04@2026-06-15` | `bdtopo-rnb-link` | 332 |
| Groupe BDNB ↔ Bâtiment RNB | `DS-03@2026-02-a` | `bdnb-group-rnb-link` | 332 |

## Volume par méthode d'appariement

L'ordre de préférence de v0.3 est : identifiant officiel, relation source explicite,
intersection spatiale, proximité, adresse normalisée, cohérence temporelle.

| Algorithme | Méthode | Décision | Volume | Confiance min | max |
|---|---|---|---:|---:|---:|
| `ban-cad-parcelles` | `source_relation` | ambiguous | 49 479 | 0.80000 | 0.80000 |
| `ban-cad-parcelles` | `source_relation` | certain | 272 695 | 0.95000 | 0.99000 |
| `ban-cad-parcelles` | `source_relation` | rejected | 3 760 | 0.00000 | 0.00000 |
| `bdnb-group-rnb-link` | `source_relation` | ambiguous | 303 219 | 0.50000 | 0.50000 |
| `bdnb-group-rnb-link` | `source_relation` | certain | 422 194 | 0.99000 | 0.99000 |
| `bdtopo-rnb-link` | `official_identifier` | ambiguous | 46 106 | 0.50000 | 0.50000 |
| `bdtopo-rnb-link` | `official_identifier` | certain | 692 633 | 1.00000 | 1.00000 |
| `bdtopo-rnb-link` | `source_relation` | certain | 1 | 0.99000 | 0.99000 |
| `bdtopo-rnb-link` | `spatial_intersection` | ambiguous | 87 255 | 0.50000 | 0.50000 |
| `rnb-ban-identifier` | `source_relation` | certain | 566 248 | 1.00000 | 1.00000 |
| `rnb-commune-spatial` | `spatial_intersection` | certain | 420 | 0.99000 | 0.99000 |
| `rnb-plot-relation` | `source_relation` | certain | 1 240 355 | 0.90000 | 1.00000 |

## Distribution des confiances

Les valeurs, non leur moyenne. Deux natures coexistent et se lisent différemment : une
confiance posée par une règle est une étiquette, qu'il faut détailler ; un taux de
recouvrement est une grandeur continue, qui se lit en tranches.

| Algorithme | Valeurs distinctes | Nature |
|---|---:|---|
| `ban-cad-parcelles` | 4 | discrète |
| `bdnb-group-rnb-link` | 2 | discrète |
| `bdtopo-rnb-link` | 3 | discrète |
| `rnb-ban-identifier` | 1 | discrète |
| `rnb-commune-spatial` | 1 | discrète |
| `rnb-plot-relation` | 10 001 | continue |

### Confiances discrètes, valeur par valeur

| Algorithme | Confiance | Décision | Volume |
|---|---:|---|---:|
| `ban-cad-parcelles` | 0.99000 | certain | 231 675 |
| `ban-cad-parcelles` | 0.95000 | certain | 41 020 |
| `ban-cad-parcelles` | 0.80000 | ambiguous | 49 479 |
| `ban-cad-parcelles` | 0.00000 | rejected | 3 760 |
| `bdnb-group-rnb-link` | 0.99000 | certain | 422 194 |
| `bdnb-group-rnb-link` | 0.50000 | ambiguous | 303 219 |
| `bdtopo-rnb-link` | 1.00000 | certain | 692 633 |
| `bdtopo-rnb-link` | 0.99000 | certain | 1 |
| `bdtopo-rnb-link` | 0.50000 | ambiguous | 133 361 |
| `rnb-ban-identifier` | 1.00000 | certain | 566 248 |
| `rnb-commune-spatial` | 0.99000 | certain | 420 |

### Confiances continues, par tranche de 0,1

| Algorithme | Tranche | Décision | Volume | Min observé | Max observé |
|---|---|---|---:|---:|---:|
| `rnb-plot-relation` | [1.0 a 1.1[ | certain | 390 768 | 1.00000 | 1.00000 |
| `rnb-plot-relation` | [0.9 a 1.0[ | certain | 849 587 | 0.90000 | 0.99999 |

## Cardinalité réelle

Un ratio moyen masquerait ce que le modèle porte nativement.

| Relation | Maximum observé | Moyenne | Cas au-delà de 1 |
|---|---:|---:|---:|
| `building_parcel` | 37 | 1.682 | 353 999 |
| `bdtopo_building_rnb` | 18 | 1.054 | 35 148 |
| `bdnb_group_rnb` | 80 | 1.376 | 94 679 |

## Par commune : aucun taux sans son volume

Un taux élevé sur une commune à faible volume ne vaut pas un taux identique sur Rennes.
Chaque tableau expose donc le volume à côté du taux.

### Bâtiment ↔ Parcelle

Les cinq communes au plus fort volume :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| RENNES | `35238` | 37 669 | 37 531 | 0 | 0 | 138 | 0.9963 |
| SAINT-MALO | `35288` | 26 119 | 26 019 | 0 | 0 | 100 | 0.9962 |
| VITRE | `35360` | 9 954 | 9 918 | 0 | 0 | 36 | 0.9964 |
| FOUGERES | `35115` | 9 919 | 9 872 | 0 | 0 | 47 | 0.9953 |
| DINARD | `35093` | 9 420 | 9 380 | 0 | 0 | 40 | 0.9958 |

Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| ANDOUILLE-NEUVILLE | `35003` | 809 | 778 | 0 | 0 | 31 | 0.9617 |
| CHARTRES-DE-BRETAGNE | `35066` | 3 222 | 3 115 | 0 | 0 | 107 | 0.9668 |
| SAINT ONEN LA CHAPELLE | `35302` | 1 307 | 1 271 | 0 | 0 | 36 | 0.9725 |
| DROUGES | `35102` | 874 | 853 | 0 | 0 | 21 | 0.9760 |
| LE FERRE | `35111` | 1 166 | 1 139 | 0 | 0 | 27 | 0.9768 |

### Adresse ↔ Parcelle

Les cinq communes au plus fort volume :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| RENNES | `35238` | 31 063 | 30 959 | 18 | 58 | 28 | 0.9967 |
| SAINT-MALO | `35288` | 19 452 | 6 | 2 | 1 | 19 443 | 0.0003 |
| FOUGERES | `35115` | 7 989 | 3 052 | 11 | 24 | 4 902 | 0.3820 |
| DINARD | `35093` | 7 487 | 3 420 | 25 | 46 | 3 996 | 0.4568 |
| VITRE | `35360` | 7 428 | 7 313 | 2 | 6 | 107 | 0.9845 |

Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| LA GUERCHE-DE-BRETAGNE | `35125` | 2 314 | 0 | 0 | 0 | 2 314 | 0.0000 |
| PLEUMELEUC | `35227` | 1 485 | 0 | 0 | 0 | 1 485 | 0.0000 |
| RIVES-DU-COUESNON | `35282` | 1 288 | 0 | 0 | 0 | 1 288 | 0.0000 |
| ST GEORGES DE REINTEMBAULT | `35271` | 1 071 | 0 | 0 | 0 | 1 071 | 0.0000 |
| MEZIERES-SUR-COUESNON | `35178` | 825 | 0 | 0 | 0 | 825 | 0.0000 |

### Adresse ↔ Bâtiment

Les cinq communes au plus fort volume :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| RENNES | `35238` | 31 063 | 30 582 | 0 | 0 | 481 | 0.9845 |
| SAINT-MALO | `35288` | 19 452 | 19 058 | 0 | 0 | 394 | 0.9797 |
| FOUGERES | `35115` | 7 989 | 7 353 | 0 | 0 | 636 | 0.9204 |
| DINARD | `35093` | 7 487 | 6 815 | 0 | 0 | 672 | 0.9102 |
| VITRE | `35360` | 7 428 | 6 982 | 0 | 0 | 446 | 0.9400 |

Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| MESNIL ROC'H | `35308` | 2 418 | 1 406 | 0 | 0 | 1 012 | 0.5815 |
| RIVES-DU-COUESNON | `35282` | 1 288 | 801 | 0 | 0 | 487 | 0.6219 |
| ST GEORGES DE REINTEMBAULT | `35271` | 1 071 | 697 | 0 | 0 | 374 | 0.6508 |
| BAIS | `35014` | 1 247 | 814 | 0 | 0 | 433 | 0.6528 |
| PLEUGUENEUC | `35226` | 1 101 | 720 | 0 | 0 | 381 | 0.6540 |

### Bâtiment BD TOPO ↔ Bâtiment RNB

Les cinq communes au plus fort volume :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| RENNES | `35238` | 42 742 | 36 244 | 5 248 | 0 | 1 250 | 0.8480 |
| SAINT-MALO | `35288` | 28 258 | 24 919 | 2 645 | 0 | 694 | 0.8818 |
| FOUGERES | `35115` | 11 519 | 9 803 | 1 294 | 0 | 422 | 0.8510 |
| VITRE | `35360` | 10 946 | 9 287 | 1 371 | 0 | 288 | 0.8484 |
| DINARD | `35093` | 10 378 | 9 139 | 986 | 0 | 253 | 0.8806 |

Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| LA CHAPELLE THOUARAULT | `35065` | 1 560 | 1 240 | 258 | 0 | 62 | 0.7949 |
| BETTON | `35024` | 6 864 | 5 551 | 1 084 | 0 | 229 | 0.8087 |
| BOVEL | `35035` | 873 | 709 | 129 | 0 | 35 | 0.8121 |
| RIMOU | `35242` | 909 | 742 | 137 | 0 | 30 | 0.8163 |
| SAINT-SULIAC | `35314` | 1 233 | 1 009 | 159 | 0 | 65 | 0.8183 |

### Groupe BDNB ↔ Bâtiment RNB

Les cinq communes au plus fort volume :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| RENNES | `35238` | 30 787 | 24 766 | 4 451 | 0 | 1 570 | 0.8044 |
| SAINT-MALO | `35288` | 21 453 | 17 532 | 3 116 | 0 | 805 | 0.8172 |
| FOUGERES | `35115` | 8 409 | 6 802 | 1 163 | 0 | 444 | 0.8089 |
| VITRE | `35360` | 8 246 | 6 792 | 1 058 | 0 | 396 | 0.8237 |
| DINARD | `35093` | 7 921 | 6 581 | 1 089 | 0 | 251 | 0.8308 |

Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :

| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |
|---|---|---:|---:|---:|---:|---:|---:|
| SAINT-JUST | `35285` | 1 279 | 813 | 419 | 0 | 47 | 0.6357 |
| SAINT-GANTON | `35268` | 508 | 327 | 173 | 0 | 8 | 0.6437 |
| BAZOUGES-LA-PEROUSE | `35019` | 1 990 | 1 292 | 644 | 0 | 54 | 0.6492 |
| LA BAZOUGE DU DESERT | `35018` | 1 027 | 667 | 337 | 0 | 23 | 0.6495 |
| ST GEORGES DE REINTEMBAULT | `35271` | 1 574 | 1 034 | 499 | 0 | 41 | 0.6569 |

## Motifs des décisions non certaines

Un ambigu et un rejeté portent tous deux un motif. Une absence d'appariement n'en porte
aucun, et c'est précisément ce qui les distingue.

| Algorithme | Décision | Motif | Volume |
|---|---|---|---:|
| `bdnb-group-rnb-link` | ambiguous | BDNB group spans several canonical buildings: its group-level attributes belong to none of | 293 085 |
| `bdtopo-rnb-link` | ambiguous | Footprints intersect but no calibrated overlap threshold exists: the measured ratio is ret | 87 255 |
| `ban-cad-parcelles` | ambiguous | BAN experimental cad_parcelles relation checked against active parcel geometry | 49 479 |
| `bdtopo-rnb-link` | ambiguous | BD TOPO footprint declares several RNB buildings: the source itself states the footprint c | 46 106 |
| `bdnb-group-rnb-link` | ambiguous | Producer qualifies at least one contributing relation as diverging, split, merged, partial | 10 134 |
| `ban-cad-parcelles` | rejected | BAN cad_parcelles names a cadastral parcel that the active referential does not contain | 3 760 |

## Où ces chiffres sont persistés

`meta.entity_match_metric`, une ligne par release, commune, relation et algorithme.
Ils sont exposés à l'administration sous `GET /api/v1/admin/match-metrics`, réservé au
rôle `organization_admin` — exigence FR-012.

