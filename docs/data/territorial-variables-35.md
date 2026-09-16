# Variables communales du 35 — population, logements, équipements, aires

**Généré le :** 2026-09-16 · **Ticket :** [D7](../backlog/D7-sources-territoriales.md) · **Décision :** [ADR-023](../decisions/ADR-023-sources-territoriales.md)

Ce fichier est **régénéré** par `make territorial-report`. Ne pas l'éditer à la main.

Ces variables décrivent une **commune**, pas une parcelle : les rattacher à une parcelle est une jointure administrative. Elles servent la segmentation des marchés ([E6](../backlog/E6-segmentation-observee.md)) et n'entrent dans aucune mesure du baromètre ni du radar. Ce rapport publie des distributions ; il ne découpe rien.

## Releases et verdicts

| Release | Source | Publiée le | Communes | Lignes | dont absentes | Run | Verdict |
|---|---|---|---:|---:|---:|---|---|
| `DS-14@rp-2023` | Recensement de la population : populations de référence et logements | 2026-06-28 | 332 | 2 656 | 0 | `territorial:DS-14:rp-2023:35:1` | `display_only` |
| `DS-15@bpe-2025` | Base permanente des équipements | 2026-07-08 | 332 | 11 620 | 0 | `territorial:DS-15:bpe-2025:35:1` | `display_only` |
| `DS-16@aav2020-geo2025` | Zonage en aires d'attraction des villes 2020 | 2025-03-21 | 332 | 1 660 | 92 | `territorial:DS-16:aav2020-geo2025:35:1` | `display_only` |

**Verdict `display_only`** pour les trois : licence, millésime, empreinte, schéma et couverture sont établis ; la maille est la commune, appariée par code officiel géographique 2025, le même que celui du référentiel. Le passage à `accepted` attend le profiling d'E6, seul à dire si ces variables séparent réellement les marchés.

| Release | Fichier | SHA-256 | Octets |
|---|---|---|---:|
| `DS-14@rp-2023` | `housing` | `c93ccc1db5706511…` | 97 954 253 |
| `DS-14@rp-2023` | `population` | `f862ddd2a9135f80…` | 985 016 |
| `DS-15@bpe-2025` | `equipments` | `ec1f2ba0f857d56e…` | 14 401 658 |
| `DS-16@aav2020-geo2025` | `areas` | `738f81b12832fe29…` | 1 104 231 |

## Distributions sur les communes

Effectif = communes valuées ; « abs. » = communes sans valeur, avec motif. Quantiles par interpolation (`percentile_cont`), sur les seules communes valuées ; valeurs arrondies à l'unité, demi vers le haut. « Lignes » compte les lignes en table, distances au pôle comprises.

