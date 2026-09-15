# Audit critique complet — Immo Opportunities

**Date :** 15 septembre 2026 · **Périmètre :** l'intégralité du dépôt (code, données, infrastructure,
process, documentation) et le besoin produit lui-même · **Méthode :** lecture du dépôt, mesures sur
la base locale en fonctionnement, recherche externe sur le marché et le droit d'accès aux données.

Ce document ne modifie rien. Il critique. Il distingue à chaque fois ce qui est **mesuré** (commande
exécutée sur ce poste, chiffre reproductible), ce qui est **lu** (chemin de fichier cité) et ce qui
est **estimé** (grille tarifaire, extrapolation). Il se termine par une remise à plat du produit, avec
sept variantes de définition et une recommandation.

---

## 0. Le verdict en une page

**Le logiciel est bien écrit. Le produit n'existe pas encore, et rien dans le dépôt n'établit que
quelqu'un en veut.**

Onze jours, 128 commits, ~44 000 lignes de code, ~18 800 lignes de documentation, 82 tables, 45
routes d'API, 16 conteneurs, 71 tickets dont 43 clos. Et :

| Ce qui compte | État mesuré |
|---|---|
| Professionnels ayant vu une liste | **0** — `docs/data/field-test-results-35.md` n'existe pas |
| Entretiens client, lettres d'intention, prospects nommés | **0** dans tout le dépôt |
| Scores publiés (`OpportunitySnapshot`) | **0** — et le moteur n'a **aucun appelant** hors tests |
| Sources métier acceptées (DS-06 à DS-09) | **0** — toutes en `display_only` |
| Déploiements hors de ce Mac | **0** — le rendu Compose de production échoue faute d'images |
| Tests touchant PostgreSQL | **0** sur 522 tests Python, qui s'exécutent en 1,3 s |
| Routes d'API exigeant une authentification | **4 sur 45** |
| Analyse juridique RGPD, exigée par `SPEC.md` §18.3 | **aucune** |
| Analyse concurrentielle | **aucune** — pas un seul concurrent nommé dans `SPEC.md` |

Le projet possède pourtant trois actifs réels et rares :

1. **Un référentiel spatial du 35 honnêtement mesuré** : 1,33 M de parcelles, 515 k bâtiments
   physiques, quatre sources métier importées, chaque taux d'erreur publié plutôt qu'enterré.
2. **Un résultat positif fort** : le dépôt d'un DPE prédit une mutation dans les 12 mois à 35 %
   contre 3 % de base, lift × 11,8, stable sur deux cohortes, courbe de conversion en S mesurée.
3. **Un résultat de marché exploitable** : sur 7 024 paires de reventes, la marge d'un marchand est
   dans le prix d'entrée (médiane × 1,90 sous 60 % du prix de marché) et non dans l'étiquette
   énergétique (décote passoire de 3 à 4 %).

Le problème n'est pas la rigueur, qui est au-dessus de la moyenne du secteur. C'est qu'elle a été
appliquée à la mesure de la donnée et jamais à la mesure du besoin, et que l'architecture a été
construite pour une échelle et une multi-tenance dont personne n'a démontré la nécessité.

**La recommandation tient en trois lignes** (détail §14 et §15) :

- Geler tout développement de plateforme. Ne pas toucher au front, à l'infra, à Dagster, au scoring.
- Passer trois semaines à parler à des professionnels avec les deux listes déjà produites, en
  corrigeant d'abord le protocole E9 dont l'aveugle est cassé.
- Décider ensuite entre trois définitions de produit réellement défendables avec des données
  ouvertes (§14, variantes V1, V3, V5), et abandonner explicitement la promesse « off-market pour
  particuliers », que les données autorisées ne peuvent pas tenir.

---

## 1. Méthode et périmètre

**Mesuré sur ce poste** (Darwin arm64, Docker Desktop 10 vCPU / 11,7 Gio, pile en fonctionnement) :
volumes de code (`wc -l`), tests (`make check`), historique (`git log`), taille de la base et des
tables (`pg_database_size`, `pg_total_relation_size`), mémoire des conteneurs (`docker stats`),
tables vides (`pg_stat_user_tables`), routes authentifiées (`grep` sur les routeurs).

**Lu** : `SPEC.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `explo.md`, les 71 tickets de `docs/backlog/`,
les rapports de `docs/data/`, les contrats, les migrations, les scripts, les fichiers Compose,
Ansible et CI, le front. Sept lectures parallèles par domaine, recoupées entre elles ; chaque
affirmation reprise ici a été vérifiée sur au moins un chemin de fichier.

**Recherche externe** : concurrents français de la prospection foncière, conditions d'accès aux
Fichiers fonciers, LOVAC, MAJIC, DVF ; tailles de marché INSEE ; réglementation 2025-2026.

**Ce que l'audit ne fait pas** : il ne relance aucun import, ne recompte aucun rapport de
`docs/data/` depuis les sources (c'est le rôle de la compétence `recompte-preuve`), et ne vérifie pas
les prix d'hébergement en ligne.

---

## 2. Le besoin et le client

### 2.1 Ce que le projet déclare

`SPEC.md` §3.1 : « Marchand de biens ou investisseur-rénovateur indépendant opérant en Bretagne. »
§4.1 : le problème est la dispersion des données et la lenteur de leur lecture manuelle.
§20.1 : la métrique nord est « candidats qualifiés à approfondir par heure de travail utilisateur ».

### 2.2 Ce qui prouve que le besoin existe : rien

Recherche exhaustive sur `entretien`, `interview`, `lettre d'intention`, `étude de marché`, `persona`
dans tout le dépôt : les seules occurrences sont dans `SPEC.md` §5, comme **méthodes futures**.

- Aucun compte rendu d'entretien. `docs/data/field-test-35/gabarit-compte-rendu.md` est un
  formulaire vierge.
- Aucun professionnel recruté. `docs/backlog/E9-test-terrain-deux-professionnels.md` ligne 39 :
  « Le recrutement de deux à trois marchands de biens […] est la première tâche » — au futur, après
  128 commits.
- Les seules citations « métier » (« en dessous de 12 m ça devient compliqué », E8d ; « une maison
  des années 50 », E8e ; « j'ai trouvé un loup », E8i) sont attribuées à « arbitrage du 15
  septembre » ou « relecture du 15 septembre », c'est-à-dire **au porteur du projet**. Le produit a
  été réglé sur le jugement de son auteur, puis ce jugement a été présenté comme contrainte métier.

### 2.3 Les questions que la spec pose encore, onze jours plus tard

`SPEC.md` §25 liste huit questions ouvertes. Cinq portent sur le client et n'ont pas bougé :

1. Quel rayon d'activité et quel volume hebdomadaire cible le premier marchand de biens ?
2. Quelle stratégie est prioritaire entre division/extension et rénovation-revente ?
3. Quelles hypothèses financières par organisation ?
4. Quelle méthode terrain pour constituer le jeu de validation ?
5. Les candidats sont-ils partagés entre clients ou différenciés par territoire ?

La question 2 est la plus grave : **deux moteurs de score complets ont été écrits sans savoir
laquelle des deux stratégies intéresse un client.** Et la réponse commence à se dessiner dans les
propres données du projet (§6.4) : la rénovation-revente n'est ni outillée ni soutenue.

### 2.4 Ce que le métier fait réellement, et où le produit s'arrête

Un marchand de biens gagne sur le **prix d'entrée** (`docs/data/pistes-analyse-marche-35.md` §5.2 :
revente sous trois ans, plus-value nette médiane × 1,90 quand l'achat est sous 60 % du prix de
marché, × 1,01 quand il est au prix). Acheter sous le marché suppose une négociation directe avec
un vendeur, donc un **contact**. Le produit s'interdit le propriétaire (`SPEC.md` §6.3, §13.6),
n'automatise pas le contact (§18.2) et n'a aucune donnée de vacance. Il s'arrête donc exactement
là où le travail du marchand commence. Personne n'a écrit cette phrase dans le dépôt.

**Question jamais posée** : un professionnel paierait-il pour une liste de parcelles qu'il ne
peut transformer en contact qu'au prix d'un relevé de propriété à 12 € et plusieurs semaines par
bien ?

### 2.5 Taille du marché

`SPEC.md` ne donne aucun ordre de grandeur. Recherche externe (à confirmer) :

| Population | Ordre de grandeur | Source |
|---|---:|---|
| Marchands de biens France (secteur 681, 2021) | 29 656 entreprises, 8 096 ETP | INSEE, fiche secteur 681 |
| Sociétés 6810Z immatriculées, 4 départements bretons | ~1 650 (35 : 519 · 56 : 396 · 29 : 369 · 22 : 364), dont une fraction active | annuaires d'entreprises |
| Professionnels immobiliers Bretagne (annuaire portail) | ~3 200 | Logic-Immo |
| Transactions Bretagne historique (5 dép.) | point bas ~65 000/an fin 2024, > 70 000 mi-2025 | Notaires de l'Ouest |

Avec 79 €/mois (`SPEC.md` §22) et un taux de conversion optimiste de 5 % sur ~800 marchands actifs,
le plafond régional est de l'ordre de **40 abonnés et 3 000 € de MRR**. Ce chiffre n'apparaît
nulle part, et il conditionne tout : il ne rembourse ni une pile de 16 conteneurs ni un développeur.

---

## 3. La promesse et ce que les données permettent

### 3.1 La promesse écrite

`SPEC.md` §1 : « candidats off-market à approfondir ». §28 : off-market = « non identifié dans le
flux d'annonces observé ». §24 : « pas une intention de vente ». §23, risque « absence de signal
d'intention de vente », réponse : « promesse candidats, pas futures ventes ».

### 3.2 Les résultats négatifs établis, tous mesurés, tous défavorables à l'objet « bien »

