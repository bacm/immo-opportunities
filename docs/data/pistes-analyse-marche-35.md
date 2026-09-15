# Pistes d'analyse du signal de vente et de la valeur pour le marchand — département 35

**Noté le :** 15 septembre 2026 · **Origine :** conversation du 15 septembre 2026, à la suite de
[`dpe-signal-vente-35.md`](./dpe-signal-vente-35.md) et de [D8](../backlog/D8-historique-dvf-2014.md)
**Statut :** notes, complétées le 15 septembre 2026 par des **sondages exploratoires** (section 5), non
recomptés. Aucune piste n'est décidée ni ouverte en ticket. Chacune dit
ce qu'elle mesurerait, sur quelle donnée, ce qu'elle servirait, et où elle se rattacherait.

Le sujet de fond tient en deux questions : *qui est sur le marché*, et *que vaut le bien pour un
marchand*. Les pistes sont classées par ce que les données déjà importées permettent, puis par ce
qui demanderait une source nouvelle.

## 1. Affiner le signal DPE avec ce qui est déjà en base

Toutes ces pistes se calculent sur `DS-06` et `DS-07` tels qu'importés. Ce sont des recomptages,
pas des modèles : aucune n'invente de seuil, chacune stratifie une mesure existante.

### 1.1 Courbe de conversion dans le temps, pas un taux à douze mois

Sur la cohorte 2024, mesurer la part vendue à 1, 3, 6, 9, 12 et 18 mois après le dépôt. Un DPE de
cinq mois sans mutation n'a plus la même probabilité résiduelle qu'un DPE de trois semaines.

- **Sert :** un rang à l'intérieur de la liste de [E8f](../backlog/E8f-liste-biens-en-vente.md),
  observé, sans seuil inventé. Aujourd'hui la cohorte « signal » est une fenêtre plate de six mois.
- **Coût :** faible, même requête que le lift, ventilée par délai.
- **Rattachement :** extension de `dpe-signal-vente-35.md`.

### 1.2 Stabilité inter-cohortes — mesurable dès maintenant

La limite 4 du rapport dit « une seule cohorte annuelle ». Or DVF couvre 2021 à 2025 : les
cohortes 2022 et 2023 ont chacune leurs douze mois de suivi. Trois lifts au lieu d'un.

- **Sert :** crédibilité du × 11,8, ou sa relativisation. C'est ce que [E9](../backlog/E9-test-terrain-deux-professionnels.md)
  devrait avoir en main avant de tester la promesse.
- **Coût :** faible.
- **Réserve :** la cohorte 2022 est tronquée à gauche — l'extrait DPE commence en juillet 2021,
  donc « premier DPE » y est moins sûr.

### 1.3 Stratifier par étiquette, surtout F et G

Depuis le 1er janvier 2025 un logement classé G ne peut plus être mis en location. Un DPE G frais
est donc rarement un DPE de location : cela lève **en partie** la dilution vente/location que le
rapport déclare irréductible. F et G sont aussi la cible de la stratégie rénovation-revente.

- **Sert :** un lift par étiquette, et une lecture différente des candidats F/G de la liste.
- **Coût :** faible.
- **Réserve :** l'interdiction G ne vaut que depuis 2025, la cohorte 2024 ne la porte pas encore.
  L'effet se lira sur les cohortes 2025 et suivantes, donc après le prochain millésime DVF.

### 1.4 Premier DPE, DPE de remplacement, DPE d'immeuble, maison ou appartement

Les champs `numero_dpe_remplace` et `numero_dpe_immeuble_associe` distinguent une réédition, un
diagnostic collectif et un premier diagnostic. Leur taux de conversion n'a aucune raison d'être le
même ; idem pour `type_batiment`.

- **Sert :** sortir proprement les DPE collectifs de la liste, et qualifier la réédition.
- **Coût :** faible.

### 1.5 Un confondant à mesurer : l'obsolescence réglementaire

Les DPE antérieurs à 2018 sont invalides depuis le 1er janvier 2023, ceux de 2018 à juin 2021
depuis le 1er janvier 2025. Cela produit des vagues de rééditions sans lien avec une vente,
attendues fin 2022 et fin 2024. La cohorte 2024 en porte probablement, ce qui **sous-estimerait**
le lift.

- **Sert :** un taux de conversion par mois de dépôt, qui fera apparaître les vagues.
- **Coût :** faible.
- **Rattachement :** à écrire comme cinquième limite de `dpe-signal-vente-35.md` si la vague est
  visible.

## 2. Ce que douze ans de DVF ouvrent pour le marchand

D8 a porté l'historique à 2014. Ces pistes n'existaient pas avec cinq ans.

