# Baromètre du marché — département 35

**Généré le :** 2026-09-16 · **Mesures :** BAR-001 à BAR-009 de [`SPEC.md`](../../SPEC.md) §13.4 · **Ticket :** [H1](../backlog/H1-barometre-marche-35-mesures.md)

**Recompté le 2026-09-16** par `recompte-preuve` — trois passes en isolement du code, dont une complète de 44 chiffres, aucune divergence de valeur.

Empreinte des mesures : `d08dba5d179c319e` — une attestation de recompte ne vaut que pour cette empreinte, consignée dans `barometre-marche-35/recompte.csv`.

Toutes les mesures sont agrégées. Aucune parcelle, aucune adresse, aucune mutation individuelle n'apparaît dans ce document ni dans les CSV qui l'accompagnent. Régénérer : `make market-barometer DEPARTMENT=35`.

## Ce qui a été lu, et dans quel état

| Source | Release | Cycle de vie | Acceptation |
|---|---|---|---|
| DS-01 | 2026-06-01 | validated | accepted |
| DS-02 | 2026-09-05 | discovered | accepted |
| DS-03 | 2026-02-a | validated | display_only |
| DS-06 | 2019-04-archive | discovered | pending |
| DS-06 | 2026-09-13 | discovered | display_only |
| DS-07 | 2026-09-14-extract | validated | display_only |

Dernière mutation connue : **2025-12-31**. Dernier dépôt de DPE de l'extrait : **2026-09-07**.

**La réforme DPE du 1er janvier 2026 ne touche aucune mesure de ce rapport.** L'extrait DPE va au-delà, mais DVF s'arrête au 31 décembre 2025 : aucune mesure croisant un diagnostic et une vente ne peut atteindre un DPE postérieur à la réforme. La rupture de série reste à traiter au prochain millésime DVF.

## Le filtre de chaque cohorte

| Cohorte | Filtre écrit | Effectif |
|---|---|---|
| Ventes exploitables | `mutation_nature = 'Vente'` · type Maison ou Appartement · `allocation_method = 'single_property_full_price'` · surface et prix > 0 · parcelle rattachée | 75 178 |
| — dont maisons | idem, `property_type = 'Maison'` | 58 233 |
| Ventes écartées par leur nature | `mutation_nature <> 'Vente'` — vente en l'état futur d'achèvement, terrain à bâtir, échange, adjudication, expropriation | 39 365 |
| DPE rattachés à une parcelle | relation bâtiment ↔ parcelle `certain` · DPE non annulé · commune lue sur la parcelle, jamais sur le diagnostic | 136 294 |
| — DPE rattachés à un bâtiment mais à aucune parcelle `certain` | hors de toute mesure de cohorte, motif : leur bâtiment ne porte aucune relation à une parcelle — aucune n'est `ambiguous`, elles sont toutes absentes | 334 |
| Premiers DPE par parcelle | le plus ancien dépôt de chaque parcelle, départagé par numéro de DPE | 46 695 |
| Cohorte 2024 | premier DPE déposé dans l'année, hors DPE d'appartement généré depuis un DPE d'immeuble | 9 653 |
| — exclusions DPE d'immeuble comptées | `numero_dpe_immeuble_associe` renseigné | 101 |
| Paires de ventes successives | deux ventes de maison **consécutives** de la même parcelle, rang n → n+1, à plus de 180 jours d'écart. Cent cinq couples (parcelle, date) portent plusieurs ventes le même jour : elles sont **départagées par prix croissant, puis par surface croissante**, faute de quoi « la vente suivante » n'est pas déterminée. Compter toutes les combinaisons de deux ventes en donnerait 10 100 | 7 024 |
| Parcelles portant au moins une mutation, toutes dates | `mutation_nature LIKE 'Vente%'` — vente, VEFA et terrain à bâtir compris — quel que soit le type de lot : une parcelle qui change de main a muté. La vente doit être **strictement postérieure** au dépôt. C'est l'événement de BAR-005, BAR-006 et BAR-007 | 326 498 |


## L'écart 14 532 / 9 754, tranché

