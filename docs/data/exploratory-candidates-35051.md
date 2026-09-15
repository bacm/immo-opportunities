# Liste exploratoire de candidats — commune 35051

**Généré le :** 2026-09-15 · **Ticket :** [E8](../backlog/E8-liste-exploratoire-terrain.md) · **Graine :** `20260915`

Ce fichier est **régénéré** par `make exploratory-candidates`. Ne pas l'éditer à la main.

## Ce que cette liste est, et n'est pas

Elle **n'est pas un score publié**. Aucun `OpportunitySnapshot` n'a été créé, aucune unité n'est devenue publiable, et les 1 333 327 unités du 35 restent en `entity_resolution_incomplete`. C'est une requête de lecture, destinée à être montrée à un professionnel par [E9](../backlog/E9-test-terrain-deux-professionnels.md).

**Chaque ligne désigne une parcelle, pas un bien.** [BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md) mesure cette limite : l'unité foncière au sens juridique suppose le propriétaire, hors périmètre, et la contiguïté seule produit des grappes de plusieurs milliers de parcelles. Un garage sur parcelle propre apparaît donc ici comme un candidat distinct de la maison voisine. Savoir si cette limite est rédhibitoire fait partie de ce que la revue doit établir.

## Ce que le zonage ne permet pas de faire

Le filtre ne retient que le **type CNIG** `U`. Le libellé local — `UI1a`, `UG2b`, `UE2c(d)` — n'est pas interprétable sans le règlement du document, et [D2](../backlog/D2-import-gpu-ds08.md) a explicitement refusé de le recoder au jugé. Les profils de règles qui le permettraient sont [D2b](../backlog/D2b-profils-de-regles.md), non livré.

Conséquence directe, constatée au premier passage : sans plafond de surface, la liste se remplit de foncier d'activité — parcelles de plusieurs hectares en zone `UI` ou `UG`, jusqu'à 31 bâtiments — qui ne relève pas de la promesse produit. Le plafond ci-dessous l'écarte grossièrement, faute de pouvoir écarter la zone. C'est une limite à signaler au relecteur, pas un réglage à défendre.

## Paramètres — arbitraires, et c'est délibéré

Aucun profiling ne les fonde. Ils bornent une population de travail sur une commune ; ils ne définissent pas ce qu'est un bon candidat et n'anticipent pas [E1](../backlog/E1-profiling-distributions.md). Les contester fait partie de la revue.

| Paramètre | Valeur |
|---|---:|
| `min_parcel_area_m2` | 800.0 |
| `max_parcel_area_m2` | 3000.0 |
| `max_footprint_ratio` | 0.2 |
| `min_width_m` | 15.0 |
| `min_building_count` | 1 |
| `zone_type` | U |

## Entonnoir

| Étape | Unités restantes |
|---|---:|
| population | 9 329 |
| bâtie | 6 412 |
| surface connue | 6 412 |
| surface suffisante | 1 828 |
| surface plafonnée | 1 177 |
| emprise connue | 1 177 |
| emprise faible | 727 |
| largeur connue | 727 |
| largeur suffisante | 715 |
| zone connue | 715 |
| zone constructible | 534 |

**534 unités éligibles**  dont 20 retenues par chaque ordre.

## Les deux ordres, et leur recouvrement

La baseline est le tri cadastral simple que H1 demande de battre : surface décroissante. Le classement ordonne **la même population** par le rang moyen des signaux morphologiques disponibles — `unbuilt_area_m2`, `footprint_ratio`, `width_m`, `boundary_distance_m`.

| | |
|---|---:|
| Candidats issus de la baseline seule | 16 |
| Candidats issus du classement seul | 16 |
| Communs aux deux ordres | 4 |
| **Total remis au relecteur** | **36** |

Les deux ordres diffèrent sur 32 candidats. C'est cet écart que la revue en aveugle départage.

0 candidats sont classés sur moins de 4 signaux, un signal absent n'étant pas remplacé par zéro.

## Candidats

