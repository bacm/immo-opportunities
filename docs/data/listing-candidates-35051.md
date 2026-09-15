# Biens probablement en vente — commune 35051

**Généré le :** 2026-09-15 · **Ticket :** [E8f](../backlog/E8f-liste-biens-en-vente.md) · **Graine :** `20260915` · **Extrait DPE au :** 2026-09-07

Ce fichier est **régénéré** par `make listing-candidates`. Ne pas l'éditer à la main.

## Ce que cette liste dit, et ce qu'elle ne dit pas

Elle dit : **un DPE a été déposé à cette date**. C'est un fait administratif, daté et public, obligatoire pour mettre un logement en vente. Ce n'est pas un modèle : rien n'est appris, aucun seuil n'est inventé, et chaque ligne s'explique par sa date.

Elle **ne dit pas** que le bien sera vendu. Mesuré sur le 35 dans [`dpe-signal-vente-35.md`](./dpe-signal-vente-35.md) : **35,65 %** des parcelles dont le premier DPE a été déposé en 2024 ont muté dans les douze mois, contre **3,03 %** de l'ensemble des parcelles bâties — lift 11,8 fois. **Deux tiers ne mutent donc pas dans l'année.**

Le dépôt précède l'acte de **169 jours en médiane**, soit environ 80 jours avant le compromis : le signal arrive à la mise en vente, pas après.

## Quatre limites, dont deux sérieuses

**Le motif du diagnostic n'est pas publié.** `methode_application_dpe` donne le périmètre de calcul — maison, appartement, immeuble — jamais la raison. Un DPE de **location** est indiscernable d'un DPE de vente. Cette dilution est déjà dans le 35,65 %.

**DVF s'arrête au 31 décembre 2025.** Pour les dépôts récents, « aucune mutation depuis » est un défaut de données autant qu'un fait de marché. Le filtre l'applique là où la donnée existe, et ne peut rien affirmer au-delà.

**Le rattachement du DPE au bâtiment plafonne à 59 %** — voir [`dpe-matching-35.md`](./dpe-matching-35.md). Les diagnostics rattachés à la seule adresse sont absents de cette liste.

**Un seul département, une seule cohorte annuelle** fondent le lift.

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

## Candidats

L'origine — signal ou baseline — est dans `docs/data/listing-candidates/35051/correspondance.csv`, que le relecteur ne voit pas.