`dpe-signal-vente-35.md` annonce une cohorte 2024 de **14 532 parcelles** sans écrire son filtre, et E8g n'a pas su la reconstituer. Le filtre écrit ci-dessus donne, pour la même année, **9 754 parcelles** avant l'exclusion des DPE d'immeuble et **9 653** après. Le 14 532 n'est donc pas reproductible et ne doit plus être cité : l'effectif de référence est celui de ce rapport, avec son filtre. Le **taux**, lui, se retrouve — 35,65 % annoncé alors, 35,5 % ici : c'est la mesure qui tenait, pas son effectif.

## Les supports, déclarés et contestables

| Mesure | Support minimal | Paramètre |
|---|---|---|
| BAR-001, BAR-002 | 15 ventes par cellule | `--sales-per-cell` |
| BAR-003, BAR-008 | 30 paires | `--repeat-pairs` |
| BAR-004 | 30 ventes par étiquette | `--label-sales` |
| Médiane de référence commune × année, utilisée par BAR-003 et BAR-004 | 15 ventes de maison | `--sales-per-cell` |
| BAR-005, BAR-006, BAR-007 | 200 parcelles de cohorte | `--dpe-cohort-parcels` |
| BAR-009 | aucun — les manques se comptent toujours | — |

Aucun de ces nombres n'est un seuil de sens métier. Sous le support, la valeur est **absente avec son motif** : elle n'est jamais repliée sur la valeur départementale.

## Le découpage par EPCI

18 EPCI, 332 communes rattachées. Le rattachement vient de l'attribut `code_epci_insee` des groupes de bâtiments de **DS-03 BDNB**, seule source du dépôt qui le porte ; il est utilisé comme clé géographique, jamais comme attribut classant. DS-03 ne porte pas le nom des EPCI : chaque EPCI est désigné par son SIREN, et ses communes sont listées dans `epci-communes.csv`. Nommer les EPCI demande un référentiel absent du dépôt — limite déclarée, à trancher par H2.

## BAR-001 et BAR-002 — volumes et prix au m²

### Maisons, département 35

| Année | Ventes | Q1 €/m² | Médiane €/m² | Q3 €/m² | Motif |
|---|---|---|---|---|---|
| 2014 | 3 682 | 1 435 | **1 875** | 2 424 |  |
| 2015 | 4 613 | 1 426 | **1 868** | 2 347 |  |
| 2016 | 4 878 | 1 417 | **1 868** | 2 396 |  |
| 2017 | 5 558 | 1 426 | **1 926** | 2 468 |  |
| 2018 | 5 483 | 1 463 | **1 970** | 2 557 |  |
| 2019 | 6 020 | 1 508 | **2 006** | 2 667 |  |
| 2020 | 6 131 | 1 568 | **2 107** | 2 794 |  |
| 2021 | 5 582 | 1 725 | **2 323** | 3 055 |  |
| 2022 | 4 801 | 1 989 | **2 615** | 3 373 |  |
| 2023 | 3 818 | 2 000 | **2 613** | 3 299 |  |
| 2024 | 3 570 | 1 948 | **2 535** | 3 187 |  |
| 2025 | 4 097 | 2 031 | **2 588** | 3 227 |  |


### Appartements, département 35

| Année | Ventes | Q1 €/m² | Médiane €/m² | Q3 €/m² | Motif |
|---|---|---|---|---|---|
| 2014 | 1 395 | 1 552 | **2 105** | 2 853 |  |
| 2015 | 1 557 | 1 580 | **2 226** | 2 871 |  |
| 2016 | 1 755 | 1 562 | **2 208** | 2 955 |  |
| 2017 | 2 024 | 1 702 | **2 344** | 3 038 |  |
| 2018 | 1 984 | 1 717 | **2 500** | 3 337 |  |
| 2019 | 2 108 | 1 844 | **2 674** | 3 558 |  |
| 2020 | 1 893 | 2 080 | **3 050** | 4 068 |  |
| 2021 | 1 278 | 2 345 | **3 418** | 4 680 |  |
| 2022 | 875 | 2 941 | **4 110** | 5 134 |  |
| 2023 | 705 | 2 703 | **3 848** | 5 071 |  |
| 2024 | 659 | 2 603 | **3 958** | 5 125 |  |
| 2025 | 712 | 2 728 | **3 998** | 5 129 |  |


Le détail par EPCI et par commune est dans `bar-001-002-volumes-prix.csv`, une ligne par cellule, effectif toujours présent. Dans cette mesure, une cellule sans vente est **absente**, jamais mise à zéro.