L'origine de chaque candidat — baseline ou classement — n'est **pas** dans ce tableau : elle est dans `docs/data/exploratory-candidates/35051/correspondance.csv`, que le relecteur ne voit pas. La liste remise est `docs/data/exploratory-candidates/35051/liste-aveugle.csv`.

| Réf. | Parcelle | Surface m² | Emprise | Libre m² | Largeur m | Recul m | Bât. | Zone | Contraintes | Dernière mutation | DPE | Risques fins |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| C001 | `35051000AZ0303` | 2 848 | 0.178 | 2 341 | 48.4 | 0.0 | 2 | U|UI1a | 13 information, 19 prescription | aucune | aucun | clay, sup_T1 |
| C002 | `35051000ZE0186` | 2 508 | 0.046 | 2 392 | 41.1 | 8.7 | 1 | U|UE2h(d) | 9 information, 14 prescription | aucune | aucun | aucun |
| C003 | `35051000YC0394` | 1 643 | 0.095 | 1 488 | 42.7 | 7.4 | 2 | U|UE2h(d) | 10 information, 13 prescription | aucune | aucun | aucun |
| C004 | `35051000YB0120` | 2 619 | 0.004 | 2 607 | 89.5 | 0.0 | 2 | U|UO1 | 11 information, 15 prescription | aucune | aucun | aucun |
| C005 | `35051000AZ0323` | 2 747 | 0.178 | 2 259 | 71.4 | 0.0 | 3 | U|UI1a | 11 information, 18 prescription | aucune | aucun | clay, sup_PM1 |
| C006 | `35051000ZT0138` | 1 331 | 0.082 | 1 222 | 44.8 | 8.0 | 1 | U|UE3 | 8 information, 16 prescription | aucune | aucun | clay |
| C007 | `35051000BC0118` | 2 571 | 0.002 | 2 565 | 73.3 | 4.2 | 1 | U|UI3 | 11 information, 14 prescription | aucune | aucun | aucun |
| C008 | `35051000BE0304` | 2 721 | 0.094 | 2 466 | 37.3 | 0.0 | 2 | U|UI1a(d) | 9 information, 20 prescription | aucune | aucun | clay |
| C009 | `35051000ZV0250` | 2 838 | 0.062 | 2 663 | 49.9 | 12.3 | 1 | U|UE3 | 10 information, 17 prescription | aucune | aucun | clay |
| C010 | `35051000AK0086` | 2 800 | 0.000 | 2 800 | 53.6 | 0.0 | 1 | U|UE2c(d) | 11 information, 16 prescription | aucune | aucun | aucun |
| C011 | `35051000AW0229` | 1 714 | 0.085 | 1 567 | 40.9 | 6.5 | 1 | U|UE2c(d) | 10 information, 14 prescription | 2024-01-19 | aucun | clay |
| C012 | `35051000ZS0176` | 2 532 | 0.133 | 2 196 | 54.9 | 0.0 | 2 | U|UE3 | 10 information, 15 prescription | 2022-10-07 | C | clay, sup_AC1 |
| C013 | `35051000AV0103` | 2 648 | 0.000 | 2 648 | 46.7 | 0.0 | 3 | U|UC2 | 10 information, 17 prescription | aucune | aucun | clay |
| C014 | `35051000AW0231` | 2 645 | 0.127 | 2 309 | 42.1 | 0.0 | 3 | U|UE2c | 9 information, 15 prescription | aucune | aucun | clay |
| C015 | `35051000BB0010` | 2 989 | 0.189 | 2 425 | 40.0 | 0.0 | 1 | U|UO1 | 11 information, 14 prescription | aucune | aucun | aucun |
| C016 | `35051000AC0088` | 2 773 | 0.111 | 2 466 | 69.8 | 0.0 | 1 | U|UA1a | 8 information, 20 prescription | aucune | aucun | clay |
| C017 | `35051000AV0143` | 2 565 | 0.000 | 2 565 | 50.6 | 0.0 | 2 | U|UC2 | 8 information, 17 prescription | aucune | aucun | clay |
| C018 | `35051000ZV0230` | 2 059 | 0.097 | 1 859 | 39.0 | 5.0 | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay |
| C019 | `35051000YD0411` | 2 569 | 0.035 | 2 479 | 100.5 | 0.0 | 2 | U|UE3 | 11 information, 22 prescription | aucune | aucun | aucun |
| C020 | `35051000AK0150` | 2 397 | 0.005 | 2 386 | 71.3 | 1.4 | 1 | U|UE2c(d) | 12 information, 14 prescription | aucune | aucun | aucun |
| C021 | `35051000ZV0136` | 2 667 | 0.065 | 2 493 | 67.2 | 1.9 | 2 | U|UE3 | 8 information, 13 prescription | aucune | aucun | clay |
| C022 | `35051000ZT0169` | 1 925 | 0.106 | 1 721 | 41.5 | 9.3 | 1 | U|UE3 | 8 information, 16 prescription | 2021-05-20 | C | clay |
| C023 | `35051000AR0283` | 2 852 | 0.085 | 2 609 | 60.5 | 0.0 | 7 | U|UO1 | 10 information, 19 prescription | aucune | aucun | clay |
| C024 | `35051000YA0166` | 2 698 | 0.120 | 2 373 | 46.7 | 0.0 | 1 | U|UE2h | 10 information, 16 prescription | aucune | aucun | aucun |
| C025 | `35051000AZ0207` | 2 021 | 0.071 | 1 878 | 43.0 | 6.6 | 1 | U|UI1a | 12 information, 19 prescription | aucune | aucun | clay, sup_T1 |
| C026 | `35051000AZ0338` | 2 147 | 0.117 | 1 896 | 38.8 | 6.5 | 1 | U|UI1b(d) | 8 information, 17 prescription | aucune | aucun | clay |
| C027 | `35051000AN0379` | 2 021 | 0.000 | 2 021 | 62.0 | 0.0 | 4 | U|UE2c | 9 information, 16 prescription | aucune | aucun | clay |
| C028 | `35051000AW0225` | 2 166 | 0.065 | 2 025 | 41.3 | 5.9 | 1 | U|UE2c(d) | 10 information, 16 prescription | aucune | aucun | clay |
| C029 | `35051000YC0085` | 1 475 | 0.071 | 1 370 | 40.5 | 10.8 | 1 | U|UE2h(d) | 10 information, 15 prescription | aucune | aucun | clay |
| C030 | `35051000AX0138` | 2 271 | 0.115 | 2 010 | 41.2 | 8.6 | 1 | U|UI1a | 7 information, 14 prescription | aucune | aucun | clay |
| C031 | `35051000ZB0082` | 2 533 | 0.077 | 2 338 | 40.4 | 0.0 | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay |
| C032 | `35051000AI0108` | 1 895 | 0.006 | 1 884 | 30.9 | 6.2 | 1 | U|UE2c(d) | 9 information, 17 prescription | aucune | aucun | clay |
| C033 | `35051000BE0641` | 2 109 | 0.006 | 2 096 | 37.0 | 11.5 | 1 | U|UI2 | 8 information, 20 prescription | aucune | aucun | aucun |
| C034 | `35051000ZV0293` | 2 209 | 0.076 | 2 042 | 45.6 | 3.5 | 1 | U|UE3 | 8 information, 15 prescription | aucune | plusieurs diagnostics — appariement ambigu | clay |
| C035 | `35051000AX0510` | 2 851 | 0.036 | 2 750 | 55.4 | 0.0 | 4 | U|UG4 | 18 information, 17 prescription | aucune | aucun | clay, sup_T1 |
| C036 | `35051000AT0051` | 2 791 | 0.120 | 2 455 | 40.4 | 3.6 | 3 | U|UE4 | 10 information, 17 prescription | aucune | aucun | clay |

## Ce que la revue doit produire

Un verdict par candidat — pertinent / non pertinent / indécidable — avec son motif, sans que le relecteur connaisse l'origine. Le protocole, les hypothèses mesurées et la conclusion attendue sont dans [E9](../backlog/E9-test-terrain-deux-professionnels.md).

