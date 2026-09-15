# Biens probablement en vente — commune 35051

**Généré le :** 2026-09-15 · **Ticket :** [E8f](../backlog/E8f-liste-biens-en-vente.md) · **Graine :** `20260915` · **Extrait DPE au :** 2026-09-07

Ce fichier est **régénéré** par `make biens-en-vente`. Ne pas l'éditer à la main.

## Ce que cette liste dit, et ce qu'elle ne dit pas

Elle dit : **un DPE a été déposé à cette date**. C'est un fait administratif, daté et public, obligatoire pour mettre un logement en vente. Ce n'est pas un modèle : rien n'est appris, aucun seuil n'est inventé, et chaque ligne s'explique par sa date.

Elle **ne dit pas** que le bien sera vendu. Mesuré sur le 35 dans [`dpe-signal-vente-35.md`](./dpe-signal-vente-35.md) : **35,65 %** des parcelles dont le premier DPE a été déposé en 2024 ont muté dans les douze mois, contre **3,03 %** de l'ensemble des parcelles bâties — lift 11,8 fois. **Deux tiers ne mutent donc pas dans l'année.**

Le dépôt précède l'acte de **169 jours en médiane**, soit environ 80 jours avant le compromis : le signal arrive à la mise en vente, pas après.

## Quatre limites, dont deux sérieuses

**Le motif du diagnostic n'est pas publié.** `methode_application_dpe` donne le périmètre de calcul — maison, appartement, immeuble — jamais la raison. Un DPE de **location** est indiscernable d'un DPE de vente. Cette dilution est déjà dans le 35,65 %.

**DVF s'arrête au 31 décembre 2025.** Pour les dépôts récents, « aucune mutation depuis » est un défaut de données autant qu'un fait de marché. Le filtre l'applique là où la donnée existe, et ne peut rien affirmer au-delà.

**Le rattachement du DPE au bâtiment plafonne à 59 %** — voir [`dpe-matching-35.md`](./dpe-matching-35.md). Les diagnostics rattachés à la seule adresse sont absents de cette liste.

**Un seul département, une seule cohorte annuelle** fondent le lift — et les taux ci-dessous, mesurés à la génération sur la cohorte de référence.

## Les deux cohortes, et pourquoi la baseline est celle-là

La fenêtre se compte depuis la **date d'extrait**, 2026-09-07, jamais depuis l'horloge : sinon la liste se viderait toute seule à mesure que l'extrait vieillit, sans que rien ne le signale.

| Cohorte | Définition | Unités |
|---|---|---:|
| **Signal** | DPE déposé depuis moins de 6 mois | 18 |
| Baseline | DPE déposé il y a plus de 24 mois | 163 |

Les deux sortent de **la même population** — résidentiel individuel en zone constructible — et ne diffèrent que par la fraîcheur du dépôt. C'est exactement ce que la liste revendique ; un tri par surface n'y répondrait pas.

## Entonnoir

| Étape | Unités restantes |
|---|---:|
| parcelles avec diagnostic | 728 |
| usage résidentiel connu | 678 |
| nature résidentielle | 670 |
| habitat individuel | 575 |
| zone connue | 575 |
| zone constructible | 549 |
| pas de mutation depuis le diagnostic | 283 |

## Ce que la cohorte de référence dit — trois lectures, jamais combinées

Cohorte : parcelles du département 35 dont le premier DPE de **maison** a été déposé en **2024** — la dernière année civile dont les douze mois de suivi sont couverts par DVF, arrêtée au 2025-12-31. Issue : au moins une mutation dans les douze mois. Relations bâtiment ↔ parcelle certaines seulement ; à date égale, le premier DPE par numéro. Les DPE d'appartement générés depuis un DPE d'immeuble, qui convertissent à moins de 1 %, en sont exclus.

| Population | Parcelles | Vendues dans les 12 mois |
|---|---:|---:|
| Département 35, maisons | 8 028 | 39,4 % |
| Commune 35051, maisons | 126 | 35,7 % |