**La série mêle deux releases DVF** : les années 2014 à 2020 viennent de l'archive `DS-06@2019-04-archive`, les années 2021 à 2025 de `DS-06@2026-09-13`. Aucune césure n'apparaît dans les tableaux. `dvf-quality-35.md` établit que 2014 et 2015 sont les deux seuls millésimes dont l'incomplétude ne peut pas être corrigée, aucune publication ultérieure ne les portant : leurs volumes sont des planchers, pas des comptes.

## BAR-003 — plus-value nette de marché selon le prix d'entrée

Reventes de maison en 1 095 jours au plus, **surface inchangée**, ratio de prix divisé par l'évolution de la médiane de la commune entre les deux années. Le prix d'entrée est rapporté à la médiane de la commune l'année de l'achat, et les deux années doivent atteindre 15 ventes.

| De la paire à la mesure | Paires |
|---|---|
| paires successives | 7 024 |
| au-delà de la fenêtre | 4 604 |
| surface modifiée entre les deux ventes | 283 |
| sans médiane de référence des deux côtés | 632 |
| retenues | 1 505 |


| Prix d'entrée | Paires | Médiane | Q3 | Part > 1,20 | Motif |
|---|---|---|---|---|---|
| < 60 % de la médiane | 139 | **1,83** | 3,00 | 79,9 % |  |
| 60 % à 80 % | 204 | **1,23** | 1,44 | 54,4 % |  |
| 80 % à 100 % | 466 | **1,09** | 1,21 | 26,6 % |  |
| 100 % et plus | 696 | **1,01** | 1,11 | 11,9 % |  |

Réserves, inchangées depuis `pistes-analyse-marche-35.md` §5.2 : biais du survivant — seules les reventes sont vues ; retour à la moyenne ; une surface erronée à l'achat gonfle mécaniquement le ratio.

## BAR-004 — décote ou surcote par étiquette

Ventes de maison depuis 2022 portant un DPE de `type_batiment = 'maison'` déposé dans les 730 jours précédant l'acte — le dernier de la fenêtre. Prix au m² rapporté à la médiane commune × année, laquelle doit atteindre 15 ventes. Contrôle commune × année seulement : ni âge, ni surface, ni modèle hédonique.

| Étiquette | Ventes | Q1 | Médiane | Q3 | Motif |
|---|---|---|---|---|---|
| A | 251 | 0,97 | **1,05** | 1,15 |  |
| B | 387 | 0,95 | **1,06** | 1,18 |  |
| C | 2 462 | 0,91 | **1,01** | 1,13 |  |
| D | 2 203 | 0,88 | **1,00** | 1,14 |  |
| E | 1 037 | 0,82 | **0,97** | 1,14 |  |
| F | 524 | 0,81 | **0,97** | 1,13 |  |
| G | 233 | 0,82 | **0,99** | 1,14 |  |

Les sept étiquettes paraissent pour chaque périmètre, **y compris à effectif nul** : qu'aucune vente de maison classée A n'ait été observée dans un EPCI est une information, alors qu'une cellule année × type sans aucune vente n'existe pas et reste absente de BAR-001/002. Les deux mesures ne traitent pas l'absence de la même façon, et c'est délibéré.

## BAR-005 — délai dépôt DPE → acte, cohorte 2024

| Périmètre | Parcelles de cohorte | Vendues sous 12 mois | Q1 j | Médiane j | Q3 j |
|---|---|---|---|---|---|
| Département 35 | 9 653 | 3 424 | 127 | **171** | 242 |

Par EPCI et par commune : `bar-005-delai-dpe-acte.csv`.

## BAR-006 — taux de mutation à douze mois après le premier DPE

| Cohorte | Parcelles | Vendues sous 12 mois | Taux | Motif |
|---|---|---|---|---|
| 2021 | 4 783 | 2 750 | **57,5 %** |  |
| 2022 | 10 546 | 5 243 | **49,7 %** |  |
| 2023 | 11 203 | 3 884 | **34,7 %** |  |
| 2024 | 9 653 | 3 424 | **35,5 %** |  |

**Ce que change la définition de la vente.** Le taux ci-dessus compte toute mutation de la parcelle. En exigeant que la mutation porte un lot Maison ou Appartement, la cohorte 2024 passe de 35,5 % à 34,7 %. L'écart est le fait des parcelles vendues comme terrain, dépendance ou local. Les deux lectures sont défendables ; c'est la première qui est publiée, et la seconde qui en donne la marge.

