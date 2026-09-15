# Liste exploratoire de candidats — commune 35051

**Généré le :** 2026-09-15 · **Ticket :** [E8](../backlog/E8-liste-exploratoire-terrain.md) · **Graine :** `20260915`

Ce fichier est **régénéré** par `make exploratory-candidates`. Ne pas l'éditer à la main.

## Ce que cette liste est, et n'est pas

Elle **n'est pas un score publié**. Aucun `OpportunitySnapshot` n'a été créé, aucune unité n'est devenue publiable, et les 1 333 327 unités du 35 restent en `entity_resolution_incomplete`. C'est une requête de lecture, destinée à être montrée à un professionnel par [E9](../backlog/E9-test-terrain-deux-professionnels.md).

**Chaque ligne désigne une parcelle, pas un bien.** [BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md) mesure cette limite : l'unité foncière au sens juridique suppose le propriétaire, hors périmètre, et la contiguïté seule produit des grappes de plusieurs milliers de parcelles. Un garage sur parcelle propre apparaît donc ici comme un candidat distinct de la maison voisine. Savoir si cette limite est rédhibitoire fait partie de ce que la revue doit établir.

## Ce que la forme du terrain libre mesure, et ce qu'aucune source ne mesure

Seconde relecture, motif devenu unique : « la maison est trop centrée pour déparcelliser ». La **surface** libre n'en dit rien — une maison centrée laisse un anneau connexe couvrant 75 % à 91 % de la parcelle, rejetées et retenues confondues. Le classement porte donc désormais sur le rayon du plus grand cercle inscriptible dans la partie libre, bâti tamponné de 3 m, et `LAND-007` a repris son sens : un bâti **proche** d'une limite laisse un côté libre, et c'est lui qu'on remonte.

Deux motifs de rejet relevés n'ont **aucune source dans le dépôt**, et rien ici ne les voit :

| Motif | Source qui le porterait | État |
|---|---|---|
| « c'est déjà goudronné » | couverture du sol, OCS GE | cité `SPEC.md` §27, non importé, sans contrat DS-* |
| « il y a une piscine » | constructions surfaciques BD TOPO | seule la couche bâtiment est importée |

**Cas manqué consigné :** `35051000ZS0176` — rayon inscriptible 11,5 m, usage et nature résidentiels, un logement — a été rejetée à la relecture pour une maison « trop grande et en plein milieu ». Aucune source disponible ne porte ce jugement. Elle est consignée telle quelle plutôt qu'écartée par un seuil taillé sur elle.

## L'usage du bâti, et la source d'où il vient

Dix candidats de la première liste relus à la main : **deux d'intérêt**, les autres des délaissés de voirie, des parcelles industrielles, des espaces verts et des immeubles. La cause est nommée dans [E8b](../backlog/E8b-usage-du-bati.md) : « grande parcelle, petit bâtiment » décrit aussi bien un jardin de maison qu'un espace vert communal. Le filtre exige désormais un usage **résidentiel** et un habitat **individuel**.

**L'usage vient de DS-04 BD TOPO, release `display_only`.** Ce n'est acceptable que parce que cette liste ne publie rien et sert à être contestée. Un score publié ne pourrait pas s'appuyer dessus. Le rattachement se fait par `identifiants_rnb`, déclaré par le producteur — aucun appariement géométrique, donc aucune des erreurs mesurées par [B4](../backlog/B4-revue-manuelle-appariements.md).

| Population avant filtre d'usage | Unités |
|---|---:|
| usage résidentiel connu | 4 291 |
| usage non résidentiel connu | 681 |
| usage indifférencié | 516 |
| aucun bâtiment BD TOPO rattaché | 3 841 |

`Indifférencié` n'est pas « non résidentiel » : c'est un inconnu. Exiger le résidentiel connu écarte donc aussi l'inconnu, et le volume perdu est publié ci-dessus plutôt que fondu dans un taux unique.

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
| `max_dwellings_per_building` | 2 |
| `setback_m` | 3.0 |
| `min_free_radius_m` | 6.0 |

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
| usage résidentiel connu | 392 |
| nature résidentielle | 389 |
| habitat individuel | 378 |
| forme mesurée | 378 |
| lot inscriptible | 357 |

**357 unités éligibles**  dont 20 retenues par chaque ordre.

## Les deux ordres, et leur recouvrement