| Résultat | Mesure | Source |
|---|---|---|
| Adresse ↔ parcelle non vérifiable | 24,4 % d'erreur, irréductible par containment, proximité ou distance | `docs/data/spatial-matching-manual-review-35.md` |
| Bâtiment ↔ parcelle | 37,5 % d'erreur sur 40 cas, toutes à confiance 0,9 pile (BUG-09) ; 400 706 relations sur 1,24 M à recouvrement < 10 %, déclarées certaines avant correction | idem, l. 336-346, 414-416 |
| Unité foncière dégénérée | 1 333 327 unités = une par parcelle, `publication_eligible: false`, motif `entity_resolution_incomplete` ; la contiguïté donne des grappes de 3 494 parcelles à Rennes | `docs/backlog/BUG-11-unite-fonciere-degeneree.md` |
| Usage du bâti | 10 candidats relus : 2 d'intérêt, 8 délaissés de voirie, industriels, espaces verts | `docs/backlog/E8b-usage-du-bati.md` |
| DPE rattaché au bâtiment | 59 % ; 10 % non rattachés ; la source se contredit sur 17 135 géocodages | `docs/data/dpe-matching-35.md` |
| DVF sans prix allouable | 65,5 % des mutations | `docs/data/dvf-quality-35.md` |
| Zone inondable typée | aucune source sur le 35, résultat négatif définitif | `docs/data/georisques-coverage-35.md` |
| Profils de règles d'urbanisme | `URB-005` vaut zéro partout ; D2b estimé à « quatre années-personne » à l'échelle nationale | `docs/data/gpu-coverage-35.md` |

**Verdict** : la promesse « candidat à approfondir » est tenable ; la promesse « bien » ne l'est pas.
Sans propriétaire, l'objet analysable est la parcelle cadastrale, objet fiscal et non objet de
marché. Le backlog l'a écrit lui-même (`docs/backlog/README.md`) : BUG-11 « est en réalité la
question de savoir si l'objet que le produit vend — un bien — est constructible avec les données
autorisées ». Il n'en a pas tiré la conséquence.

### 3.3 Le pivot non déclaré : la liste « biens probablement en vente »

`E8f` produit une seconde liste dont le signal est « un DPE a été déposé récemment ». Or un DPE est
obligatoire pour vendre : un bien à DPE frais est **en train d'entrer sur le marché**. C'est la
définition inverse de « off-market » (§28), et la contradiction frontale de §24. Le rapport
`docs/data/dpe-signal-vente-35.md` s'autorise lui-même : « Autorisé sans amender la spécification
[…] §2.2 n'interdit que la promesse d'une vente certaine ». `git log -- SPEC.md` ne renvoie que le
commit initial. **Le produit a changé de promesse en une journée, par argument sémantique, dans un
fichier de `docs/data/`, sans ADR.**

Ce pivot est pourtant le meilleur résultat du projet (§6.3). Il faut le nommer, l'assumer ou le
refuser, pas le glisser.

### 3.4 La précision de la liste n'a jamais été remesurée

Seule mesure existante : 2 candidats d'intérêt sur 10 (E8b), puis 4 sur 6 rejetés « maison trop
centrée » (E8c). Après E8c, E8d, E8e, E8h, E8i : **aucun nouveau taux**. Le rapport final
`docs/data/exploratory-candidates-35051.md` donne l'entonnoir (692 éligibles sur 9 329) et le
recouvrement des deux ordres (13 / 13 / 7), jamais une précision. Cinq itérations censées améliorer
un taux qui n'a pas été republié.

Et 692 candidats sur une commune de 17 000 habitants n'est pas un volume actionnable : à dix
minutes de qualification par parcelle, c'est 115 heures. Le produit ne réduit pas le travail, il le
déplace du sourcing vers le tri.

---

## 4. Marché, concurrence, prix

### 4.1 Dans le dépôt : rien

`grep -i "kelfoncier|urbanease|pricehubble|geofoncier|meilleurs agents"` → zéro occurrence.
`SPEC.md` §22 et §23 ne citent aucun concurrent. Le seul texte est `explo.md` l. 903-915 : « Tout
le monde peut récupérer [les données]. Le vrai avantage sera : le moteur de scoring, les données
annotées, le dataset IA, les retours utilisateurs. » Les quatre sont à zéro.

### 4.2 Ce qui existe déjà (recherche externe, prix publics seulement)

| Outil | Cible | Propriétaire nommé | Parcelles divisibles | Intention de vente | Prix |
|---|---|---|---|---|---|
| Kel Foncier | promoteurs, aménageurs, **marchands de biens**, CMI | oui (bases publiques + privées + terrain) | **oui**, page dédiée MDB | — | sur devis |
| Urbanease (PriceHubble) | agents, promoteurs, investisseurs | oui, « 36 M de données propriétaires » | partiel | **oui**, « intentions de vente », « propriétaires en difficulté » | sur devis |
| Telescop | agents, promoteurs, off-market industrialisé | oui, 8 M avec nom, 5,7 M avec téléphone | — | pige | sur devis, par département |
| Immonator | marchands de biens | non | **oui**, simulation de division | — | non publié |
| Géofoncier (Ordre des géomètres) | géomètres, notaires, immobilier | personnes morales | filtre surface/zonage | — | 21 à 87 €/mois |
| Prospect+ | mandataires, agences | personnes morales | non | — | 25 à 30 €/mois |
| Immo Data | agents, investisseurs | non | non | — | 39 à 89 €/mois |

**Trois leçons** :

1. Les deux choses que le projet n'a pas — propriétaire et intention de vente — sont le cœur de
   l'offre des leaders. Ils les obtiennent par croisement d'annuaires et observation terrain, avec
   une exposition RGPD qu'ils assument. On ne les rattrape pas à l'open data.
2. La détection de parcelles divisibles est **déjà commercialisée** (Kel Foncier, Immonator). Le
   différenciateur possible n'est pas la fonction, c'est la **qualité morphologique** (RNB, bâtiments
   physiques, cercle inscriptible, motifs de manquant tracés) que personne ne publie.
3. Les prix publiés du segment sont bas (25 à 90 €/mois). Le 79 €/mois de `SPEC.md` §22 est dans la
   fourchette, mais pour un outil national. Un outil régional sans propriétaire se vendra en dessous.

### 4.3 Modèle économique : trois nombres hérités d'un brainstorm

`SPEC.md` §22 : 79 / 249 € / sur devis, repris de `explo.md` l. 861-889, jamais recalculés. Aucune
cible de chiffre d'affaires, aucun nombre de clients nécessaires, aucun coût d'exploitation chiffré
(alors qu'il est calculable, §10), aucun coût d'acquisition, aucun canal de vente.

**Le problème de rétention n'est posé nulle part.** Une fois qu'un marchand a épuisé les 692
parcelles éligibles de son territoire, que reste-t-il à payer le mois suivant ? Le stock se
renouvelle au rythme des mutations, environ 3 % par an. Un outil « stock » se vend une fois ; seul
un outil « flux » (nouvelles mises en vente, nouveaux permis) justifie un abonnement. La liste E8f
est un flux ; la liste E8 est un stock.

---

## 5. Juridique

### 5.1 Ce qui est bien tenu : les licences

`docs/data/DS-01-acceptance.md` : Licence Ouverte 2.0, attribution retenue. `docs/data/spatial-sources-audit.md`
l. 166-169 et 303 : tables propriétaire de BDNB **écartées explicitement** (« c'est de la donnée
de propriétaire »). `SPEC.md` §13.6 interdit âge, nom, coordonnées du propriétaire et toute donnée
scrapée. C'est exemplaire.

### 5.2 Ce qui manque : l'analyse RGPD que la spec exige

`SPEC.md` §18.3 l. 1309 : « Une revue spécialisée RGPD, prospection et droit immobilier est requise
avant un pilote. » Recherche `rgpd|cnil|dpo|données personnelles` dans `docs/` : **aucun document,
aucun ticket sur 71.**

Trois angles morts concrets :

- **DVF rapproché d'une parcelle et d'une adresse.** Le cadre légal de DVF (loi 2018-727, décret
  2018-1350, art. L112 A LPF) pose une finalité de transparence des marchés et une **interdiction de
  réidentification** ayant pour objet ou pour effet de remonter au vendeur ou à l'acheteur. Une fiche
  produit qui affiche les mutations d'une parcelle identifiée, avec son adresse, permet d'inférer le
  prix payé par une personne physique identifiable. Le dépôt n'en dit pas un mot.
- **La liste E8f.** `docs/data/biens-en-vente-35051.md` publie 38 adresses postales complètes avec
  surface habitable, année, étiquette DPE et **une probabilité de vente chiffrée** (« 31,7 % »).
  `SPEC.md` §18.3 interdit toute étiquette « propriétaire vendeur ». La liste s'intitule « biens
  probablement en vente ». La différence est mince et n'a fait l'objet d'aucune revue. C'est une
  inférence sur le comportement d'un occupant identifiable par son adresse.
- **API ADEME.** 231 416 diagnostics aspirés par pagination ; les conditions d'usage (volumétrie,
  redistribution des adresses déclarées) ne sont pas analysées, contrairement à `SPEC.md` §13.11.

Contexte 2026 à intégrer : le démarchage téléphonique B2C sans consentement est interdit depuis le 11
août 2026 ; un outil qui produit des cibles particuliers pousse vers le courrier. La réforme DPE du
1er janvier 2026 (coefficient électricité 2,3 → 1,9) sort ~850 000 logements du statut de passoire
sans travaux : toute lecture « à rénover » fondée sur une étiquette antérieure est fausse pour
l'électrique.

**Le paradoxe** : un projet qui a produit 14 800 lignes de documentation, un ADR sur sa propre
boucle de développement et un recompte adversarial de chaque chiffre publié n'a pas une page sur le
risque juridique de son cœur de métier.

---

## 6. Les données : l'actif principal, et ce qu'il dit

### 6.1 Ce qui existe en base (mesuré)