Le taux de la commune est donné avec son effectif, **jamais masqué sous un minimum** : le relecteur juge lui-même ce que vaut un taux sur quelques dizaines de parcelles.

**Courbe de conversion** — part vendue selon les mois écoulés depuis le dépôt :

| Mois | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Cumul vendu | 0,0 % | 0,2 % | 0,5 % | 2,1 % | 8,7 % | 16,1 % | 21,9 % | 26,5 % | 29,8 % | 33,2 % | 35,7 % | 37,8 % | 39,4 % |

La colonne « chance de vente sous 6 mois » se lit sur cette courbe : part de la cohorte vendue entre l'âge du candidat et cet horizon, parmi celles encore invendues à cet âge. L'horizon est **arbitraire et déclaré**, comme les fenêtres. Au-delà de la portée de la courbe, la valeur manque — elle n'est pas extrapolée.

**Par étiquette** — taux à douze mois, même cohorte :

| Étiquette | Parcelles | Vendues dans les 12 mois |
|---|---:|---:|
| A | 334 | 42,8 % |
| B | 500 | 40,6 % |
| C | 2 694 | 35,9 % |
| D | 2 587 | 38,5 % |
| E | 1 128 | 43,1 % |
| F | 519 | 48,7 % |
| G | 266 | 44,4 % |

Âge et étiquette sont deux lectures **indépendantes** de la même cohorte. Elles ne se combinent pas : les combiner serait un modèle, et rien n'établit leur indépendance.

## Candidats

L'origine — signal ou baseline — est dans `docs/data/biens-en-vente/35051/correspondance.csv`, que le relecteur ne voit pas.