### 2.1 Marge de revente observée — ventes répétées

Même parcelle vendue deux fois : écart de prix, délai entre les deux actes, présence d'un DPE ou
d'un changement de surface bâtie entre les deux.

- **Sert :** la question centrale du produit — la marge **réellement réalisée** localement en
  rénovation-revente — qui n'est aujourd'hui ni mesurée ni supposée. Le même calcul donne un indice
  de prix par ventes répétées, plus robuste que la tendance sur médianes annuelles prévue pour
  `MKT-105`.
- **Coût :** moyen. La pré-qualification des mutations complexes de D1 s'applique aux deux ventes.
- **Rattachement :** [E7](../backlog/E7-decision-valorisation.md) pour la valorisation,
  [E1](../backlog/E1-profiling-distributions.md) pour `MKT-105`.
- **Réserve :** l'identité de mutation d'Etalab n'est pas reproductible entre millésimes, voir
  `dvf-quality-35.md`. Le rapprochement se fait par parcelle et date, pas par `id_mutation`.

### 2.2 Décote énergétique observée

Sur les ventes portant à la fois un prix DVF et une étiquette DPE — 21 718 sur le 35 — comparer le
prix au m² des F/G à celui des C/D, à commune et période égales.

- **Sert :** l'arbitrage que le marchand exploite, mesuré plutôt que postulé. C'est aussi une
  pondération observée pour `REN-004` dans le moteur, à la place d'un poids déclaré.
- **Coût :** moyen — le support statistique par commune sera le facteur limitant, comme pour les
  comparables.
- **Rattachement :** E1, E7.

### 2.3 Durée de détention

L'absence de mutation depuis 2014 redevient une information, comme le ticket D8 l'annonçait : sur
cinq ans, 85,1 % des parcelles de 35051 n'avaient aucune mutation, ce qui ne discriminait rien.

- **Sert :** attribut de **contexte** de la fiche — dernière mutation connue, ou « aucune depuis
  2014 ».
- **Interdit :** en faire une propension du propriétaire à vendre. `SPEC.md` l'exclut, et
  `dpe-signal-vente-35.md` le rappelle.
- **Coût :** faible ; la colonne « Dernière mutation » de la liste E8f existe déjà, il s'agit de
  l'étendre à douze ans.

### 2.4 Délai de vente et température de marché par commune

Le délai dépôt DPE → acte est un proxy du délai de vente, donnée rare en open data. Par commune,
avec le taux de conversion à douze mois, cela donne une liquidité observée.

- **Sert :** une définition de `MKT-005` (`market_liquidity_proxy`) fondée sur un délai réel plutôt
  que sur un ratio volume/stock.
- **Coût :** faible sur la mesure, moyen sur son intégration au moteur.
- **Rattachement :** E1.
- **Réserve :** même dilution location/vente que le signal lui-même.

## 3. Sources absentes du contrat

### 3.1 Sitadel — autorisations d'urbanisme

Open data du SDES, avec identifiant de parcelle depuis 2017. Deux usages, qu'aucune source en
contrat ne couvre :

- **Vérité terrain ex post pour [E8](../backlog/E8-liste-exploratoire-terrain.md).** Les parcelles
  jugées divisibles ont-elles fait l'objet d'une déclaration préalable de division ou d'un permis
  après mutation ? C'est la seule mesure de précision de la liste « où pourrait-on construire »
  qui ne dépende pas d'un relecteur.
- **Contexte pour E8f.** Un permis en cours sur une parcelle à DPE frais signifie que le
  propriétaire rénove ou vend avec permis : le signal ne se lit plus de la même façon.

Demande un contrat `DS-10`, un audit de source comme `market-data-sources-audit.md`, et donc un
ticket. Pièges attendus : la parcelle de Sitadel est déclarative et peut porter un numéro périmé
après division ; la granularité communale des extractions anciennes.

### 3.2 Registre national des copropriétés

Open data de l'ANAH. Sert à identifier les immeubles en copropriété et à sortir proprement les DPE
collectifs, en complément de 1.4. Rendement modeste, à ne pas ouvrir avant que 1.4 ait montré que
le champ DPE ne suffit pas.

## 4. Ce qui n'est pas poursuivi, et pourquoi

| Piste | Motif |
|---|---|
| Déclarations d'intention d'aliéner | pas en open data ; quelques communes les publient en délibération, sans structure |
| Annonces immobilières | scraping, hors périmètre par `SPEC.md` |
| Fichiers fonciers, MAJIC, LOVAC | données propriétaires sans droit, hors périmètre |
| Indicateurs communaux INSEE (résidences secondaires, évolution de population) | trop grossiers pour classer des parcelles ; utilisables au mieux comme contexte de commune |