| | Valeur |
|---|---|
| Base `immo` | **29 Go** logiques, 32,8 Go sur volume ; MinIO 6,0 Go |
| Tables utilisateur | 85, dont **30 vides** — toutes dans `app.*`, `scoring.*`, `market.*` : le produit |
| `feature.feature_value` | 8,5 Go, 19,9 M lignes |
| `meta.*` (résolution d'entités) | ~11 Go, 40 % de la base, pour porter des relations dont un tiers est faux |
| `reference.cadastral_parcel` | 1 334 373 |
| `reference.physical_building` | 1 032 474 enregistrements pour 514 859 bâtiments physiques RNB |
| `observation.transaction` | 284 699 mutations, 668 315 lots, 12 millésimes |
| `observation.energy_assessment` | 207 944 |
| `observation.urban_zone` / `urban_constraint` | 20 260 / 424 022 |

La base a **doublé en huit jours** (14 Go le 7 septembre, `docs/operations/postgresql-tuning.md` ;
29 Go le 15) sur un seul département, par le seul ajout de DS-06 à DS-09, et rien ne purge (BUG-08,
à faire).

### 6.2 Ce qui n'est accepté par personne

Aucune source métier n'est `accepted`. DS-06, DS-07, DS-08, DS-09 sont en `display_only`
(`docs/data/market-data-quality-35.md`), comme DS-03, DS-04 et DS-05. Une feature dont la source
n'est pas acceptée sort `source_not_accepted`. Les deux définitions de score sont `draft`,
`publication_eligible: false`, `parameter_status: profiling_required`. La chaîne unité foncière →
features → score → opportunité est cassée à chaque maillon, et le dépôt le sait.

### 6.3 Le seul résultat positif fort : le signal DPE

`docs/data/dpe-signal-vente-35.md` et `pistes-analyse-marche-35.md` §5.1 :

| Mesure | Valeur |
|---|---|
| Délai dépôt DPE → acte, médiane | 169 jours (≈ 80 jours avant compromis : le DPE tombe à la mise en vente) |
| Taux de mutation à 12 mois, cohorte 2024 | 35,1 à 35,7 % selon filtre |
| Taux de base, toutes parcelles bâties | 3,03 % |
| Lift | **× 11,8** |
| Stabilité inter-cohortes | 2023 : 34,2 % · 2024 : 35,1 % (2022 : 49,7 %, cycle haut) |
| Courbe de conversion | en S : 2 % à 3 mois, 20 % à 6 mois, 35 % à 12 mois |
| Par étiquette | courbe en U : F et G convertissent 40 % de plus que C et D |
| Appartement issu d'un DPE d'immeuble | 0,6 % — à exclure |

Limites réelles : motif du DPE non publié (location indiscernable de vente), DVF arrêté au
31/12/2025, rattachement à 59 %, un seul département. Et un **écart de comptage non expliqué**
(14 532 parcelles dans le rapport, 9 754 à 17 640 selon le filtre à la reproduction) qui doit
passer par `recompte-preuve` avant tout usage.

**Ce que ce signal est** : un fait administratif daté, explicable parcelle par parcelle, sans modèle
ni seuil. C'est exactement ce qu'Urbanease et les outils « IA de prospection » vendent comme
« intention de vente » à partir de 200 signaux opaques. Le projet en a un, transparent et mesuré.

### 6.4 Le résultat de marché qui tranche entre les deux stratégies

`pistes-analyse-marche-35.md` §5.2, sur 7 024 paires de reventes 2014-2025 :

| Prix d'entrée rapporté au marché | Paires | Plus-value nette médiane | Part > +20 % |
|---|---:|---:|---:|
| sous 60 % | 142 | **× 1,90** | 80 % |
| 60 à 80 % | 203 | × 1,23 | 54 % |
| 80 à 100 % | 466 | × 1,09 | 27 % |
| 100 % et plus | 694 | × 1,01 | 12 % |

Et la décote énergétique des maisons du 35 : 3 à 4 % pour E et F, invisible pour G sur 202 ventes,
avec un écart interquartile de ± 13 % qui noie l'effet. **L'arbitrage « acheter une passoire
décotée » que suppose la stratégie rénovation-revente n'est pas soutenu par les données du
projet.** Ajouté au fait que les familles REN et BLD ne sont pas matérialisées et que le DPE n'est
rattaché qu'à 59 %, la stratégie rénovation-revente est à la fois non outillée et non fondée.
Aucun ticket n'en tire la conséquence.

### 6.5 Ce que les données ne verront jamais

Deux motifs de rejet relevés en relecture n'ont aucune source dans le dépôt : « c'est déjà
goudronné » (OCS GE, non importé) et « il y a une piscine » (constructions surfaciques BD TOPO,
non importées). Le cas `35051000ZS0176` (rayon inscriptible 11,5 m, rejeté pour « maison trop grande
et en plein milieu ») est consigné sans qu'aucune source ne porte ce jugement. Ces limites sont
déclarées honnêtement ; elles signifient qu'une liste morphologique plafonnera toujours à une
précision que seule la photo aérienne ou la visite lève.

---

## 7. Le code — backend

**5 188 lignes en 28 fichiers, sans ORM, SQL brut via `text()`, pyright strict, zéro `TODO`, zéro
injection SQL trouvée, zéro dépendance obsolète.** La qualité d'écriture est bonne. Le problème est
ailleurs.

### 7.1 La chaîne de publication est structurellement inatteignable

1. `scoring.score_definition` n'a **aucun INSERT** dans tout le dépôt (seul `scoring.strategy` est
   semée). La fonction SQL `scoring.publish_score_definition()` n'est appelée nulle part.
2. Donc `scoring.active_score_definition` est vide, donc `scoring.publish_opportunity_snapshot()`
   lève `NO_DATA_FOUND`.
3. `backend/src/immo/brittany_pilot.py:85-94` exige `active_scores == 2` et une segmentation
   `active` ; la segmentation est semée `draft` et aucun `UPDATE` ne l'active.
4. Par cascade, `meta.active_regional_release` est vide et **12 routes sur 43** retournent
   systématiquement vide ou 404.

Le produit n'a pas « pas encore publié de score » : **il ne le peut pas, faute de code
d'amorçage.** Et côté pipelines, `persist_score_snapshot` et `publish_snapshot`
(`pipelines/src/immo_pipelines/scoring/persistence.py`) n'ont **aucun appelant**, ni script, ni
asset, ni test. 927 lignes de moteur, testées par 300 lignes de tests unitaires excellents, jamais
exécutées sur une parcelle réelle par un chemin de production. Vérifié.

### 7.2 Sécurité : quatre défauts qui se cumulent

| # | Défaut | Preuve |
|---|---|---|
| 1 | **41 routes sur 45 sont anonymes**, dont une écriture : `POST /api/v1/review/verdicts` accepte un `reviewer` arbitraire et écrit en append-only dans le jeu d'annotation qui mesure la qualité d'appariement. Fiches, recherche, mutations DVF par parcelle, DPE par parcelle, scores, version PostgreSQL et SHA de commit : tout est servi sans jeton derrière un Caddy public. | `backend/src/immo/main.py` (aucune dépendance globale), `grep current_principal` : 4 routes dans `connected_mvp.py` et `brittany_pilot.py` seulement ; `config/caddy/Caddyfile:28-30` |
| 2 | **L'API tourne avec le rôle propriétaire de la base.** `database_user = "immo"`, jamais surchargé ; `config/postgres/init/10-init-databases.sh:50` fait `GRANT migration_owner, api_rw, pipeline_rw TO immo`. Aucun `SET LOCAL ROLE api_rw` dans `backend/src` (les pipelines le font 21 fois). La matrice de privilèges de la migration 0001 est décorative. | `backend/src/immo/config.py:25`, `compose.yaml:241-242` |
| 3 | **La RLS est désarmable par le processus qu'elle protège.** `FORCE ROW LEVEL SECURITY` est bien posé, le contexte est bien positionné depuis le JWT ; mais le rôle `immo` étant membre de `migration_owner`, le processus API peut `DISABLE ROW LEVEL SECURITY`. Elle ne protège que contre une erreur de filtrage dans le code applicatif. | migrations 0013, 0014 ; `backend/scripts/provision_member.py:29` le fait déjà |
| 4 | **Aucun rate limiting, aucun `statement_timeout`, aucune limite de corps.** `GET /api/v1/property-units` (anonyme) accepte une bbox de 1° × 1° et exécute un `ST_Intersects` + `LATERAL ST_UnaryUnion` par parcelle sur un pool de 5 connexions. Déni de service trivial. | `backend/src/immo/api/routes/explorer.py:68-69`, `explorer.py:246-263`, `config.py:27` |

Les tuiles `/tiles/v1/opportunities/*` sont dans le même cas : proxy direct vers Martin sans auth,
et la fonction expose `score`, `confidence_level`, `property_unit_id`. Dès la première publication,
l'actif différenciant sera extractible en masse, anonymement, à partir du zoom 10.

### 7.3 Tests : 522 tests en 1,3 seconde, zéro base

`make check` est vert en 9 secondes. 119 tests backend en 0,26 s, 334 tests pipelines en 0,92 s,
69 tests scripts en 0,08 s. **Aucun ne touche PostgreSQL.** Pas de fixture base, pas de
`testcontainers`, pas de service postgres en CI. Les 5 925 lignes de SQL des migrations, les 12
politiques RLS, les 6 fonctions PL/pgSQL, les ~150 requêtes `text()` et les 2 969 lignes de
`spatial/importer.py` ne sont jamais exécutées par la CI.

Ce qui les remplace : **12 fichiers sur 29 dans `backend/tests` grep le code source**.
`test_connected_mvp_migration_contract.py:36` : `assert "FORCE ROW LEVEL SECURITY" in source`.
`test_optional_sql_parameters.py:11` l'assume : « faute de banc PostgreSQL dans `make check` ».
Le contexte est aggravant : ce fichier documente que BUG-07 avait rendu la recherche d'adresse
inutilisable en production sur un `AmbiguousParameter`, et la réponse a été une regex sur le
source. BUG-09 (400 706 relations fausses) vient d'une ligne de `spatial/importer.py` qu'aucun
test n'exécute ; il a été trouvé par un relecteur humain au 47ᵉ cas d'une revue qui ne le cherchait
pas. `pytest-cov` est installé et jamais lancé.

### 7.4 Ce qui est mort ou spéculatif

- **13 tables sur 82** sans écrivain : `market.market_area`, `market_metric`,
  `comparable_selection` (lue, jamais écrite), `meta.territory_coverage_snapshot`,
  `scoring.backtest_run`, `backtest_metric`, `ablation_result`, `score_definition` + 3 filles.