| Réf. | Parcelle | Adresse du DPE | DPE déposé | Âge (mois) | Chance de vente sous 6 mois (âge) | Étiquette | Taux 12 mois (étiquette) | Surface hab. | Année | Parcelle m² | Zone | Dernière mutation |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---|
| C001 | `35051000BH0260` | 40 Rue des Gardes 35510 Cesson-Sévigné | 2024-06-14 | 26 | non mesurée — hors courbe | C | 35,9 % | 145.4 | 1995 | 608 | U|UE2c(d) | aucune |
| C002 | `35051000AZ0656` | 30 Rue de la Monniais 35510 Cesson-Sévigné | 2024-07-17 | 25 | non mesurée — hors courbe | D | 38,5 % | 26.3 | 2003 | 671 | U|UE2c(d) | aucune |
| C003 | `35051000AZ0490` | 38 Rue de l'Etournel 35510 Cesson-Sévigné | 2026-04-04 | 5 | 25,8 % | B | 40,6 % | 171.8 | 2002 | 613 | U|UE2c(d) | 2023-07-28 |
| C004 | `35051000ZS0045` | 4 Rue de la Plesse 35510 Cesson-Sévigné | 2026-05-12 | 3 | 31,7 % | F | 48,7 % | 82.5 | 2004 | 535 | U|UE3 | aucune |
| C005 | `35051000AK0130` | 3 Rue du Hyl 35510 Cesson-Sévigné | 2024-08-30 | 24 | non mesurée — hors courbe | C | 35,9 % | absente | 1979 | 608 | U|UE2c(d) | aucune |
| C006 | `35051000AZ0593` | 47 Rue des Ormeaux 35510 Cesson-Sévigné | 2026-03-26 | 5 | 25,8 % | C | 35,9 % | 133 | 2004 | 587 | U|UE2c(d) | aucune |
| C007 | `35051000AN0260` | Allée des Rosiers 35510 Cesson-Sévigné | 2026-08-19 | 0 | 21,9 % | D | 38,5 % | 80.1 | 1932 | 193 | U|UE2c(d) | aucune |
| C008 | `35051000AR0094` | 2 Rue de la Fresnerie 35510 Cesson-Sévigné | 2026-07-17 | 1 | 26,4 % | D | 38,5 % | 13.4 | 1800 | 112 | U|UA1a | aucune |
| C009 | `35051000AP0158` | 17 Rue des Lauriers 35510 Cesson-Sévigné | 2024-06-13 | 26 | non mesurée — hors courbe | D | 38,5 % | 193 | 1971 | 1 417 | U|UE2c(d) | aucune |
| C010 | `35051000AZ0698` | 47 Rue des Galardières 35510 Cesson-Sévigné | 2024-05-06 | 28 | non mesurée — hors courbe | C | 35,9 % | 188 | 2003 | 628 | U|UE2c(d) | aucune |
| C011 | `35051000AW0141` | 61 Rue de Rennes 35510 Cesson-Sévigné | 2026-08-28 | 0 | 21,9 % | D | 38,5 % | 153 | 1962 | 389 | U|UE1a | aucune |
| C012 | `35051000AB0054` | 78 Rue de la Coulée 35510 Cesson-Sévigné | 2024-07-31 | 25 | non mesurée — hors courbe | D | 38,5 % | 132 | 1974 | 639 | U|UE2c(d) | aucune |
| C013 | `35051000AK0102` | 40 Rue du Hyl 35510 Cesson-Sévigné | 2026-06-23 | 2 | 29,4 % | D | 38,5 % | 119.4 | 1980 | 715 | U|UE2c(d) | aucune |
| C014 | `35051000AH0126` | 7 Rue de la Chesnaie 35510 Cesson-Sévigné | 2024-04-26 | 28 | non mesurée — hors courbe | D | 38,5 % | 145 | 1978 | 477 | U|UE2c(d) | 2021-07-30 |
| C015 | `35051000AD0060` | 56 Rue des Petits Champs 35510 Cesson-Sévigné | 2026-04-09 | 4 | 29,6 % | D | 38,5 % | 102.5 | 1978 | 218 | U|UE2c | 2018-05-04 |
| C016 | `35051000AN0182` | 3 Rue de la Rabine 35510 Cesson-Sévigné | 2024-07-03 | 26 | non mesurée — hors courbe | C | 35,9 % | 177.1 | 1983 | 904 | U|UE2c(d) | 2018-07-30 |
| C017 | `35051000AN0364` | 15 Rue du Grand Champ 35510 Cesson-Sévigné | 2026-03-20 | 5 | 25,8 % | D | 38,5 % | 98.7 | 1974 | 173 | U|UE2c | aucune |
| C018 | `35051000AA0132` | 17 Rue du Pressoir 35510 Cesson-Sévigné | 2024-06-02 | 27 | non mesurée — hors courbe | C | 35,9 % | 152.2 | 1988 | 723 | U|UE2c(d) | aucune |
| C019 | `35051000AE0129` | 22 Rue du Champ Gaudois 35510 Cesson-Sévigné | 2024-05-28 | 27 | non mesurée — hors courbe | D | 38,5 % | 80.5 | 1978 | 547 | U|UE2c(d) | aucune |
| C020 | `35051000YA0156` | 15 Rue de la Garenne 35510 Cesson-Sévigné | 2024-08-20 | 24 | non mesurée — hors courbe | D | 38,5 % | 130 | 1995 | 560 | U|UE2c(d) | aucune |
| C021 | `35051000AZ0561` | 39 Rue de la Monniais 35510 Cesson-Sévigné | 2024-06-05 | 27 | non mesurée — hors courbe | C | 35,9 % | 187.1 | 2003 | 679 | U|UE2c(d) | aucune |
| C022 | `35051000AB0186` | 27 Rue de la Chalotais 35510 Cesson-Sévigné | 2026-06-01 | 3 | 31,7 % | C | 35,9 % | 160.8 | 1973 | 531 | U|UE2c(d) | 2022-09-15 |
| C023 | `35051000AT0203` | 29 Rue du Petit Marais 35510 Cesson-Sévigné | 2026-04-22 | 4 | 29,6 % | C | 35,9 % | 95.1 | 1998 | 282 | U|UE2c | aucune |
| C024 | `35051000BD0140` | 21 Rue de la Pommeraie 35510 Cesson-Sévigné | 2026-05-26 | 3 | 31,7 % | D | 38,5 % | 234.4 | 1992 | 557 | U|UE2c(d) | aucune |
| C025 | `35051000AB0229` | 6 Rue du Courtil 35510 Cesson-Sévigné | 2026-03-18 | 5 | 25,8 % | F | 48,7 % | 102.4 | 1975 | 601 | U|UE2c(d) | aucune |
| C026 | `35051000AS0017` | 2 Rue du Verger 35510 Cesson-Sévigné | 2026-06-01 | 3 | 31,7 % | E | 43,1 % | 167.3 | 1970 | 691 | U|UE2c(d) | aucune |
| C027 | `35051000AK0249` | 10 Allée des Tulipes 35510 Cesson-Sévigné | 2024-04-23 | 28 | non mesurée — hors courbe | D | 38,5 % | 145 | 1955 | 472 | U|UE2c | aucune |
| C028 | `35051000AN0356` | 16 Rue du Grand Champ 35510 Cesson-Sévigné | 2024-08-27 | 24 | non mesurée — hors courbe | D | 38,5 % | 83.9 | 1974 | 159 | U|UE2c | aucune |
| C029 | `35051000AB0203` | 18 Avenue de Caradeuc 35510 Cesson-Sévigné | 2024-08-05 | 25 | non mesurée — hors courbe | E | 43,1 % | 135.9 | 1973 | 357 | U|UE2c(d) | aucune |
| C030 | `35051000AE0155` | 5 Rue des Petits Champs 35510 Cesson-Sévigné | 2024-06-03 | 27 | non mesurée — hors courbe | E | 43,1 % | 104.4 | 1977 | 292 | U|UE2c | aucune |
| C031 | `35051000AW0043` | 9 Allée des Korrigans 35510 Cesson-Sévigné | 2026-05-21 | 3 | 31,7 % | D | 38,5 % | 96.4 | 1968 | 492 | U|UE2c(d) | 2025-07-21 |
| C032 | `35051000AW0123` | 4 Rue de Bel Air 35510 Cesson-Sévigné | 2026-05-05 | 4 | 29,6 % | E | 43,1 % | 106.8 | 1958 | 365 | U|UE2c | aucune |
| C033 | `35051000AA0311` | 26 Rue de la Grande Pierre 35510 Cesson-Sévigné | 2026-03-27 | 5 | 25,8 % | D | 38,5 % | 112.1 | 1986 | 490 | U|UE2c(d) | aucune |
| C034 | `35051000AR0102` | 3 Place de l'Eglise 35510 Cesson-Sévigné | 2024-06-24 | 26 | non mesurée — hors courbe | C | 35,9 % | 67 | 1880 | 115 | U|UA1a | 2015-12-18 |
| C035 | `35051000ZT0172` | 26 Route de Chantepie 35510 Cesson-Sévigné | 2024-08-18 | 24 | non mesurée — hors courbe | D | 38,5 % | 162.8 | 1972 | 4 296 | U|UE3 | aucune |
| C036 | `35051000AK0196` | 4 Allée des Fauvettes 35510 Cesson-Sévigné | 2024-06-16 | 26 | non mesurée — hors courbe | E | 43,1 % | 62.2 | 1955 | 278 | U|UE2c | aucune |
| C037 | `35051000AD0057` | 50 Rue des Petits Champs 35510 Cesson-Sévigné | 2026-04-30 | 4 | 29,6 % | D | 38,5 % | 95.8 | 1978 | 208 | U|UE2c | aucune |
| C038 | `35051000ZT0144` | 14 Route de Chantepie 35510 Cesson-Sévigné | 2024-04-29 | 28 | non mesurée — hors courbe | E | 43,1 % | 70.8 | 1931 | 1 490 | U|UE3 | aucune |

La revue et les hypothèses mesurées sont dans [E9](../backlog/E9-test-terrain-deux-professionnels.md), qui départage cette promesse et celle de [E8](../backlog/E8-liste-exploratoire-terrain.md).

