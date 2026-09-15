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

## L'âge du bâti, et ce qu'il vaut

Une maison de 1950 plantée au milieu de son terrain intéresse davantage un marchand qu'une maison de 2015 bien excentrée. L'âge est donc entré dans le classement — **en signal, jamais en filtre** : un bien récent n'est pas écarté, il passe derrière.

La source est `date_d_apparition` de BD TOPO, **renseignée sur 44,6 %** des bâtiments et **approximative pour l'ancien** : les valeurs se concentrent sur 1800, 1850, 1870, 1880 et 1900, signature d'une datation historique arrondie. C'est une période, pas une date d'acte, et une unité sans année reste classée sur les autres signaux.

BDNB porte la même information mieux : `ffo_bat_annee_construction`, renseignée à **68,9 %** et distribuée sur toutes les périodes. Elle est hors de portée faute de rattachement — aucun identifiant RNB, seul un appariement géométrique y mènerait. Entrée de plus pour [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md).

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

**Les parcelles en zone d'aménagement concerté sont écartées** depuis [E8i](../backlog/E8i-exclure-les-zac.md). Lire le code CNIG `information 02` n'est pas interpréter un règlement : c'est une entrée de dictionnaire, comme le type `U`. Le foncier d'une ZAC est sous la main de l'aménageur et du droit de préemption ; le premier passage en avait retenu dix sur trente-cinq, dont une dont les deux voisines avaient été achetées par un aménageur en 2020. Une parcelle est en ZAC si le périmètre couvre plus de 50% de sa surface — paramètre déclaré.

La colonne « Voisinage » porte la signature d'un aménageur quand elle existe : une voisine contiguë entrée dans un acte « Vente terrain à bâtir » d'au moins 3 parcelles. Contexte, jamais filtre — elle ne dépend pas du PLU.

## Le plancher de surface a été supprimé

Il valait 800 m² et faisait doublon : proxy grossier d'une divisibilité que le rayon inscriptible mesure directement depuis [E8c](../backlog/E8c-divisibilite-geometrique.md). Il écartait **348 parcelles pourtant divisibles** — 262 entre 600 et 800 m², 86 entre 400 et 600 — pour un vivier retenu de 357. Un seul critère décide désormais : le lot est-il inscriptible ? Voir [E8d](../backlog/E8d-seuils-parametrables.md).

| Tranche de surface | Unités du vivier |
|---|---:|
| moins de 400 m² | 1 |
| 400 à 600 m² | 86 |
| 600 à 800 m² | 261 |
| 800 à 1 000 m² | 126 |
| 1 000 à 1 500 m² | 165 |
| plus de 1 500 m² | 53 |

**La largeur minimale du lot vaut 12 m** — soit un rayon inscriptible de 6.0 m — et se règle par `make exploratory-candidates COMMUNE=… LOT_WIDTH=…`. C'est le seul seuil de sens métier de ce rapport.

**Cette valeur suppose un retrait obligatoire par rapport aux limites séparatives.** Là où le règlement autorise la construction en limite, un lot plus étroit reste constructible et la question change. Cette règle est dans le règlement du PLU, que [D2b](../backlog/D2b-profils-de-regles.md) doit rendre lisible et qui n'est pas livré : `URB-001` ne donne que le code de zone, jamais ce qu'il autorise. La valeur retenue est donc une hypothèse de travail, pas une contrainte physique.

## Paramètres — arbitraires, et c'est délibéré

Aucun profiling ne les fonde. Ils bornent une population de travail sur une commune ; ils ne définissent pas ce qu'est un bon candidat et n'anticipent pas [E1](../backlog/E1-profiling-distributions.md). Les contester fait partie de la revue.