La baseline est le tri cadastral simple que H1 demande de battre : surface décroissante. Le classement ordonne **la même population** par le rang moyen des signaux morphologiques disponibles — `free_radius_m`, `footprint_ratio`, `width_m`, `boundary_distance_m`.

| | |
|---|---:|
| Candidats issus de la baseline seule | 10 |
| Candidats issus du classement seul | 10 |
| Communs aux deux ordres | 10 |
| **Total remis au relecteur** | **30** |

Les deux ordres diffèrent sur 20 candidats. C'est cet écart que la revue en aveugle départage.

0 candidats sont classés sur moins de 4 signaux, un signal absent n'étant pas remplacé par zéro.

## Candidats

L'origine de chaque candidat — baseline ou classement — n'est **pas** dans ce tableau : elle est dans `docs/data/exploratory-candidates/35051/correspondance.csv`, que le relecteur ne voit pas. La liste remise est `docs/data/exploratory-candidates/35051/liste-aveugle.csv`.

| Réf. | Parcelle | Surface m² | Emprise | Rayon libre m | Voirie m | Largeur m | Recul m | Bât. | Usage | Log. | Zone | Contraintes | Mutation | DPE | Risques fins |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|---|---|
| C001 | `35051000YE0133` | 2 320 | 0.067 | 12.4 | 2.5 | 62.7 | 0.0 | 3 | Résidentiel | 1 | U|UE3 | 10 information, 18 prescription | aucune | aucun | clay |
| C002 | `35051000YB0151` | 1 851 | 0.092 | 14.2 | 5.8 | 37.4 | 0.0 | 3 | Annexe · Résidentiel | 1 | U|UE2h(d) | 11 information, 20 prescription | 2023-11-23 | aucun | aucun |
| C003 | `35051000YA0165` | 2 210 | 0.105 | 13.7 | 0.0 | 44.8 | 0.0 | 2 | Résidentiel | 1 | U|UE2h | 10 information, 15 prescription | aucune | aucun | aucun |
| C004 | `35051000ZY0198` | 2 372 | 0.114 | 14.0 | 3.7 | 42.8 | 2.4 | 2 | Indifférencié · Résidentiel | 1 | U|UE2h(d) | 10 information, 17 prescription | aucune | aucun | aucun |
| C005 | `35051000ZV0230` | 2 059 | 0.097 | 13.1 | 2.1 | 39.0 | 5.0 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay |
| C006 | `35051000ZV0293` | 2 209 | 0.076 | 15.6 | 4.1 | 45.6 | 3.5 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 15 prescription | aucune | plusieurs diagnostics — appariement ambigu | clay |
| C007 | `35051000ZE0186` | 2 508 | 0.046 | 18.1 | 4.5 | 41.1 | 8.7 | 1 | Résidentiel | 1 | U|UE2h(d) | 9 information, 14 prescription | aucune | aucun | aucun |
| C008 | `35051000ZT0139` | 1 835 | 0.096 | 11.5 | 0.0 | 40.4 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UE3 | 9 information, 18 prescription | aucune | aucun | clay |
| C009 | `35051000ZB0082` | 2 533 | 0.077 | 14.3 | 4.7 | 40.4 | 0.0 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay |
| C010 | `35051000ZV0320` | 1 222 | 0.110 | 12.8 | 3.3 | 39.9 | 0.0 | 1 | Indifférencié · Résidentiel | 1 | U|UE3 | 8 information, 13 prescription | aucune | aucun | clay |
| C011 | `35051000ZV0250` | 2 838 | 0.062 | 13.5 | 2.8 | 49.9 | 12.3 | 1 | Résidentiel | 1 | U|UE3 | 10 information, 17 prescription | aucune | aucun | clay |
| C012 | `35051000AW0225` | 2 166 | 0.065 | 10.5 | 0.9 | 41.3 | 5.9 | 1 | Résidentiel | 1 | U|UE2c(d) | 10 information, 16 prescription | aucune | aucun | clay |
| C013 | `35051000AR0283` | 2 852 | 0.085 | 15.4 | 1.6 | 60.5 | 0.0 | 7 | Annexe · Résidentiel | 1 | U|UO1 | 10 information, 19 prescription | aucune | aucun | clay |
| C014 | `35051000ZS0170` | 1 204 | 0.105 | 10.4 | 1.9 | 38.2 | 0.0 | 2 | Indifférencié · Résidentiel | 1 | U|UE3 | 9 information, 16 prescription | aucune | aucun | clay |
| C015 | `35051000ZV0136` | 2 667 | 0.065 | 11.8 | 1.5 | 67.2 | 1.9 | 2 | Annexe · Résidentiel | 1 | U|UE3 | 8 information, 13 prescription | aucune | aucun | clay |
| C016 | `35051000BE0086` | 1 631 | 0.071 | 12.3 | 11.6 | 41.4 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UG2b | 10 information, 18 prescription | aucune | aucun | clay, sup_PM1 |
| C017 | `35051000ZB0107` | 1 418 | 0.098 | 12.0 | 4.8 | 43.8 | 0.0 | 2 | Résidentiel | 1 | U|UE2c | 11 information, 15 prescription | aucune | aucun | clay |
| C018 | `35051000ZS0176` | 2 532 | 0.133 | 11.5 | 3.5 | 54.9 | 0.0 | 2 | Résidentiel | 1 | U|UE3 | 10 information, 15 prescription | 2022-10-07 | C | clay, sup_AC1 |
| C019 | `35051000AY0064` | 2 507 | 0.087 | 16.3 | 4.5 | 51.5 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UE2h | 12 information, 24 prescription | aucune | aucun | clay |
| C020 | `35051000YC0199` | 1 677 | 0.103 | 13.3 | 3.8 | 34.0 | 0.0 | 2 | Résidentiel | 1 | U|UE2h(d) | 9 information, 15 prescription | aucune | aucun | clay |
| C021 | `35051000YH0008` | 1 804 | 0.000 | 15.7 | 4.5 | 35.2 | 0.0 | 1 | Résidentiel | 1 | U|UI1a(d) | 8 information, 15 prescription | aucune | aucun | aucun |
| C022 | `35051000AL0015` | 1 793 | 0.129 | 14.3 | 14.9 | 45.8 | 0.0 | 2 | Résidentiel | 1 | U|UE2h | 11 information, 21 prescription | aucune | aucun | clay |
| C023 | `35051000YD0141` | 1 878 | 0.101 | 15.0 | 5.6 | 30.2 | 0.0 | 3 | Indifférencié · Résidentiel | 1 | U|UE2d | 9 information, 18 prescription | aucune | aucun | aucun |
| C024 | `35051000ZV0262` | 2 022 | 0.141 | 12.8 | 3.1 | 37.6 | 4.2 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 15 prescription | aucune | aucun | clay |
| C025 | `35051000YA0032` | 2 055 | 0.116 | 8.9 | 5.0 | 46.4 | 0.0 | 2 | Résidentiel | 1 | U|UE2c(d) | 10 information, 14 prescription | aucune | aucun | clay |
| C026 | `35051000ZV0217` | 1 927 | 0.158 | 13.7 | 4.0 | 37.6 | 5.6 | 1 | Résidentiel | 1 | U|UE3 | 9 information, 15 prescription | aucune | aucun | clay |
| C027 | `35051000AW0231` | 2 645 | 0.127 | 17.2 | 0.9 | 42.1 | 0.0 | 3 | Indifférencié · Résidentiel | 1 | U|UE2c | 9 information, 15 prescription | aucune | aucun | clay |
| C028 | `35051000ZV0141` | 2 420 | 0.062 | 12.0 | 4.5 | 37.7 | 0.0 | 7 | Annexe · Indifférencié · Résidentiel | 1 | U|UE3 | 9 information, 15 prescription | aucune | aucun | clay |
| C029 | `35051000ZT0062` | 2 241 | 0.051 | 15.1 | 0.0 | 30.7 | 6.7 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 16 prescription | aucune | aucun | clay |
| C030 | `35051000ZT0145` | 2 004 | 0.111 | 10.6 | 5.0 | 38.4 | 0.0 | 3 | Annexe · Résidentiel | 1 | U|UE3 | 8 information, 17 prescription | aucune | aucun | clay |

## Ce que la revue doit produire

Un verdict par candidat — pertinent / non pertinent / indécidable — avec son motif, sans que le relecteur connaisse l'origine. Le protocole, les hypothèses mesurées et la conclusion attendue sont dans [E9](../backlog/E9-test-terrain-deux-professionnels.md).