| Indicateur | Période | Unité | Effectif | abs. | à zéro | Min | P10 | Q1 | Médiane | Q3 | P90 | Max | Somme |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `logements_appartements` | 2023 | logements | 332 | 0 | 9 | 0 | 2 | 8 | 22 | 159 | 869 | 119 540 | 242 533 |
| `logements_maisons` | 2023 | logements | 332 | 0 | 0 | 53 | 213 | 369 | 644 | 1 276 | 2 115 | 16 561 | 345 037 |
| `logements_total` | 2023 | logements | 332 | 0 | 0 | 55 | 217 | 382 | 700 | 1 508 | 3 135 | 137 847 | 592 053 |
| `population_comptee_a_part` | 2023 | habitants | 332 | 0 | 0 | 1 | 8 | 16 | 28 | 66 | 130 | 4 060 | 24 620 |
| `population_municipale` | 2023 | habitants | 332 | 0 | 0 | 97 | 416 | 806 | 1 425 | 2 903 | 6 379 | 230 890 | 1 120 666 |
| `population_totale` | 2023 | habitants | 332 | 0 | 0 | 101 | 424 | 821 | 1 449 | 2 944 | 6 479 | 234 950 | 1 145 286 |
| `residences_principales` | 2023 | logements | 332 | 0 | 0 | 49 | 176 | 328 | 586 | 1 299 | 2 781 | 122 334 | 513 565 |
| `residences_secondaires_occasionnelles` | 2023 | logements | 332 | 0 | 0 | 1 | 5 | 10 | 24 | 51 | 116 | 10 358 | 42 705 |
| `equipements_domaine_a` — Services pour les particuliers | 2025 | équipements | 332 | 0 | 0 | 1 | 5 | 11 | 20 | 49 | 112 | 2 858 | 16 860 |
| `equipements_domaine_b` — Commerces | 2025 | équipements | 332 | 0 | 62 | 0 | 0 | 1 | 3 | 9 | 35 | 1 301 | 5 731 |
| `equipements_domaine_c` — Enseignement | 2025 | équipements | 332 | 0 | 40 | 0 | 0 | 1 | 1 | 2 | 6 | 365 | 1 270 |
| `equipements_domaine_d` — Santé et action sociale | 2025 | équipements | 332 | 0 | 79 | 0 | 0 | 1 | 6 | 27 | 63 | 2 970 | 11 932 |
| `equipements_domaine_e` — Transports et déplacements | 2025 | équipements | 332 | 0 | 183 | 0 | 0 | 0 | 0 | 1 | 3 | 141 | 532 |
| `equipements_domaine_f` — Sports, loisirs et culture | 2025 | équipements | 332 | 0 | 17 | 0 | 1 | 4 | 6 | 10 | 16 | 255 | 2 919 |
| `equipements_domaine_g` — Tourisme | 2025 | équipements | 332 | 0 | 208 | 0 | 0 | 0 | 0 | 1 | 3 | 119 | 600 |
| `equipements_sous_domaine_a1` — Services publics | 2025 | équipements | 332 | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 3 | 35 | 536 |
| `equipements_sous_domaine_a2` — Services généraux | 2025 | équipements | 332 | 0 | 117 | 0 | 0 | 0 | 1 | 2 | 5 | 125 | 728 |
| `equipements_sous_domaine_a3` — Services automobiles | 2025 | équipements | 332 | 0 | 73 | 0 | 0 | 1 | 2 | 6 | 13 | 156 | 1 801 |
| `equipements_sous_domaine_a4` — Artisanat du bâtiment | 2025 | équipements | 332 | 0 | 3 | 0 | 2 | 5 | 11 | 22 | 41 | 787 | 6 627 |
| `equipements_sous_domaine_a5` — Autres services | 2025 | équipements | 332 | 0 | 14 | 0 | 1 | 3 | 6 | 15 | 38 | 1 755 | 7 168 |
| `equipements_sous_domaine_b1` — Grandes surfaces | 2025 | équipements | 332 | 0 | 242 | 0 | 0 | 0 | 0 | 1 | 2 | 46 | 281 |
| `equipements_sous_domaine_b2` — Commerces alimentaires | 2025 | équipements | 332 | 0 | 81 | 0 | 0 | 1 | 2 | 4 | 9 | 373 | 1 805 |
| `equipements_sous_domaine_b3` — Commerces spécialisés non-alimentaires | 2025 | équipements | 332 | 0 | 128 | 0 | 0 | 0 | 1 | 5 | 23 | 882 | 3 645 |
| `equipements_sous_domaine_c1` — Enseignement du premier degré | 2025 | équipements | 332 | 0 | 40 | 0 | 0 | 1 | 1 | 2 | 3 | 99 | 680 |
| `equipements_sous_domaine_c2` — Enseignement du second degré - premier cycle | 2025 | équipements | 332 | 0 | 276 | 0 | 0 | 0 | 0 | 0 | 1 | 20 | 117 |
| `equipements_sous_domaine_c3` — Enseignement du second degré - second cycle | 2025 | équipements | 332 | 0 | 305 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 96 |
| `equipements_sous_domaine_c4` — Enseignement supérieur non-universitaire | 2025 | équipements | 332 | 0 | 321 | 0 | 0 | 0 | 0 | 0 | 0 | 63 | 87 |
| `equipements_sous_domaine_c5` — Enseignement supérieur universitaire | 2025 | équipements | 332 | 0 | 325 | 0 | 0 | 0 | 0 | 0 | 0 | 39 | 53 |
| `equipements_sous_domaine_c6` — Formation continue | 2025 | équipements | 332 | 0 | 298 | 0 | 0 | 0 | 0 | 0 | 1 | 90 | 209 |
| `equipements_sous_domaine_c7` — Autres services de l'éducation | 2025 | équipements | 332 | 0 | 329 | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 28 |
| `equipements_sous_domaine_d1` — Etablissements et services de santé | 2025 | équipements | 332 | 0 | 253 | 0 | 0 | 0 | 0 | 0 | 1 | 94 | 294 |
| `equipements_sous_domaine_d2` — Fonctions médicales et paramédicales (à titre libéral) | 2025 | équipements | 332 | 0 | 111 | 0 | 0 | 0 | 4 | 20 | 46 | 2 298 | 8 972 |
| `equipements_sous_domaine_d3` — Autres établissements et services à caractère sanitaire | 2025 | équipements | 332 | 0 | 196 | 0 | 0 | 0 | 0 | 1 | 4 | 85 | 442 |
| `equipements_sous_domaine_d4` — Action sociale pour personnes âgées | 2025 | équipements | 332 | 0 | 201 | 0 | 0 | 0 | 0 | 1 | 3 | 59 | 367 |
| `equipements_sous_domaine_d5` — Action sociale pour enfants en bas-âge | 2025 | équipements | 332 | 0 | 126 | 0 | 0 | 0 | 2 | 4 | 7 | 235 | 1 192 |
| `equipements_sous_domaine_d6` — Action sociale pour handicapés | 2025 | équipements | 332 | 0 | 225 | 0 | 0 | 0 | 0 | 1 | 3 | 96 | 439 |
| `equipements_sous_domaine_d7` — Autres services d'action sociale | 2025 | équipements | 332 | 0 | 287 | 0 | 0 | 0 | 0 | 0 | 1 | 103 | 226 |
| `equipements_sous_domaine_e1` — Infrastructures de transports | 2025 | équipements | 332 | 0 | 183 | 0 | 0 | 0 | 0 | 1 | 3 | 141 | 532 |
| `equipements_sous_domaine_f1` — Equipements sportifs | 2025 | équipements | 332 | 0 | 35 | 0 | 0 | 2 | 4 | 7 | 13 | 213 | 2 232 |
| `equipements_sous_domaine_f2` — Equipements de loisirs | 2025 | équipements | 332 | 0 | 152 | 0 | 0 | 0 | 1 | 1 | 2 | 6 | 264 |
| `equipements_sous_domaine_f3` — Equipements culturels et socioculturels | 2025 | équipements | 332 | 0 | 56 | 0 | 0 | 1 | 1 | 1 | 2 | 40 | 423 |
| `equipements_sous_domaine_g1` — Tourisme | 2025 | équipements | 332 | 0 | 208 | 0 | 0 | 0 | 0 | 1 | 3 | 119 | 600 |
| `equipements_total` — Ensemble des équipements | 2025 | équipements | 332 | 0 | 0 | 1 | 9 | 19 | 38 | 99 | 233 | 8 009 | 39 844 |
| `aav_distance_centre_m` | AAV2020 | m | 284 | 48 | 7 | 0 | 5 388 | 9 054 | 16 645 | 25 994 | 31 365 | 38 696 | — |