- **12 routes sur 43** appelées par aucun code front, dont tout `market_data.py` (341 lignes).
- `geoalchemy2` en dépendance directe, jamais importée.
- `backend/scripts/provision_member.py` : code mort qui fait exactement ce que la docstring de
  `accounts.py` qualifie de « façon simple et fausse » (`SET LOCAL ROLE migration_owner`), avec des
  identifiants incompatibles (`user:{subject}` contre `user:{uuid4()}`).
- Un seul logger dans tout le backend, une seule ligne d'accès ; `api/errors.py` fait `del exc`
  sans journaliser ; ~25 `except SQLAlchemyError → 503` transforment toute erreur de programmation
  en « service indisponible », mécanisme exact qui a masqué BUG-07.

### 7.5 Sur-ingénierie caractérisée

Versionnement de définitions de score en base (6 tables, une fonction PL/pgSQL à 4 gardes) pour
zéro définition ; infrastructure de backtest et d'ablation sans point de sortie ; pilote régional
(3 fonctions PL/pgSQL, un bundle transactionnel, une vue de readiness) derrière deux gardes
définitivement insatisfaisables ; protocole de revue en double aveugle avec bras `top_score` /
`baseline` / `random`, splits `development` / `validation` / `final`, pseudonymes de relecteurs, sur
un produit sans un seul candidat ; hiérarchie de rôles à quatre niveaux et multi-tenant RLS pour un
pilote sans utilisateur.

---

## 8. Le code — pipelines

### 8.1 Dagster orchestre un asset

`pipelines/src/immo_pipelines/definitions.py` fait six lignes et enregistre deux assets : un
diagnostic qui logge la version de Python, et `cadastre_department_release` (DS-01). **194 lignes
décorées sur 19 492, 1 %.** Les 25 cibles d'import du Makefile utilisent le conteneur `dagster-code`
comme interpréteur Python (`run --rm dagster-code python pipelines/scripts/…`). Le daemon, le
webserver et la base Dagster tournent pour rien ; le webserver n'a même pas de route Caddy en
production. BUG-02 le dit, chiffre 36 exécutions manuelles à quatre départements, et reste à faire,
ordonnancé après E3 — lui-même bloqué par l'absence de scoring. **Dépendance circulaire non notée.**

### 8.2 Reproductibilité : bon socle, une exception majeure

`cadastre/manifest.py` (283 l.) est le seul module commun sérieux : refus avant téléchargement d'un
asset sans SHA-256 ou sans marqueur daté, résolution archive base → archive manifeste → amont,
origine tracée. Huit imports sur neuf portent une version de transformation dans leur clé
d'idempotence.

Deux trous :

- **DS-01, le seul asset Dagster, est le seul import sans version de transformation** dans sa clé
  (`assets/cadastre.py:127`). C'est le défaut BUG-09, corrigé partout ailleurs, laissé sur le
  référentiel le plus structurant.
- **DS-08 (GPU) est intégralement hors régime** : 184 assets avec `sha256: null` et sans archive ;
  `import_gpu_release.py` n'importe ni `resolve_asset` ni `require_reproducible`, streame les ZIP
  distants, ne hache que le manifeste. 21 136 zones d'urbanisme en base sans octet vérifiable, et un
  lot arrêté à 152 documents sur 184 que rien ne signale. Le script a été écrit pour contourner la
  garde plutôt que la satisfaire, pour une raison assumée (« archiver coûterait 430 Go »), mais la
  conséquence n'est écrite nulle part.

### 8.3 Le runbook de reconstitution est faux

`docs/operations/referentiel-local-35.md` (daté du 4 septembre) affirme que « DS-03, DS-06 à DS-09
n'ont aucune release réelle ». Faux depuis le 14 septembre. Treize commandes manuelles couvrent
quatre datasets sur neuf, aucune étape de features ni de scoring, aucune durée totale. **La séquence
censée rétablir l'état sur lequel les rapports ont été mesurés ne le rétablit pas.**

### 8.4 Contrats : 12 sur 14 sont déclaratifs

`contracts/features/market-data-v1.json` (27 features, avec `valid_range`, `out_of_range`,
`requirement`, `missing_value`), `morphology-v1.json` et `feature-registry-v1.json` ne sont ouverts
par aucun code ; leur logique est réimplémentée à la main dans `market_data/features.py` (855 l.).
Six contrats dataset sont lus uniquement pour être hachés ; DS-06 et DS-08 ont leur empreinte en
dur. Aucun schéma ne valide les contrats eux-mêmes. Rien ne détecterait une divergence.

### 8.5 Seuils en dur, dans le périmètre censé l'interdire

`scoring/engine.py:458-465` : `< 40 low`, `< 60 review`, `< 80 interesting`, sinon
`high_priority` ; bornes de confiance 80/60 et 0,8/0,6. `contracts/scoring/README.md` promet
« aucun seuil territorial arbitraire dans ces contrats » — exact, ils sont dans le moteur. Hors
périmètre : `2 <= floor_height <= 5`, `max_distance_m = 10_000`, `max_age_months = 60`,
`ambiguity_ratio_tolerance = 0.05` (qui produit les 2 114 `ambiguous_match` publiés sans que le
paramètre soit cité). La règle `seuil-invente` de `check-diff-invariants` ne regarde que
`pipelines/src/immo_pipelines/scoring/` et n'attrape qu'un identifiant nommé `threshold|seuil|…`.

### 8.6 Duplication

25 blocs `psycopg.connect(…)` identiques ; 6 copies de `contract_fingerprint()` ; 4
réimplémentations du cycle `import_run` qui **divergent déjà** (DVF purge les versions antérieures,
DPE purge toute la release, GPU ne purge rien) ; 5 recalculs manuels de SHA-256 dans les scripts
`pin_*`. La partie difficile (checksum, archive) est factorisée ; la partie répétitive ne l'est pas.

### 8.7 Ce qui ne passera pas à quatre départements

Import GPU effondré à 2 documents / 20 minutes par limitation du producteur ; premier appel de liste
API à 1 839 ms sur un département (NFR 500 ms) ; argiles 823 Mo en couche nationale non découpable ;
1 340 appels communaux Géorisques ; 34 Go d'archives GPU pour le seul 35 ; tables de rendu
reconstruites intégralement à chaque publication ; profiling non transposable (G1 exige une revue
stratifiée par département). `map/martin/` et `map/sql/` documentent un contenu qui n'existe pas.

---

## 9. Le code — frontend

**2 176 lignes écrites à la main** (dont 1 243 dans `App.tsx`), 6 dépendances runtime, MapLibre
seul, pas de lib d'état. Contrainte respectée. Mais :

### 9.1 Les écrans qui portent la promesse sont vides

`docs/data/captures/01-explorer-initial.png` : « 0 candidat », « Aucun candidat publié », carte
grise. Liste de candidats, fiche candidat, workspace (11 statuts, 9 motifs de rejet, notes,
historique), scénarios financiers, recherches sauvegardées (écriture seule, jamais relues) : ~700 des
1 243 lignes d'`App.tsx` sont inatteignables. Ce qui fonctionne est l'outillage interne (fiches
parcelle, DVF, DPE, revue B4, admin).

### 9.2 Le chemin critique produit contourne entièrement le front

E9, la seule validation utilisateur planifiée, passe par `pipelines/scripts/field_test_kit.py`
(254 lignes de Python → HTML imprimable + CSV), pas par l'Explorer. Le ticket E8h l'écrit : « ni
passer par l'Explorer ». Le front React, son OIDC, sa carte, ses 31 `useState` et ses 18 tests
Playwright ne participent pas à la seule confrontation utilisateur prévue. **Tout investissement
supplémentaire dans le front avant E9 est spéculatif.**

### 9.3 Bugs trouvés à la lecture

- **La carte s'ouvre au large de l'Afrique.** `App.tsx:81-84` : `Number(params.get(key))` vaut `0`
  quand le paramètre est absent, et `Number.isFinite(0)` est vrai ; le `fallback` (Rennes) n'est
  jamais atteint. Visible sur la capture 01 (bouton « − » désactivé). Premier écran de tout nouvel
  utilisateur.
- **Changer de département donne une carte vide** : zoom 9-10 alors que `parcels` démarre à 13 et
  `buildings` à 15. Aucun message, indiscernable d'un territoire non couvert.
- **L'inconnu est peint comme un zéro sur la carte.** `RealMap.tsx:125` :
  `['coalesce', ['get', 'score'], 0]`. Violation frontale de FR-007 et de la règle maison, dans le
  dépôt qui l'automatise (`check-diff-invariants` ne connaît pas la forme tableau MapLibre).
- **Deux blocs de vérification transforment une panne en « aucune donnée »** : `App.tsx:683` et
  `:791` appellent `fetch()` brut sans `Authorization`, puis `response.ok ? json : []` et
  `.catch(() => setRows([]))`. Un 401, un 500 ou une coupure s'affichent « Aucune mutation rattachée
  à cette parcelle ».
- **L'authentification déconnectera en boucle** : `automaticSilentRenew` et `monitorSession` sans
  `silent_redirect_uri`, alors que Caddy pose `X-Frame-Options: DENY` ; les iframes de
  renouvellement sont bloquées → `signinRedirect()` à chaque expiration d'access token, avec perte de
  toute saisie. Refresh token `offline_access` en `sessionStorage` sans CSP. `initializeAuth` peut
  bloquer à jamais sur « Connexion sécurisée… ». Un clic sur son nom déconnecte sans confirmation.
- Typographie à 8 et 9 px sur les filtres et l'admin ; modales sans piège de focus ni Échap ;
  combobox ARIA sur le patron abandonné ; entre 761 et 980 px l'interface est coupée sans barre de
  défilement ; sous 760 px la carte disparaît. Énumérations brutes en anglais (« high »,
  « ambiguous_position », « source_relation ») dans une interface française.
- Lignes JSX de 2 114, 1 867, 1 260 et 1 010 caractères : non diffables, non revuables.
- Captures de « preuve » C3 : `03` et `04` ont le même MD5, `05` et `06` aussi. Quatre preuves
  annoncées, deux images.

### 9.4 Tests : la CI ne teste pas le front, et le front testé n'est pas le front servi