| Réf. | Parcelle | DPE déposé | Étiquette | Surface hab. | Année | Parcelle m² | Zone | Dernière mutation |
|---|---|---|---|---:|---:|---:|---|---|
| C001 | `35051000BH0260` | 2024-06-14 | C | 145.4 | 1995 | 608 | U|UE2c(d) | aucune |
| C002 | `35051000AZ0656` | 2024-07-17 | D | 26.3 | 2003 | 671 | U|UE2c(d) | aucune |
| C003 | `35051000AZ0490` | 2026-04-04 | B | 171.8 | 2002 | 613 | U|UE2c(d) | 2023-07-28 |
| C004 | `35051000ZS0045` | 2026-05-12 | F | 82.5 | 2004 | 535 | U|UE3 | aucune |
| C005 | `35051000AK0130` | 2024-08-30 | C | absente | 1979 | 608 | U|UE2c(d) | aucune |
| C006 | `35051000AZ0593` | 2026-03-26 | C | 133 | 2004 | 587 | U|UE2c(d) | aucune |
| C007 | `35051000AN0260` | 2026-08-19 | D | 80.1 | 1932 | 193 | U|UE2c(d) | aucune |
| C008 | `35051000AR0094` | 2026-07-17 | D | 13.4 | 1800 | 112 | U|UA1a | aucune |
| C009 | `35051000AP0158` | 2024-06-13 | D | 193 | 1971 | 1 417 | U|UE2c(d) | aucune |
| C010 | `35051000AZ0698` | 2024-05-06 | C | 188 | 2003 | 628 | U|UE2c(d) | aucune |
| C011 | `35051000AW0141` | 2026-08-28 | D | 153 | 1962 | 389 | U|UE1a | aucune |
| C012 | `35051000AB0054` | 2024-07-31 | D | 132 | 1974 | 639 | U|UE2c(d) | aucune |
| C013 | `35051000AK0102` | 2026-06-23 | D | 119.4 | 1980 | 715 | U|UE2c(d) | aucune |
| C014 | `35051000AH0126` | 2024-04-26 | D | 145 | 1978 | 477 | U|UE2c(d) | 2021-07-30 |
| C015 | `35051000AD0060` | 2026-04-09 | D | 102.5 | 1978 | 218 | U|UE2c | aucune |
| C016 | `35051000AN0182` | 2024-07-03 | C | 177.1 | 1983 | 904 | U|UE2c(d) | aucune |
| C017 | `35051000AN0364` | 2026-03-20 | D | 98.7 | 1974 | 173 | U|UE2c | aucune |
| C018 | `35051000AA0132` | 2024-06-02 | C | 152.2 | 1988 | 723 | U|UE2c(d) | aucune |
| C019 | `35051000AE0129` | 2024-05-28 | D | 80.5 | 1978 | 547 | U|UE2c(d) | aucune |
| C020 | `35051000YA0156` | 2024-08-20 | D | 130 | 1995 | 560 | U|UE2c(d) | aucune |
| C021 | `35051000AZ0561` | 2024-06-05 | C | 187.1 | 2003 | 679 | U|UE2c(d) | aucune |
| C022 | `35051000AB0186` | 2026-06-01 | C | 160.8 | 1973 | 531 | U|UE2c(d) | 2022-09-15 |
| C023 | `35051000AT0203` | 2026-04-22 | C | 95.1 | 1998 | 282 | U|UE2c | aucune |
| C024 | `35051000BD0140` | 2026-05-26 | D | 234.4 | 1992 | 557 | U|UE2c(d) | aucune |
| C025 | `35051000AB0229` | 2026-03-18 | F | 102.4 | 1975 | 601 | U|UE2c(d) | aucune |
| C026 | `35051000AS0017` | 2026-06-01 | E | 167.3 | 1970 | 691 | U|UE2c(d) | aucune |
| C027 | `35051000AK0249` | 2024-04-23 | D | 145 | 1955 | 472 | U|UE2c | aucune |
| C028 | `35051000AN0356` | 2024-08-27 | D | 83.9 | 1974 | 159 | U|UE2c | aucune |
| C029 | `35051000AB0203` | 2024-08-05 | E | 135.9 | 1973 | 357 | U|UE2c(d) | aucune |
| C030 | `35051000AE0155` | 2024-06-03 | E | 104.4 | 1977 | 292 | U|UE2c | aucune |
| C031 | `35051000AW0043` | 2026-05-21 | D | 96.4 | 1968 | 492 | U|UE2c(d) | 2025-07-21 |
| C032 | `35051000AW0123` | 2026-05-05 | E | 106.8 | 1958 | 365 | U|UE2c | aucune |
| C033 | `35051000AA0311` | 2026-03-27 | D | 112.1 | 1986 | 490 | U|UE2c(d) | aucune |
| C034 | `35051000AR0102` | 2024-06-24 | C | 67 | 1880 | 115 | U|UA1a | aucune |
| C035 | `35051000ZT0172` | 2024-08-18 | D | 162.8 | 1972 | 4 296 | U|UE3 | aucune |
| C036 | `35051000AK0196` | 2024-06-16 | E | 62.2 | 1955 | 278 | U|UE2c | aucune |
| C037 | `35051000AD0057` | 2026-04-30 | D | 95.8 | 1978 | 208 | U|UE2c | aucune |
| C038 | `35051000ZT0144` | 2024-04-29 | E | 70.8 | 1931 | 1 490 | U|UE3 | aucune |

La revue et les hypothèses mesurées sont dans [E9](../backlog/E9-test-terrain-deux-professionnels.md), qui départage cette promesse et celle de [E8](../backlog/E8-liste-exploratoire-terrain.md).