Lecture :

- **Population** : populations de référence millésimées 2023. La population totale ajoute la population comptée à part à la population municipale ; sommer les populations totales compte deux fois certaines personnes.
- **Logements** : estimations pondérées du recensement 2023, non arrondies. Les logements vacants ne sont pas importés (`SPEC.md` §12) ; les maisons et appartements ne couvrent pas tout le parc (autres types exclus).
- **Équipements** : dénombrement de la BPE 2025. Un zéro dit qu'aucun équipement du sous-domaine n'est recensé dans la commune — c'est la valeur observée, pas une absence.
- **Distance au pôle** : entre centroïdes Lambert-93 de la commune et de la commune-centre de son aire d'attraction ; zéro pour la commune-centre elle-même. Absente (`not_applicable`) hors attraction.

## Aires d'attraction des villes

| Variable | Valeur | Communes |
|---|---|---:|
| `aav_categorie` | 20 — commune de la couronne | 277 |
| `aav_categorie` | 30 — commune hors attraction des villes | 44 |
| `aav_categorie` | 11 — commune-centre | 7 |
| `aav_categorie` | 12 — autre commune du pôle principal | 4 |
| `aav_code` | 013 | 181 |
| `aav_code` | 000 | 44 |
| `aav_code` | 088 | 30 |
| `aav_code` | 169 | 29 |
| `aav_code` | 172 | 24 |
| `aav_code` | 474 | 9 |
| `aav_code` | 188 | 8 |
| `aav_code` | 431 | 3 |
| `aav_code` | 525 | 3 |
| `aav_code` | 533 | 1 |
| `aav_tranche_taille` | 4 | 181 |
| `aav_tranche_taille` | 2 | 83 |
| `aav_tranche_taille` | 0 | 44 |
| `aav_tranche_taille` | 1 | 24 |

La tranche de taille (`TAAV2017`) est celle de l'INSEE, calculée sur la population 2017 de l'aire ; elle n'est pas un seuil de ce projet.

### Communes sans distance au pôle

Leur commune-centre est hors du référentiel importé (le 35 seul) : la distance reste absente, avec le motif `source_value_missing`.

| Commune | Nom | Commune-centre de l'aire |
|---|---|---|
| `35046` | LES BRULAIS | `56075` |
| `35084` | COMBLESSAC | `56075` |
| `35160` | LOUTEHEL | `56075` |
| `35222` | PLEINE-FOUGERES | `50410` |

## Limites

- Une commune n'est pas homogène : Rennes a une valeur, ses quartiers n'en ont pas. Toute lecture à la parcelle hérite de cette imprécision.
- La distance entre centroïdes n'est ni un temps de trajet ni une distance par la route.
- Les communes du 35 dont l'aire déborde du département ont une commune-centre voisine dont la distance ne peut pas se mesurer tant que le référentiel se limite au 35.