Zéro test unitaire. 18 tests Playwright, dont 2 sautés (échantillon B4 entièrement jugé), 6 qui
échouent sur base vide (identifiants réels en dur, comptes DVF/DPE en dur : un nouveau millésime
les casse), 8 `waitForTimeout` dont quatre de 4 s. `make e2e` n'est pas dans `make check` ; la CI ne
lance que `tsc -b` et `vite build`. Playwright vise un serveur Vite où `auth.ts:3` désactive
l'OIDC, avec une réécriture de tuiles différente de celle de Caddy et sans le fallback SPA de nginx.
**Le flux d'authentification en production n'est couvert par rien, ni automatique ni manuel.**

---

## 10. Infrastructure et coûts

### 10.1 Ce qui tourne (mesuré)

20 services Compose, **16 conteneurs permanents**, identiques en dev et en prod (aucun profil).
RSS total au repos, département 35 seul : **4,4 Gio**, dont PostgreSQL 2,6 Gio, Keycloak 539 Mio,
Alloy 367 Mio, MinIO 247 Mio, Grafana 204 Mio, Loki 158 Mio, Prometheus 113 Mio, Dagster × 3
156 Mio, API 58 Mio, Martin 41 Mio, Caddy 22 Mio, web 8 Mio, Redis 4 Mio.

### 10.2 Dix conteneurs sur seize n'ont aucun usage démontré

| Service | Justification aujourd'hui | Preuve |
|---|---|---|
| Observabilité × 5 (prometheus, loki, grafana, alloy, node-exporter) | Prometheus ne scrute ni l'API, ni Martin, ni PostgreSQL, ni Dagster ; aucun Alertmanager, donc les 4 règles d'alerte ne sont routées nulle part ; le backend n'expose aucun `/metrics` | `config/prometheus/prometheus.yml:8-24` |
| Dagster × 3 | un asset réel ; webserver sans route Caddy ; daemon sans healthcheck ; `dagster-code` à 46 % CPU au repos | §8.1 |
| MinIO | 6 Go d'archives immuables ; le backend ne le référence pas ; la réplication hors site exige un second MinIO qui n'existe pas | `docs/backlog/A6:81` |
| Redis | **référencé par aucun code** ; prévu pour un Celery qui n'existe pas | vérifié par grep |
| Keycloak | realm avec 0 utilisateur, 0 rôle ; deux comptes de dev par script ; 539 Mio de RAM | `config/keycloak/realm-immo.json` |

Ils consomment 1,3 Gio de RAM, 11 des 19 chaînes d'approvisionnement à patcher, et sont la raison
pour laquelle la cible passe de 4 vCPU / 8 Go à 8 vCPU / 16 Go.

### 10.3 Le déploiement est structurellement impossible

Reproduit : le rendu Compose de production échoue sur `required variable API_IMAGE is missing`.
`compose.prod.yaml` exige `API_IMAGE`, `PIPELINES_IMAGE`, `WEB_IMAGE` ; `immo.env.j2` ne les définit
pas ; **aucun workflow ne construit ni ne pousse d'image** (`grep "docker push|ghcr.io|registry"` →
zéro). Aucune tâche ne fait arriver les 30 Go de données sur un VPS. `secrets/production.sops.yaml`
n'existe pas, donc `deploy-vps.yml` est rouge à chaque push depuis le 4 septembre (A6:86-87).
`docs/data/mvp-dod-traceability.md:36` : « syntaxe validée, exécution externe absente ».

Trois bugs de déploiement latents :

- **Choisir `staging` déploie en production** : `ENV=production` codé en dur dans les quatre appels
  make de `deploy-vps.yml:70,73,81,89`. Et tout merge sur `main` déclenche un déploiement production
  sans approbation.
- **Les secrets seront illisibles au premier démarrage réel** : installés `0400 root:root` par
  Ansible, bind-montés dans des conteneurs UID 10001. VirtioFS sur ce Mac remappe la propriété et
  masque le défaut ; Ubuntu ne le fera pas.
- `ACME_EMAIL` n'arrive jamais dans le conteneur Caddy : certificat Let's Encrypt sans contact.

### 10.4 Sauvegardes : le point le plus grave de l'infra

`scripts/backup-platform:39` : `pg_dump -d immo` seulement. Les bases `keycloak` et `dagster`
(comptes, mots de passe) **ne sont jamais sauvegardées**. Les dumps sont écrits sur la machine
sauvegardée (`/srv/immo/backups`) ; aucune copie hors site ; aucune rétention (« à définir avec
l'hébergeur ») ; à ~6 Go par nuit sur le disque de 80 Go recommandé, **plein en 5 à 7 nuits**.
Aucun archivage WAL malgré `ARCHITECTURE.md:859`. Restauration jamais exercée : RPO et RTO « non
mesurés » (`docs/operations/backup-restore.md:46-49`). G6 est à faire.

### 10.5 Dimensionnement incohérent

Limites déclarées dans `compose.prod.yaml` : 21,75 Go de mémoire et 13 vCPU pour une cible de 16 Go
et 8 vCPU ; neuf services longs sans limite. Un import qui dérape (+3,7 Go mesurés) déclenche l'OOM
killer sur un service arbitraire. PostgreSQL 15 (EOL novembre 2027) sur un projet démarré en 2026.
PostGIS forcé en `linux/amd64` sur un hôte arm64 : toutes les mesures de performance locales sont
prises sous émulation.

Extrapolation à quatre départements (clé foncière, ×4, la bonne : 74 % du volume est indexé sur la
parcelle) : **120 Go de base**, +28 Go par tour de millésimes sans purge, +22 Go MinIO → 150 à 200 Go
de données, sans place pour les sauvegardes. Besoin réel : 300 à 400 Go.

### 10.6 Coûts mensuels estimés

**Grilles Hetzner / OVH / Scaleway de mémoire à la mi-2026, hors taxes, ± 25 %, à revalider avant
tout engagement.**

| Scénario | Composition | Basse | Haute |
|---|---|---:|---:|
| A. Démo A6 (5 communes, sans Dagster/MinIO/observabilité) | CPX31 4/8/160 → OVH Comfort | 11 € | 20 € |
| B. MVP 35, pile actuelle (16 conteneurs, 31 Go) | CPX41 8/16/240 → CCX33 + volume | 30 € | 69 € |
| C. Pilote 4 départements, pile actuelle (120-150 Go) | CPX51 16/32/360 + volume → CCX43 | 74 € | 133 € |
| D. Séparation base/app, 35 | CCX23 + CPX31 + snapshots | 52 € | 62 € |
| F. Sauvegarde hors site (inexistante) | Storage Box 1 To → 5 To | 3 € | 11 € |
| G. Stockage objet MinIO auto-hébergé | part disque + **VPS de réplication obligatoire** | 14 € | 28 € |
| H. Stockage objet S3 compatible (22 Go) | OVH/Scaleway au Go → Hetzner forfait | 0,25 € | 6 € |
| L. PostgreSQL managé (référence, achète le contenu de G6) | 16 Go / 200 Go | 150 € | 250 € |

| Cible | Basse | Haute |
|---|---:|---:|
| Démo déployable (A + F + H) | **14 €** | **37 €** |
| MVP 35, pile actuelle (B + F + G + observabilité) | **49 €** | **113 €** |
| MVP 35, pile dégraissée (B + F + H, sans observabilité/Dagster/MinIO/Redis) | **25 €** | **45 €** |
| Pilote 4 départements, pile actuelle | **95 €** | **217 €** |
| Pilote 4 départements, dégraissé | **77 €** | **150 €** |

MinIO coûte 40 à 100 fois plus qu'un bucket S3 dès qu'on compte le VPS de réplication qu'il
impose, pour 6 Go d'archives immuables.

**Ce que le tableau ne dit pas** : la facture matérielle est négligeable. Le poste dominant est le
temps du développeur unique : 19 chaînes d'approvisionnement à suivre en CVE (Keycloak et Grafana
publient des avis quasi mensuels), 2 à 4 h/mois de patch minimal, 1 à 3 jours par majeure. Pour une
pile qui n'a jamais démarré hors de ce Mac.

### 10.7 Coût d'opportunité rapporté au marché

Au plafond régional estimé §2.5 (~3 000 € de MRR optimiste), même la pile complète à 113 €/mois
est rentable sur le papier. **Le coût qui tue n'est pas l'hébergement, c'est le temps** : chaque
semaine passée à maintenir 16 conteneurs est une semaine sans conversation client.

### 10.8 Boucle de développement locale

`compose.dev.yaml` ne monte aucun volume : toute ligne de Python impose `make rebuild`, qui
reconstruit l'image **et recrée PostgreSQL**. Ce cycle a déjà détruit deux lots d'import
(`Makefile:64-78`, garde-fou `check-no-batch` ajouté après incident). Coût mesuré : 84 Go de disque
Docker, 207 images, 87 % de couches mortes. Aucun serveur Vite dans la pile : itérer sur le front à
travers Caddy impose de reconstruire l'image nginx. Un Mac 16 Go et 100 Go de disque libre sont le
plancher.

---

## 11. Sécurité opérationnelle

Bien fait : secrets par fichier et SOPS/age déchiffrés en mémoire, réseaux `internal`,
`no-new-privileges`, UID non-root, UFW, fail2ban, SSH par clé, credentials CI éphémères, aucun
`:latest`, aucun secret dans git.

Défauts au-delà de §7.2 et §10.3 :

- API d'administration Caddy sur `0.0.0.0:2019`, joignable depuis six conteneurs : un conteneur
  compromis reconfigure le reverse proxy. Ouverte parce que Prometheus la scrute.
- `alloy` monte `/var/run/docker.sock` en root : équivalent root hôte. `node-exporter` monte `/` avec
  `pid: host`. Les deux plus gros privilèges de la pile portés par deux services sans usage.
- Images non épinglées par digest, contrairement à `ARCHITECTURE.md:851` ; bases de build en tags
  flottants (`python:3.13-slim`, `node:24-alpine`) : deux builds du même commit diffèrent. Aucun scan
  de vulnérabilité.
- `immo_admin_cidrs: ["0.0.0.0/0"]` dans l'inventaire d'exemple de production, présenté par
  `DEPLOYMENT.md:85` comme « le chemin le plus simple ».
- Aucune CSP, aucun HSTS ; polices Google chargées depuis un CDN tiers (`styles.css:1`).

---

## 12. Le process de développement