La cohorte la plus récente est la dernière dont les douze mois de suivi sont couverts par DVF — **2024**, dérivée de la dernière mutation connue, jamais choisie. La cohorte la plus ancienne est tronquée à gauche : l'extrait DPE commence le 2021-07-01, donc « premier DPE » y est moins sûr.

## BAR-007 — courbe de conversion, cohorte 2024

| Mois après dépôt | 1 | 2 | 3 | 6 | 9 | 12 |
|---|---|---|---|---|---|---|
| Cumul vendu | 0,2 % | 0,5 % | 1,8 % | 19,2 % | 29,3 % | 35,1 % |
| Parcelles | 9 653 | 9 653 | 9 653 | 9 653 | 9 653 | 9 653 |

Mois conventionnels de 30 jours, déclarés comme tels. La courbe porte sur 9 653 parcelles. Son douzième mois vaut 360 jours et non 365 : c'est pourquoi il tombe légèrement sous le taux de BAR-006, qui est la même mesure sur cinq jours de plus.

## BAR-008 — effet d'une extension de surface

Paires de ventes successives de maison, **surface bâtie strictement en hausse** entre les deux actes, écart de plus de 180 jours. Aucune médiane de référence n'intervient : les deux ratios sont bruts. La ligne « surface modifiée » de l'entonnoir BAR-003 compte toute surface différente, celle-ci seulement les hausses.

| Fenêtre | Paires | Ratio de prix médian | Ratio au m² médian | Motif |
|---|---|---|---|---|
| revente en 1095 jours au plus | 205 | 1,37 | **1,00** |  |
| toutes durées au-delà de 180 jours | 743 | 1,63 | **1,17** |  |


## BAR-009 — ce que le baromètre ne voit pas

| Mesure | Total | Manquants | Part |
|---|---|---|---|
| Mutations sans prix allouable — toutes natures, tous millésimes | 312 639 | 178 072 | 57,0 % |
| DPE non rattachés à un bâtiment — extrait entier | 208 086 | 71 458 | 34,3 % |

Commune par commune : `bar-009-couverture.csv`, 353 communes — contre 332 au référentiel cadastral. L'écart est le phénomène de communes fusionnées déjà mesuré dans `dvf-quality-35.md` : une commune que DVF ou l'ADEME connaît encore mais que le cadastre ne porte plus reste comptée ici, sans EPCI, plutôt que rattachée par défaut. Une part n'est jamais calculée sur un dénominateur nul : elle reste absente avec son motif.

## Ce que ce rapport n'établit pas

- Il ne publie aucune parcelle ni aucune adresse, et n'estime la valeur d'aucun bien non vendu.
- Il ne combine aucune mesure en score : l'étiquette et l'âge d'un DPE restent deux lectures indépendantes.
- Le rattachement d'un DPE à un bâtiment plafonne à ce que mesure BAR-009 ; les diagnostics rattachés à la seule adresse sont hors de toutes les mesures de cohorte.
- Le taux de conversion encaisse la dilution vente / location : le motif d'un diagnostic n'est pas publié par l'ADEME.
- **Le « 0,6 % » hérité ne se reproduit pas.** `SPEC.md` §7.3 et `pistes-analyse-marche-35.md` §1.4 justifient l'exclusion des DPE d'appartement générés depuis un DPE d'immeuble par un taux de conversion de 0,6 %, sans filtre écrit. Sous les filtres de ce rapport, ces premiers DPE des cohortes 2021 à 2024 sont 277, dont 1 a muté dans les douze mois, soit **0,4 %**. Même ordre de grandeur, pas le même chiffre, et le filtre d'origine reste inconnu. L'exclusion garde sa justification — ce taux est sans commune mesure avec celui de la cohorte — mais c'est ce chiffre-ci, avec son effectif et son filtre, qui doit être cité. La réécriture de `SPEC.md` est le ticket H6.
- Les CSV descendent à des effectifs communaux de quelques parcelles. Ce sont des comptes sans attribut, donc rien de nominatif, mais une commune où la cohorte compte une parcelle n'a plus grand-chose d'agrégé : ces lignes portent toutes « support insuffisant » et aucune valeur, et n'ont pas à être publiées telles quelles par H2.

Sources : DVF DGFiP / Etalab, DPE ADEME, cadastre Etalab, BDNB CSTB. Licence Ouverte 2.0.