| Paramètre | Valeur |
|---|---:|
| `max_parcel_area_m2` | 3000.0 |
| `max_footprint_ratio` | 0.2 |
| `min_width_m` | 15.0 |
| `min_building_count` | 1 |
| `zone_type` | U |
| `max_dwellings_per_building` | 2 |
| `setback_m` | 3.0 |
| `zac_min_coverage` | 0.5 |
| `developer_min_parcels` | 3 |
| `min_lot_width_m` | 12.0 |

## Entonnoir

| Étape | Unités restantes |
|---|---:|
| population | 9 329 |
| bâtie | 6 412 |
| surface connue | 6 412 |
| surface plafonnée | 5 761 |
| emprise connue | 5 761 |
| emprise faible | 2 315 |
| largeur connue | 2 315 |
| largeur suffisante | 1 951 |
| zone connue | 1 951 |
| zone constructible | 1 744 |
| contraintes connues | 1 744 |
| hors ZAC | 1 708 |
| usage résidentiel connu | 1 466 |
| nature résidentielle | 1 464 |
| habitat individuel | 1 452 |
| forme mesurée | 1 452 |
| lot inscriptible | 692 |

**692 unités éligibles**  dont 20 retenues par chaque ordre.

## Les deux ordres, et leur recouvrement

La baseline est le tri cadastral simple que H1 demande de battre : surface décroissante. Le classement ordonne **la même population** par le rang moyen des signaux morphologiques disponibles — `built_year`, `free_radius_m`, `footprint_ratio`, `width_m`, `boundary_distance_m`.

| | |
|---|---:|
| Candidats issus de la baseline seule | 13 |
| Candidats issus du classement seul | 13 |
| Communs aux deux ordres | 7 |
| **Total remis au relecteur** | **33** |

Les deux ordres diffèrent sur 26 candidats. C'est cet écart que la revue en aveugle départage.

0 candidats sont classés sur moins de 5 signaux, un signal absent n'étant pas remplacé par zéro.

## Candidats

L'origine de chaque candidat — baseline ou classement — n'est **pas** dans ce tableau : elle est dans `docs/data/exploratory-candidates/35051/correspondance.csv`, que le relecteur ne voit pas. La liste remise est `docs/data/exploratory-candidates/35051/liste-aveugle.csv`.