### 12.1 Chiffres (mesurés)

| | |
|---|---|
| Commits | 128 en 12 jours calendaires, 9 jours actifs ; 75 sur les 14 et 15 septembre (59 %) |
| Commits ne touchant que la documentation | **47 sur 128** (recompte robuste) |
| `docs/backlog/README.md` | modifié dans 59 commits sur 128 (46 %) |
| Documentation | 14 794 lignes dans `docs/` (144 fichiers) + 4 229 lignes de `.md` racine ≈ **18 800 lignes**, contre ~23 600 lignes de code produit hors scripts d'import jetables |
| Outillage de process (`scripts/`) | 887 lignes + 434 lignes de tests, mieux testé (1 test pour 2 lignes) que les pipelines (0 test d'intégration pour 2 969 lignes de SQL) |
| Messages de commit | ~23 lignes de prose par commit ; la même décision écrite dans le ticket, le corps de commit et `docs/data/` |
| Tickets | 71 : 43 terminés, 28 à faire, **0 en cours, 0 abandonné** — rien n'est jamais retiré |
| Tickets sans champ `Touche` | 52 sur 71 (73 %) : le mécanisme des lots parallèles est inopérant sur trois quarts du backlog, pour un projet à un seul auteur |
| Tickets sans champ `Nature` | 51 sur 71 : le verrou humain repose sur une déclaration que 7 tickets sur 10 ne font pas |
| ADR | 15 déclarées dans `ARCHITECTURE.md` §23, **1 fichier** dans `docs/decisions/` ; 15/15 « acceptée », 0 révisée ; la seule vraie ADR porte sur la boucle de développement elle-même |

### 12.2 La règle cardinale n'est pas appliquée

`CLAUDE.md` : « s'ouvre en ticket avant la première ligne modifiée ». Six des neuf tickets de la
série E8 (E8b, E8c, E8e, E8g, E8h, E8i) n'existent que dans **un seul commit**, qui contient
simultanément le fichier ticket avec `État : Terminé` déjà inscrit, le code et les tests. Neuf
tickets créés en 5 h 08. Délai médian ouverture → clôture des tickets de process A3/A4/A5/BUG-15/
BUG-16 : environ 10 minutes. Le ticket ne planifie rien ; c'est une seconde copie du message de
commit, produite pour satisfaire `make ticket-check`.

### 12.3 Les contrôles automatiques ne voient pas ce qu'ils prétendent voir

- `check-diff-invariants` l. 63, commentaire de l'auteur : « chaque motif a été calibré contre
  l'historique du dépôt : il ne signale rien sur les dix derniers commits ». Un détecteur ajusté à
  zéro détection sur ses propres données n'a aucune puissance démontrée.
- **Aucune des cinq règles ne détecterait BUG-09, BUG-10 ou BUG-12**, les trois défauts qui
  justifient leur existence. Tous trois ont été trouvés par un humain regardant des données réelles.
- La règle `seuil-invente` ne couvre pas `pipelines/scripts/exploratory_candidates.py`, où vivent
  tous les seuils des quinze derniers commits. Le fichier porte un `# invariant-ok:` contre un
  contrôle qui ne l'inspecte pas.
- `ticket-ok:` a été utilisé 8 fois sur 8 à contresens : sur des commits `docs/` seuls, que le script
  exempte déjà par construction. Moins d'une journée après avoir écrit la règle, l'auteur ne sait
  plus ce qu'elle vérifie.
- `make dod` et `make backlog-check` ne tournent jamais en CI.

### 12.4 Ce que le process a protégé, et ce qu'il coûte

Il a protégé : la discipline des résultats négatifs, les garde-fous de publication (1,33 M d'unités
en `publication_eligible: false` depuis le début, aucune donnée fausse publiée), le refus constant
d'inventer des seuils, la compétence `recompte-preuve` (46 lignes de prose, sans code, la seule
calibrée sur la bonne classe d'erreur), et le verrou humain déclaré.

Il coûte : un tiers des commits en documentation seule, 46 % des commits régénérant un tableau,
8 000 à 12 000 tokens de lecture obligatoire avant la première ligne d'un ticket de 100 lignes, ~60
prescriptions distinctes dans `CLAUDE.md` (un marqueur d'interdiction toutes les 10 lignes), et un
process qui génère ses propres tickets (A3 à A6, BUG-15, BUG-16), ses propres bugs (une regex
`[ab]?`, un identifiant en double) et sa propre ADR.

**Le process a cessé d'être un moyen de protéger le produit pour devenir le produit.** Le backlog
l'a diagnostiqué le 15 septembre (« il place la seule validation qui compte derrière onze
tickets ») sans en tirer la conclusion.

---

## 13. Cohérence documentaire

Trois documents de pilotage donnent trois états différents du projet le même jour :

| `CLAUDE.md` affirme | Réalité |
|---|---|
| « État au 13 septembre » | fichier modifié le 15 septembre à 07:47, 5 commits ce jour-là |
| « v0.4 Carte réelle — En cours, seule version active » | v0.4 clôturée le 14 septembre ; `docs/versions/README.md` dit v0.5 |
| « v0.1 Terminée le 15 septembre », « v0.3 Terminée le 13 » | une version terminée deux jours après celle qui en dépend |
| « v0.5 → v0.8 : En attente » | D1 à D8 et E8 à E8i (v0.6) tous terminés |
| « DS-06 à DS-09 : contrats seulement, aucun import réel » | les quatre sont importés et mesurés |
| « Le plus important maintenant : D1 » | D1 est terminé depuis le 14 septembre à 08:40 |
| « `ARCHITECTURE.md` (41 Ko) » | 47 Ko |

`docs/backlog/README.md` est daté du 4 septembre avec une section « révisé le 15 » et un verdict
d'état qui affirme encore que la revue B4 n'est pas faite. `docs/versions/README.md` se contredit
à 12 lignes d'écart sur le nombre de versions actives et déclare v0.6 « bloquée » avec 9 tickets
clos. `docs/data/mvp-dod-traceability.md`, source désignée pour « vérifier ce qui est prouvé »,
est daté du **10 août 2026, 25 jours avant le premier commit**, et contient deux fois les mêmes
tableaux. Trois documents attribuent trois contenus différents à `DS-10` (OCS GE dans `SPEC.md`,
population dans D7, Sitadel dans les pistes marché). `SPEC.md` n'a jamais été amendé en 128
commits alors qu'il est source de vérité n°1 et que la promesse a changé.

Pour un dépôt qui impose `make dod`, `make backlog-check` et un recompte adversarial de chaque
chiffre, c'est une faille de gouvernance : le seul document chargé systématiquement par chaque
agent l'oriente vers du travail déjà fait.

---

## 14. Remise à plat : ce que le produit pourrait être

Le périmètre initial (« candidats off-market pour marchands de biens, deux stratégies, quatre
départements ») cumule trois impossibilités : il vend un « bien » que les données ne construisent
pas, un « off-market » qui suppose le propriétaire, et une « rénovation-revente » que la décote
énergétique observée ne soutient pas. Il faut le redéfinir, pas l'affiner.

### 14.1 Grille d'évaluation

Six critères, notés de −− à ++ :

- **T** — tenable avec les données autorisées (open data, sans propriétaire particulier)
- **D** — différenciant face à Kel Foncier, Urbanease, Telescop, Géofoncier, Immo Data
- **M** — marché atteignable depuis la Bretagne (taille × prix × rétention)
- **J** — risque juridique (RGPD, DVF, ADEME)
- **R** — réutilise l'existant (référentiel 35, imports, mesures)
- **€** — délai avant un premier euro ou un premier verdict payant

### 14.2 Les variantes

#### V0 — Statu quo : plateforme SaaS multi-tenant, deux stratégies, quatre départements

Ce que le backlog prévoit après E9. Exige D6, E1 à E7, F1 à F3, G1 à G9, soit onze tickets dont
une extension XL, avant la première validation complète.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| − | − | − | − | ++ | −− |

Non tenable en l'état : l'objet « bien » n'existe pas (BUG-11 sans plan), la rénovation-revente est
infondée, la concurrence fait déjà la divisibilité avec le propriétaire en plus. À abandonner comme
définition, même si le code reste.

#### V1 — « Gisement foncier divisible » : un produit parcellaire assumé

Vendre exactement ce que les données construisent : un classement morphologique et réglementaire
de parcelles bâties à capacité résiduelle (cercle inscriptible, recul, largeur de façade, accès
voirie, zonage U hors ZAC, signature d'aménageur), enrichi de **Sitadel** (déclarations préalables
de division, permis d'aménager voisins : la seule vérité terrain ex post qui ne dépende pas d'un
relecteur) et de la contrainte ZAN qui rend le BIMBY structurellement porteur.

Cible : **aménageurs-lotisseurs, constructeurs de maisons individuelles, marchands de biens déjà
équipés d'un outil national** qui veulent une seconde lecture locale plus fine, géomètres-experts,
et EPCI (qui ont les Fichiers fonciers et deviennent le partenaire naturel pour le propriétaire).

Ce qui change : on cesse de parler de « bien » et de « off-market ». On dit « parcelle », on montre
la géométrie, on publie la précision mesurée, on laisse le client faire le relevé de propriété. La
liste E8 devient le produit, avec Sitadel comme colonne de vérité.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| ++ | + | − | ++ | ++ | + |

Réserve : marché de niche et produit « stock » (faible rétention). Le différenciateur est la qualité
morphologique et la traçabilité, que personne ne publie ; il faut le prouver contre Kel Foncier sur
une commune, en aveugle.

#### V2 — « Radar de mise en vente » : le signal DPE comme produit

Faire du lift × 11,8 le produit : une liste hebdomadaire des parcelles dont un DPE vient d'être
déposé, avec l'âge du dépôt, la chance résiduelle observée, l'étiquette, le taux communal, la
dernière mutation. Un flux, pas un stock, donc un abonnement défendable.

Cible : agents immobiliers (mandats), marchands de biens (arriver avant l'annonce), chasseurs.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| + | − | + | −− | ++ | ++ |

Deux problèmes lourds. **Juridique** : c'est une inférence sur le comportement d'un occupant à une
adresse identifiée, à la frontière de ce que `SPEC.md` §18.3 interdit et de ce que la CNIL admet
pour la prospection ; sans avis juridique, c'est indéfendable. **Concurrentiel** : Urbanease vend
déjà « intentions de vente » avec 36 M de données propriétaires ; le signal DPE seul est un
sous-ensemble transparent de leur offre. Et ce n'est plus « off-market » du tout. À ne poursuivre
que comme **pondération** dans V1 ou V5, ou après avis juridique explicite.

#### V3 — « Off-market personnes morales » : le seul off-market propre

Croiser **MAJIC personnes morales** (open data DGFiP depuis 2021 : dénomination et forme juridique
du propriétaire pour chaque parcelle détenue par une société, une SCI, une collectivité) avec
**BODACC** (procédures collectives) et **Sirene** (cessations), sur le référentiel spatial existant.
Résultat : des locaux et terrains détenus par des sociétés en difficulté ou en liquidation, avec un
propriétaire **nommé et légalement contactable** (B2B en opt-out).

Cible : marchands de biens, investisseurs, promoteurs.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| ++ | + | + | + | + | + |

C'est la seule variante qui tient la promesse « off-market avec propriétaire » sans Fichiers
fonciers. Prospect+ et Géofoncier exposent MAJIC PM mais aucun ne le croise avec BODACC ni avec une
morphologie. Réserve : volume réel inconnu sur le 35 (à sonder en une requête après import MAJIC PM,
un fichier annuel gratuit), et `SPEC.md` §13.6 devra être amendé pour autoriser explicitement le
propriétaire personne morale.

#### V4 — Collectivités et EPCI : vacance, BIMBY, lutte contre les friches

Retourner la relation : l'EPCI est **ayant droit** des Fichiers fonciers et de LOVAC. Le projet
devient prestataire d'un ayant droit (seule porte prévue par le Cerema pour un bureau d'études),
sur des missions PLH, OPAH, BIMBY, ZAN, biens sans maître, avec le référentiel et les mesures
existants.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| ++ | + | + | ++ | ++ | −− |

Cycle de vente public long (6 à 18 mois, marchés), usage borné aux politiques publiques (non
réutilisable pour un produit MDB), concurrence de Cartofriches et des agences d'urbanisme. Mais
c'est le seul chemin qui donne accès un jour au propriétaire particulier, et le seul où « module
vacance pour collectivités » (`SPEC.md` §3.2, §7.3) a un sens.

#### V5 — Intelligence de marché : vendre les mesures, pas la plateforme

Le dépôt a produit des chiffres que personne ne publie sur le 35 : marge de revente observée par
prix d'entrée, décote énergétique réelle, courbe de conversion DPE → vente par commune, délai de
vente par commune, effet de l'extension sur le prix au m², liquidité observée. Ce sont des faits de
marché que `pistes-analyse-marche-35.md` §5.3 propose déjà de « présenter comme contexte ».

Produit : un rapport de marché trimestriel par EPCI (PDF, tableau de bord léger), un baromètre
public gratuit pour l'acquisition, et des études sur mesure. Pas de SaaS, pas de multi-tenant, pas
de carte temps réel, pas d'OIDC.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| ++ | ++ | + | ++ | ++ | ++ |

Réserve : ce n'est plus un logiciel, c'est un produit éditorial ou de conseil ; la scalabilité est
celle d'une personne. Mais c'est ce qui monétise le plus vite l'actif réel du projet, et c'est ce
qui ouvre les portes des professionnels qu'il faut de toute façon rencontrer pour V1 ou V3.

#### V6 — Composant : vendre la couche morphologie et qualité à ceux qui ont déjà le client

Les outils nationaux ont le propriétaire mais pas la qualité géométrique ni la traçabilité des
manquants. Vendre une API ou un jeu de données (bâtiments physiques, cercle inscriptible, relations
bâtiment ↔ parcelle avec confiance mesurée, appariement DPE avec motifs) à Kel Foncier, Immonator,
Géofoncier, ou aux géomètres-experts.

| T | D | M | J | R | € |
|---|---|---|---|---|---|
| ++ | ++ | − | ++ | ++ | − |

Marché de quelques acheteurs, négociation longue, dépendance. Mais c'est la variante qui exige le
moins de code nouveau et qui valorise directement ce qui a coûté le plus cher.

#### V7 — Arrêt propre et capitalisation

Publier les importeurs (cadastre, RNB, BDNB, BD TOPO, BAN, DVF, DPE, GPU, Géorisques), les contrats,
les rapports de qualité et les résultats négatifs en open source. Documenter ce qui survit. G9
exige déjà « que le travail reste réutilisable » sans jamais en évaluer la part : elle est réelle
(les imports et les mesures) mais minoritaire (OIDC, RLS, multi-tenant, tuiles, Dagster, Ansible,
observabilité, 15 migrations sont spécifiques et non réutilisables).

### 14.3 Recommandation

**Abandonner V0 comme définition.** Retenir **V1 + V3 comme produit cible**, avec **V5 comme
premier revenu et premier contact**, et **V2 uniquement comme pondération** interne après avis
juridique.

Pourquoi cette combinaison :

- V1 et V3 sont les deux seules promesses tenables avec les données autorisées qui restent
  « off-market » au sens utile : une parcelle sous-exploitée dont personne n'a vu l'annonce, et un
  propriétaire personne morale contactable.
- V5 monétise immédiatement ce qui existe, sans code de plateforme, et fournit le prétexte des
  entretiens que le projet n'a jamais eus. Un baromètre gratuit par EPCI est aussi le meilleur canal
  d'acquisition pour un produit régional.
- V2 est le meilleur signal du projet, mais il ne peut être ni la promesse de tête ni une colonne
  publique tant que le RGPD n'a pas été instruit.
- V4 reste une option de long terme, à ouvrir seulement si un EPCI se présente.

**Ce que cela change dans le dépôt** : `SPEC.md` est réécrit (pas amendé) autour de « parcelle » et
« personne morale », la stratégie rénovation-revente est retirée du MVP, `DS-10` devient Sitadel,
`DS-11` MAJIC PM, `DS-12` BODACC, et `SPEC.md` §13.6 autorise explicitement le propriétaire personne
morale. Tout le reste du backlog (D6, E1 à E7, F1 à F3, G1 à G8) est suspendu, pas supprimé.

---

## 15. Plan proposé : trente jours, sans une ligne de plateforme

### Semaine 1 — Réparer le protocole, puis appeler

1. **Corriger E9** : retirer les colonnes « DPE déposé » et « Âge » de la liste E8f remise au
   relecteur (l'aveugle est cassé : les 20 « signal » portent des dates 2026, les 18 « baseline » des
   dates 2024 et « non mesurée »). Retirer la colonne « Surface » de la liste E8 ou changer la
   baseline. Fixer le prix de H5 avant la session.
2. **Republier la précision de la liste E8 après E8i** (dix candidats relus, taux), faute de quoi la
   session mesurera l'effet des huit limites déclarées et non celui du signal.
3. **Recruter cinq professionnels, pas deux** : deux marchands de biens, un lotisseur ou CMI, un
   géomètre-expert, un agent. Le prétexte : leur présenter les chiffres de marché du 35 (V5), qui
   les intéressent quoi qu'il arrive.
4. **Passer `recompte-preuve` sur `dpe-signal-vente-35.md`** : l'écart 14 532 / 9 754 doit être
   expliqué avant qu'un professionnel voie le × 11,8.

### Semaine 2 — Les sessions, et une requête

5. Cinq sessions selon le protocole E9 corrigé ; verbatims, verdicts, prix.
6. **Sonder V3 en une requête** : importer MAJIC PM 35 (un fichier annuel, Licence Ouverte),
   joindre sur `reference.cadastral_parcel`, croiser avec BODACC sur SIREN. Compter. Si le 35 donne
   moins de quelques centaines de cibles, V3 tombe.
7. **Sonder Sitadel** : combien de parcelles jugées divisibles par E8 ont porté une DP de division
   ou un PA depuis 2017 ? C'est la seule mesure de précision de V1 qui ne dépende pas d'un relecteur.

### Semaine 3 — Décider

8. Écrire la décision (G9 anticipé, sans attendre G8) : V1 + V3 + V5, ou recadrage, ou arrêt.
9. Obtenir un avis juridique écrit sur DVF rapproché d'une parcelle identifiée, sur l'inférence de
   mise en vente à une adresse, et sur MAJIC PM × BODACC. Une heure d'avocat spécialisé coûte moins
   qu'un ticket.
10. Réécrire `SPEC.md` (§1, §3, §6, §7, §13, §22, §24) et retirer `CLAUDE.md` de son état du 13
    septembre.

### Semaine 4 — Dégraisser, sécuriser le minimum, publier un premier chiffre

11. **Retirer de la pile** : Redis, Dagster webserver et daemon, la stack d'observabilité
    (conserver `docker logs`), MinIO au profit d'un bucket S3 compatible. Garder PostGIS, API, web,
    Caddy, Martin. Keycloak : à remplacer par un JWT signé par l'API dès que le multi-tenant n'est
    plus une exigence du MVP.
12. **Cinq corrections de sécurité avant tout déploiement**, chacune de quelques lignes :
    dépendance d'authentification globale sur l'API (`app.include_router(..., dependencies=[Depends(current_principal)])`
    sauf `/health`), rôle `api_rw` pour l'API, `statement_timeout`, bbox maximale réduite, verdicts
    de revue authentifiés.
13. **Un banc PostGIS en CI** (service `postgis` dans le workflow, une dizaine de tests
    d'intégration sur les migrations, la RLS et deux requêtes spatiales). Supprimer les tests qui
    grep le source à mesure qu'ils sont remplacés.
14. **Publier un baromètre gratuit du 35** (V5) : marge par prix d'entrée, décote énergétique,
    délai de vente par commune. Un PDF, une page. C'est le premier artefact public du projet.

### Ce qu'on ne fait pas pendant ces trente jours

Aucun ticket D6, E1 à E7, F1 à F3, G1 à G8, BUG-02, BUG-08, BUG-11, BUG-13, D7, A6, G6, G7. Aucune
ligne dans `App.tsx`. Aucun nouveau contrôle de process. Aucune ADR sur la méthode.

---

## 16. Les vingt-cinq constats, classés

| # | Constat | Gravité | Domaine |
|---|---|---|---|
| 1 | Aucune preuve que le client existe : zéro entretien, zéro professionnel recruté, cinq questions de `SPEC.md` §25 ouvertes | Bloquant | Produit |
| 2 | 91 % du code écrit avant la première question à un client ; le plan de `SPEC.md` §21 l'ordonne | Bloquant | Produit |
| 3 | L'objet « bien » n'est pas constructible avec les données autorisées (BUG-11 sans plan, 24 % et 37 % d'erreur d'appariement) | Bloquant | Données |
| 4 | Le moteur de score n'a aucun appelant ; la chaîne de publication est structurellement inatteignable (aucun INSERT de définition, segmentation jamais activée) | Bloquant | Backend |
| 5 | Le déploiement est impossible : aucune image construite, `API_IMAGE` manquant, aucun chargement de données, workflow rouge depuis le 4 septembre | Bloquant | Infra |
| 6 | Le pivot « biens en vente » contredit `SPEC.md` §24 et §28, sans amendement ni ADR | Critique | Produit |
| 7 | Aucune analyse juridique (DVF réidentification, inférence de vente à une adresse, API ADEME) alors que §18.3 l'exige | Critique | Juridique |
| 8 | 41 routes sur 45 anonymes, dont une écriture qui corrompt le jeu d'annotation | Critique | Sécurité |
| 9 | L'API tourne en propriétaire de la base ; la RLS est désarmable par le processus qu'elle protège | Critique | Sécurité |
| 10 | Zéro test d'intégration base ; 522 tests en 1,3 s ; 12 fichiers de tests grep le source | Critique | Tests |
| 11 | Aucune sauvegarde hors site, aucune rétention, `keycloak` et `dagster` jamais sauvegardés, disque plein en 5 à 7 nuits | Critique | Infra |
| 12 | Le protocole E9 ne peut pas trancher H1 : aveugle cassé sur E8f, cohorte signal exhaustive (18 unités), 2 juges | Critique | Produit |
| 13 | Aucune analyse concurrentielle ; les fonctions manquantes sont le cœur des leaders ; la divisibilité est déjà vendue | Critique | Marché |
| 14 | Aucun chemin exécutable vers « arrêter » : G9 dépend de G8 qui dépend de G1 (XL) | Élevé | Process |
| 15 | La rénovation-revente est non outillée (REN/BLD absentes, DPE 59 %) et infondée (décote 3-4 %) ; aucun ticket n'en tire la conséquence | Élevé | Produit |
| 16 | DS-08 hors régime de reproductibilité ; DS-01 sans version de transformation ; runbook faux et incomplet | Élevé | Pipelines |
| 17 | Dagster orchestre un asset ; 10 conteneurs sur 16 sans usage ; Redis référencé par aucun code | Élevé | Infra |
| 18 | `staging` déploie en production ; secrets `0400 root` illisibles par UID 10001 sur Linux ; admin Caddy sur `0.0.0.0:2019` ; `alloy` root avec le socket Docker | Élevé | Infra |
| 19 | Aucun rate limiting, aucun `statement_timeout` ; déni de service anonyme trivial sur la bbox | Élevé | Sécurité |
| 20 | La précision de la liste E8 n'a pas été remesurée après cinq itérations ; huit limites déclarées rendent un rejet ininterprétable | Élevé | Produit |
| 21 | Le front s'ouvre au large de l'Afrique ; l'inconnu est peint comme zéro ; deux écrans affichent « aucune donnée » sur un 500 ; l'OIDC déconnectera en boucle | Élevé | Front |
| 22 | Le ticket est écrit dans le même commit que le code (6 sur 9 E8*) ; les invariants sont calibrés à zéro détection et ne verraient aucun des bugs qui les justifient | Élevé | Process |
| 23 | `CLAUDE.md` faux sur six points d'état ; trois documents de pilotage contradictoires ; `SPEC.md` jamais amendé ; DS-10 attribué trois fois | Élevé | Documentation |
| 24 | Aucun dimensionnement de marché ni modèle économique ; plafond régional estimé ~3 000 € MRR ; rétention d'un produit « stock » non posée | Élevé | Marché |
| 25 | 12 contrats sur 14 déclaratifs ; seuils de classement en dur dans le moteur ; 25 blocs de connexion dupliqués ; 4 cycles `import_run` divergents | Moyen | Pipelines |

---

## 17. Ce qu'il faut garder, tel quel

Un audit sévère doit être exact. Ces éléments sont au-dessus de la moyenne du secteur et ne
doivent pas être sacrifiés au dégraissage :

- **Le référentiel spatial du 35 et ses mesures** : bâtiments physiques, relations avec confiance,
  quarantaine par attribut, motifs de manquant, rapports de qualité par commune.
- **La discipline des résultats négatifs** : 24 %, 37 %, `RISK-002` impossible, décote 3-4 %,
  `LAND-004` qui « ne sépare rien », cas manqué consigné plutôt que neutralisé. Rien n'est enterré.
- **Les garde-fous de publication** : rien de faux n'a jamais été publié en onze jours de vitesse.
- **Le refus d'inventer des seuils** : suppression du plancher 800 m² qui écartait 348 parcelles
  divisibles, refus de combiner âge et étiquette.
- **`manifest.py`**, `test_scoring_engine.py`, la validation Pydantic, l'absence d'injection SQL, les
  docstrings du front qui expliquent chaque décision d'affichage par l'incident qui l'a motivée.
- **La compétence `recompte-preuve`** et le **verrou humain déclaré** : les deux seuls dispositifs
  du process calibrés sur la classe d'erreur qui a réellement frappé.
- **Le signal DPE et les mesures de marge** : les deux résultats qui valent quelque chose pour un
  professionnel, et qui n'existent chez aucun concurrent sous cette forme transparente.

**La prochaine ligne de code à écrire est un appel téléphonique.** Le backlog l'a écrit le 15
septembre à 08:59. Ce document dit pourquoi, chiffre ce que ça coûte de ne pas le faire, et propose
avec quoi appeler.

---

## Annexe A — Mesures brutes du 15 septembre 2026

```text
Code (wc -l, hors node_modules, .venv, générés)
  backend/src            5 188 lignes   29 fichiers
  backend/tests          2 039          29
  backend/migrations     5 925          26
  pipelines/src         10 874          38
  pipelines/scripts      8 618          28
  pipelines/tests        5 687          32
  apps/web/src           5 317          10   (2 176 écrites à la main, 3 140 générées)
  scripts/               1 766 + 434 tests
  contracts/            22 641          40   (dont DS-08 manifeste 15 275, OpenAPI 5 335)
  docs/                 14 794         144
  racine .md             4 229          (SPEC 1 590, ARCHITECTURE 1 234, explo 936, CLAUDE 288)

make check : exit 0, 9,2 s
  backend   119 passed  0,26 s
  pipelines 334 passed  0,92 s
  scripts    69 passed  0,08 s
  aucune connexion PostgreSQL dans aucun conftest

Git : 128 commits, 2026-09-04 → 2026-09-15, 1 auteur
  par jour : 6 · 2 · 7 · 1 · 18 · 4 · 15 · 41 · 34
  docs-only : 47 / 128 ; docs/backlog/README.md touché 59 fois
  SPEC.md : 1 commit (initial)
  ticket-ok : 8 usages, tous sur docs/ ; invariant-ok : 4 dans le code

Base immo : 29 Go (pg_database_size), volume 32,83 Go ; MinIO 6,02 Go
  85 tables, 30 vides (app.*, scoring.*, market.*, meta.regional_*)
  feature.feature_value           8 524 Mo  19 941 510
  meta.entity_source_observation  4 855 Mo   2 697 244
  meta.entity_match               2 594 Mo   3 371 840
  meta.entity_source_identifier   2 266 Mo   4 715 121
  meta.entity_observation_link    1 352 Mo   1 552 941
  reference.cadastral_parcel      1 136 Mo   1 334 373
  tiles.parcel_render_v1          1 057 Mo   1 332 727
  observation.transaction           213 Mo     284 699
  observation.energy_assessment     507 Mo     207 944

Conteneurs (docker stats, au repos) : 16
  postgres 2,62 Gio · keycloak 539 Mio · alloy 367 · minio 247 · grafana 204 · loki 158
  prometheus 113 · dagster-daemon 106 · api 58 · martin 41 · dagster-code 30 · caddy 22
  dagster-webserver 20 · node-exporter 12 · web 8 · redis 4          total ≈ 4,4 Gio

API : 45 routes déclarées, 4 avec Depends(current_principal)
  (connected_mvp.py : 2, brittany_pilot.py : 2) ; aucune dépendance globale dans main.py
```

## Annexe B — Sources externes citées

Concurrents : kelfoncier.com (page marchands de biens, FAQ), pricehubble.com/products/urbanease,
telescop.com/fonctionnalites, geofoncier.fr/tarifs, prospect-plus.fr, immonator.fr (comparatif),
lesgrandesmaisons.fr (tarifs Immo Data), yanport.com/tarifs, diffuze.fr (SeLoger Pro).
Données : doc-datafoncier.cerema.fr (Fichiers fonciers, ayants droit), datafoncier.cerema.fr
(millésime 2025, acte d'engagement LOVAC), data.gouv.fr (MAJIC personnes morales, DVF+ open data,
BODACC, Cartofriches, LOVAC communal, Sitadel), legifrance (arrêté SPDC 2003, décret 2018-1350),
groupe-dvf.fr (vade-mecum, cadre légal), data.ademe.fr/pages/faq.
Marché : insee.fr/fr/statistiques/7763822 (secteur 681), annuaires 6810Z par département,
notaireetbreton.bzh (baromètre septembre 2025).
Réglementation : vizea.fr (loi TRACE), trackstone.fr (calendrier DPE), DREAL Bretagne (loi Le
Meur), cnil.fr (réutilisation de données publiques à des fins de démarchage).
Tendances : galivel.com, immo2.pro (Masteos, Immocitiz, PriceHubble/Urbanease).

Prix d'hébergement : grilles Hetzner, OVH, Scaleway de mémoire à la mi-2026, non revérifiées.