## Ordre suggéré

1. **1.1, 1.2, 1.3** — trois recomptages à faible coût, qui renforcent directement ce que E9 va
   tester. À faire avant E9 si le calendrier le permet.
2. **2.1 et 2.2** — les deux chiffres qui parlent au marchand, calculables sans nouvelle source.
3. **3.1** — un contrat à ouvrir, donc un ticket à part, après le verdict de E9 sur la promesse E8.

## 5. Sondages du 15 septembre 2026 — ce que les données disent déjà

Sondages en lecture sur la base locale, SQL dans [`pistes-analyse-marche-35/`](./pistes-analyse-marche-35/).
**Non recomptés** : aucun de ces chiffres ne sort de ce fichier sans passer par `recompte-preuve`.
Méthode commune au signal DPE : parcelle ↔ bâtiment en relation `certain`, premier DPE par
parcelle, issue = au moins une vente DVF dans les 365 jours suivant le dépôt.

### 5.1 Le signal DPE — pistes 1.1 à 1.5

**Stabilité inter-cohortes (1.2).** Le taux à douze mois est stable entre 2023 et 2024, et
nettement plus haut avant.

| Cohorte du premier DPE | Parcelles | Taux 12 mois |
|---|---:|---:|
| 2022 | 10 557 | 49,66 % |
| 2023 | 11 368 | 34,17 % |
| 2024 | 9 754 | 35,11 % |

Le mois par mois descend de 55 % en janvier 2022 à 31–37 % de 2023 à 2024, pendant que les dépôts
mensuels triplent, de 1 600 à 4 000. Aucun pic de dépôts fin 2022 ni fin 2024 : la vague
d'obsolescence réglementaire (1.5) n'est pas visible. La baisse ressemble à un effet de cycle et de
dilution, pas à un artefact. **Le taux à présenter est celui de la dernière cohorte, et il est
corroboré par la précédente.**

**Écart de comptage à instruire.** La cohorte 2024 compte ici 9 754 parcelles contre 14 532 dans
`dpe-signal-vente-35.md`, pour un taux quasi identique. Sans le filtre `certain` on trouve
15 568. Le rapport ne dit pas quel filtre il a appliqué : c'est une entrée pour `recompte-preuve`.

**Courbe de conversion (1.1).** Elle est en S, et c'est ce qui rend l'âge du DPE informatif.

| Mois après dépôt | 1 | 2 | 3 | 6 | 9 | 12 | 18 | 24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cohorte 2023, cumul vendu | 0,4 % | 1,0 % | 3,0 % | 19,7 % | 28,8 % | 33,9 % | 39,9 % | 43,2 % |
| Cohorte 2024, cumul vendu | 0,2 % | 0,5 % | 1,8 % | 19,0 % | 29,0 % | 34,8 % | — | — |

Presque rien avant trois mois, la moitié des conversions entre trois et six mois. Un DPE de six
mois encore invendu conserve environ 19 % de chance de vente sur les six mois suivants ; à douze
mois, environ 9 %. La fenêtre « moins de six mois » de E8f est donc bien placée, et **l'âge du
dépôt peut porter un rang observé** à l'intérieur de la liste.

**Étiquette (1.3).** Courbe en U : les extrêmes convertissent le plus.

| Étiquette | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| Parcelles 2023–2024 | 619 | 1 109 | 7 296 | 7 040 | 3 093 | 1 280 | 685 |
| Taux 12 mois | 45,4 % | 38,1 % | 31,5 % | 31,6 % | 39,3 % | 44,4 % | 44,4 % |

F et G convertissent 40 % de plus que C et D, avant même l'interdiction de louer les G. A et B
sont le neuf. Pour un marchand en rénovation-revente, **un DPE F ou G frais est le meilleur
candidat de la liste**, et c'est mesuré.

**Type et remplacement (1.4).** Maison, premier DPE : 39,6 % ; maison, DPE de remplacement :
36,5 % — le remplacement ne change rien. Appartement : 21,3 %. Appartement généré depuis un DPE
d'immeuble : **0,6 %** — à exclure de toute mesure départementale, la liste E8f les exclut déjà par
sa population.

**Par commune (2.4).** Sur les dix communes les plus fournies, cohortes 2023–2024, maisons : taux
de 29,5 % à 51,9 %, délai médian dépôt → acte de 150 à 198 jours. Cesson-Sévigné (35051) : 33,2 %
sur 271 parcelles, 191 jours. La variation est réelle ; le support n'existe qu'au-delà de deux
cents parcelles, donc une dizaine de communes.

### 5.2 Ce que douze ans de DVF disent — pistes 2.1 et 2.2