| Réf. | Parcelle | Année | Surface m² | Emprise | Rayon libre m | Voirie m | Largeur m | Recul m | Bât. | Usage | Log. | Zone | Contraintes | Mutation | DPE | Risques fins | Voisinage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|---|---|---|
| C001 | `35051000ZV0194` | 1800 | 1 026 | 0.110 | 9.2 | 3.0 | 32.8 | 0.0 | 1 | Résidentiel | 1 | U|UE3 | 9 information, 14 prescription | aucune | aucun | clay | aucun signal |
| C002 | `35051000ZT0144` | 1931 | 1 490 | 0.104 | 10.6 | 4.2 | 34.5 | 0.0 | 4 | Annexe · Indifférencié · Résidentiel | 1 | U|UE3 | 8 information, 16 prescription | aucune | E | clay | aucun signal |
| C003 | `35051000ZS0176` | 1978 | 2 532 | 0.133 | 11.5 | 3.5 | 54.9 | 0.0 | 2 | Résidentiel | 1 | U|UE3 | 10 information, 15 prescription | 2022-10-07 | C | clay, sup_AC1 | aucun signal |
| C004 | `35051000AY0071` | 1955 | 1 795 | 0.061 | 9.3 | 5.0 | 28.7 | 0.0 | 4 | Indifférencié · Résidentiel | 1 | U|UI1a | 9 information, 20 prescription | aucune | aucun | aucun | aucun signal |
| C005 | `35051000ZV0320` | 1850 | 1 222 | 0.110 | 12.8 | 3.3 | 39.9 | 0.0 | 1 | Indifférencié · Résidentiel | 1 | U|UE3 | 8 information, 13 prescription | 2018-11-28 | aucun | clay | aucun signal |
| C006 | `35051000BE0017` | 1954 | 1 398 | 0.054 | 11.0 | 4.6 | 22.3 | 0.0 | 1 | Résidentiel | 1 | U|UE3 | 12 information, 22 prescription | 2019-09-06 | aucun | clay, sup_PM1 | aucun signal |
| C007 | `35051000ZT0062` | 1981 | 2 241 | 0.051 | 15.1 | 0.0 | 30.7 | 6.7 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 16 prescription | 2017-04-20 | aucun | clay | aucun signal |
| C008 | `35051000AR0283` | 1720 | 2 852 | 0.085 | 15.4 | 1.6 | 60.5 | 0.0 | 7 | Annexe · Résidentiel | 1 | U|UO1 | 10 information, 19 prescription | aucune | aucun | clay | aucun signal |
| C009 | `35051000ZV0230` | 2007 | 2 059 | 0.097 | 13.1 | 2.1 | 39.0 | 5.0 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay | aucun signal |
| C010 | `35051000AY0064` | 1989 | 2 507 | 0.087 | 16.3 | 4.5 | 51.5 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UE2h | 12 information, 24 prescription | aucune | aucun | clay | aucun signal |
| C011 | `35051000ZV0293` | 1980 | 2 209 | 0.076 | 15.6 | 4.1 | 45.6 | 3.5 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 15 prescription | aucune | plusieurs diagnostics — appariement ambigu | clay | aucun signal |
| C012 | `35051000ZV0217` | 2006 | 1 927 | 0.158 | 13.7 | 4.0 | 37.6 | 5.6 | 1 | Résidentiel | 1 | U|UE3 | 9 information, 15 prescription | aucune | aucun | clay | aucun signal |
| C013 | `35051000ZV0262` | 2011 | 2 022 | 0.141 | 12.8 | 3.1 | 37.6 | 4.2 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 15 prescription | aucune | aucun | clay | aucun signal |
| C014 | `35051000YD0141` | 1969 | 1 878 | 0.101 | 15.0 | 5.6 | 30.2 | 0.0 | 3 | Indifférencié · Résidentiel | 1 | U|UE2d | 9 information, 18 prescription | aucune | aucun | aucun | aucun signal |
| C015 | `35051000YE0133` | 1978 | 2 320 | 0.067 | 12.4 | 2.5 | 62.7 | 0.0 | 3 | Résidentiel | 1 | U|UE3 | 10 information, 18 prescription | aucune | aucun | clay | aucun signal |
| C016 | `35051000ZT0145` | 2008 | 2 004 | 0.111 | 10.6 | 5.0 | 38.4 | 0.0 | 3 | Annexe · Résidentiel | 1 | U|UE3 | 8 information, 17 prescription | 2018-09-17 | aucun | clay | aucun signal |
| C017 | `35051000ZV0279` | 1980 | 1 908 | 0.085 | 13.4 | 1.3 | 30.1 | 5.0 | 1 | Annexe · Résidentiel | 1 | U|UE3 | 8 information, 15 prescription | aucune | aucun | clay | aucun signal |
| C018 | `35051000ZB0082` | 1995 | 2 533 | 0.077 | 14.3 | 4.7 | 40.4 | 0.0 | 1 | Résidentiel | 1 | U|UE3 | 8 information, 14 prescription | aucune | aucun | clay | aucun signal |
| C019 | `35051000AL0015` | 1900 | 1 793 | 0.129 | 14.3 | 14.9 | 45.8 | 0.0 | 2 | Résidentiel | 1 | U|UE2h | 11 information, 21 prescription | 2017-03-16 | aucun | clay | aucun signal |
| C020 | `35051000AW0225` | 1972 | 2 166 | 0.065 | 10.5 | 0.9 | 41.3 | 5.9 | 1 | Résidentiel | 1 | U|UE2c(d) | 10 information, 16 prescription | aucune | aucun | clay | aucun signal |
| C021 | `35051000YA0165` | 1850 | 2 210 | 0.105 | 13.7 | 0.0 | 44.8 | 0.0 | 2 | Résidentiel | 1 | U|UE2h | 10 information, 15 prescription | aucune | aucun | aucun | aucun signal |
| C022 | `35051000YH0008` | 1974 | 1 804 | 0.000 | 15.7 | 4.5 | 35.2 | 0.0 | 1 | Résidentiel | 1 | U|UI1a(d) | 8 information, 15 prescription | aucune | aucun | aucun | aucun signal |
| C023 | `35051000AT0278` | 1993 | 1 920 | 0.121 | 16.4 | 9.0 | 33.2 | 0.0 | 2 | Résidentiel | 1 | U|UE3 | 9 information, 18 prescription | 2024-06-21 | D | clay | aucun signal |
| C024 | `35051000AY0084` | 1871 | 1 583 | 0.144 | 13.9 | 0.0 | 35.5 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UE2h | 8 information, 14 prescription | aucune | aucun | clay | aucun signal |
| C025 | `35051000ZV0141` | 1983 | 2 420 | 0.062 | 12.0 | 4.5 | 37.7 | 0.0 | 7 | Annexe · Indifférencié · Résidentiel | 1 | U|UE3 | 9 information, 15 prescription | aucune | aucun | clay | aucun signal |
| C026 | `35051000BE0086` | 1860 | 1 631 | 0.071 | 12.3 | 11.6 | 41.4 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UG2b | 10 information, 18 prescription | aucune | aucun | clay, sup_PM1 | aucun signal |
| C027 | `35051000AK0347` | 1934 | 952 | 0.109 | 11.1 | 16.0 | 28.0 | 1.9 | 1 | Résidentiel | 1 | U|UE2c(d) | 11 information, 15 prescription | aucune | aucun | clay | aucun signal |
| C028 | `35051000ZV0136` | 1982 | 2 667 | 0.065 | 11.8 | 1.5 | 67.2 | 1.9 | 2 | Annexe · Résidentiel | 1 | U|UE3 | 8 information, 13 prescription | aucune | aucun | clay | aucun signal |
| C029 | `35051000AY0292` | 1850 | 1 745 | 0.140 | 13.2 | 4.2 | 36.2 | 0.0 | 2 | Annexe · Résidentiel | 1 | U|UE2h | 12 information, 22 prescription | 2014-10-02 | aucun | clay | aucun signal |
| C030 | `35051000ZV0250` | 2010 | 2 838 | 0.062 | 13.5 | 2.8 | 49.9 | 12.3 | 1 | Résidentiel | 1 | U|UE3 | 10 information, 17 prescription | aucune | aucun | clay | aucun signal |
| C031 | `35051000AS0337` | 1951 | 1 400 | 0.098 | 7.6 | 5.9 | 35.2 | 0.0 | 4 | Annexe · Résidentiel | 1 | U|UE1a | 8 information, 18 prescription | aucune | aucun | clay | aucun signal |
| C032 | `35051000YA0032` | 1973 | 2 055 | 0.116 | 8.9 | 5.0 | 46.4 | 0.0 | 2 | Résidentiel | 1 | U|UE2c(d) | 10 information, 14 prescription | aucune | aucun | clay | aucun signal |
| C033 | `35051000AW0231` | 1939 | 2 645 | 0.127 | 17.2 | 0.9 | 42.1 | 0.0 | 3 | Indifférencié · Résidentiel | 1 | U|UE2c | 9 information, 15 prescription | aucune | aucun | clay | aucun signal |

## Ce que la revue doit produire

Un verdict par candidat — pertinent / non pertinent / indécidable — avec son motif, sans que le relecteur connaisse l'origine. Le protocole, les hypothèses mesurées et la conclusion attendue sont dans [E9](../backlog/E9-test-terrain-deux-professionnels.md).

