# Le dépôt d'un DPE comme signal de mise en vente — département 35

**Mesuré le :** 15 septembre 2026 · **Sources :** `DS-06` DVF 2021-2025, `DS-07` DPE
**Demandé par :** conversation du 15 septembre 2026 — « le marchand veut savoir qui va vendre »

Ce document mesure un signal, il n'en fait pas un produit. Ce qu'il autorise et ce qu'il interdit
sont écrits en fin de fichier.

## Pourquoi ce signal, et pourquoi il n'est pas une prédiction

Un DPE est **obligatoire pour mettre un logement en vente**. Son dépôt est un fait administratif
daté et public, pas un modèle : il s'explique parcelle par parcelle, ne s'apprend pas, et
n'invente aucun seuil. C'est ce qui le distingue d'une propension estimée.

## Le DPE précède l'acte de cinq à six mois

Délai entre dépôt du DPE et mutation, sur les parcelles du 35 portant les deux, mutations depuis
2022 — **21 718 ventes**.

| | Jours |
|---|---:|
| Q1 | 113 |
| **Médiane** | **169** |
| Q3 | 282 |
| Moyenne | 170 |

| Fenêtre | Ventes |
|---|---:|
| DPE dans les 3 mois précédant l'acte | 1 255 |
| DPE de 3 à 12 mois avant l'acte | 14 676 |
| DPE **postérieur** à la vente | 2 128 |

Une vente française sépare compromis et acte d'environ trois mois. Un DPE déposé à J correspond
donc à un compromis autour de J+80 et à un acte autour de J+169 : **le dépôt tombe au moment de la
mise en vente**, pas au moment de signer. L'objection « le DPE est fait parce que la vente se
réalise, donc trop tard » ne tient pas sur ces chiffres.

Les 2 128 DPE postérieurs à la vente sont attendus : nouveau propriétaire, ou rénovation.

## Ce que le signal vaut : un sur trois contre un sur trente-trois

Cohorte : parcelles du 35 dont le premier DPE a été déposé en 2024. Issue : au moins une mutation
dans les 365 jours suivant ce dépôt. Témoin : toutes les parcelles portant un bâtiment en relation
`certain`, sur une fenêtre de douze mois comparable.

| Groupe | Parcelles | Vendues dans les 12 mois | Taux |
|---|---:|---:|---:|
| **DPE déposé en 2024** | 14 532 | 5 180 | **35,65 %** |
| Toutes parcelles bâties | 494 676 | 14 999 | 3,03 % |

**Lift × 11,8.**

Le taux de base est corroboré indépendamment : sur la commune 35051, 1 390 parcelles sur 9 329
portent une mutation sur cinq millésimes, soit 14,9 % — environ 3 % par an.

## Quatre limites, dont deux sérieuses

**Le motif du diagnostic n'est pas publié.** `methode_application_dpe` décrit le périmètre de
calcul — maison, appartement, immeuble — jamais la raison. Un DPE de **location** est
indiscernable d'un DPE de vente. Cette dilution est déjà dans le 35,65 % : elle est encaissée par
la mesure, pas corrigée après coup.

**Notre DVF s'arrête au 31 décembre 2025.** Pour toute cohorte plus récente, l'absence de mutation
observée est un **défaut de données**, pas un fait de marché. La mesure ci-dessus porte donc sur
2024, dont les douze mois de suivi sont couverts. Elle ne dit rien de la conversion d'un DPE
déposé en 2026, et aucune mesure ne le pourra avant la publication du millésime.

**Le rattachement au bâtiment plafonne à 59 %.** Voir [`dpe-matching-35.md`](./dpe-matching-35.md).
Les diagnostics rattachés à la seule adresse sont hors de cette mesure.

**Un seul département, une seule cohorte annuelle.** Rien n'établit la stabilité du lift dans le
temps ni sa transposition au 22, 29 ou 56.

## Ce que ce résultat autorise, et ce qu'il n'autorise pas

**Autorisé sans amender la spécification** : présenter les parcelles à DPE récemment déposé comme
*probablement en vente ou en préparation de vente*, avec la date du dépôt comme preuve et le taux
observé comme mesure de fiabilité. C'est un fait administratif assorti de sa statistique, non une
prédiction — `SPEC.md` §2.2 n'interdit que la promesse d'une vente **certaine**.

**Non autorisé en l'état** : annoncer qu'un bien *va être vendu*, ou classer les propriétaires par
propension à vendre. Deux tiers des parcelles à DPE frais ne mutent pas dans l'année, et la part
imputable aux locations est inconnue.

**À ne pas confondre** avec la détection de divisibilité de
[`exploratory-candidates-35051.md`](./exploratory-candidates-35051.md) : celle-ci répond à « où
pourrait-on construire », celui-là à « qui est sur le marché ». Ce sont deux promesses distinctes,
et rien n'établit que le même professionnel veuille les deux.

Les prolongements envisagés de cette mesure — courbe de conversion, cohortes 2022 et 2023,
stratification par étiquette, ventes répétées — sont notés dans
[`pistes-analyse-marche-35.md`](./pistes-analyse-marche-35.md), sans être mesurés.