Ventes simples de maisons à prix alloué, 2014–2025 : 58 233. Paires de ventes successives sur la
même parcelle à plus de six mois d'écart : **7 024**.

**Plus-value brute (2.1).** Ratio prix de revente / prix d'achat, médiane 1,29 sur un délai
médian de 3,9 ans, soit 6,2 % par an annualisé — c'est surtout le marché. Revente en moins d'un
an : médiane 1,11, quartiles 1,00 et 1,28.

**Plus-value nette de marché.** Ratio divisé par l'évolution de la médiane commune × année, à
surface inchangée, communes à quinze ventes par an au moins :

| Délai entre les deux ventes | Paires | Q1 | Médiane | Q3 |
|---|---:|---:|---:|---:|
| 6 mois à 1 an | 234 | 1,00 | 1,09 | 1,28 |
| 1 à 2 ans | 562 | 0,98 | 1,07 | 1,25 |
| 2 à 3 ans | 709 | 0,96 | 1,06 | 1,22 |

**Selon le prix d'entrée**, revente en moins de trois ans, prix d'achat au m² rapporté à la
médiane de la commune l'année de l'achat :

| Prix d'entrée | Paires | Plus-value nette médiane | Q3 | Part au-delà de +20 % |
|---|---:|---:|---:|---:|
| sous 60 % de la médiane | 142 | **1,90** | 3,15 | 80,3 % |
| 60 à 80 % | 203 | 1,23 | 1,45 | 54,2 % |
| 80 à 100 % | 466 | 1,09 | 1,21 | 26,6 % |
| 100 % et plus | 694 | 1,01 | 1,11 | 12,0 % |

C'est le métier du marchand de biens, lisible dans DVF : **la marge est dans le prix d'entrée**,
et elle est très concentrée. Réserves : biais du survivant (seules les reventes sont vues) ;
retour à la moyenne ; une surface ou un prix erroné à l'achat gonfle mécaniquement le ratio. Le
support local est mince : 51 communes ont dix paires de revente rapide, 7 en ont trente.

**Extension.** Reventes en moins de trois ans avec surface bâtie augmentée : 205 paires, ratio
médian 1,37 mais **ratio au m² 1,00** — les m² ajoutés se vendent au prix des m² existants, ni
plus ni moins. Utile au scénario division/extension, à confirmer sur un effectif plus large.

**Décote énergétique (2.2).** Ventes de maisons 2022–2025 avec un DPE déposé dans les 24 mois
précédant l'acte, prix au m² rapporté à la médiane commune × année :

| Étiquette | Ventes | Q1 | Médiane | Q3 |
|---|---:|---:|---:|---:|
| A | 190 | 0,97 | 1,04 | 1,14 |
| B | 323 | 0,94 | 1,06 | 1,19 |
| C | 2 129 | 0,91 | 1,01 | 1,13 |
| D | 1 938 | 0,88 | 1,00 | 1,14 |
| E | 898 | 0,82 | 0,97 | 1,13 |
| F | 458 | 0,81 | 0,97 | 1,12 |
| G | 202 | 0,83 | 1,00 | 1,14 |

**La décote passoire est faible sur les maisons du 35** : 3 à 4 % en médiane pour E et F, rien
de visible pour G sur 202 ventes, et l'écart interquartile, ± 13 %, dépasse largement l'effet de
l'étiquette. Contrôle limité à commune × année, sans âge ni surface : un modèle hédonique
pourrait en trouver davantage, mais l'ordre de grandeur est là. L'arbitrage « acheter une passoire
décotée » que suppose la stratégie rénovation-revente n'est pas soutenu par l'étiquette seule.
Rapproché du tableau précédent : la marge existe, mais **ce n'est pas l'étiquette qui désigne le
bien décoté**.

### 5.3 Ce que cela change pour l'échantillon présenté aux marchands

- **À intégrer à la liste E8f, faible coût, sans nouvelle source :** l'âge du DPE avec sa chance
  résiduelle observée ; l'étiquette lue comme signal de conversion, F/G en tête ; le taux de la
  commune plutôt que celui du département quand le support existe. Trois colonnes, aucune
  n'invente de seuil.
- **À présenter comme contexte, pas comme colonne :** la plus-value nette selon le prix
  d'entrée, et la faible décote énergétique. Ce sont des faits de marché qui cadrent la
  conversation sur la stratégie — la question que E9 pose en dernier — et qui testent si le
  marchand reconnaît son métier dans les chiffres.
- **À ne pas faire avant E9 :** Sitadel, un modèle hédonique, une mesure par EPCI. Leur intérêt
  dépend de la promesse que E9 retiendra.

