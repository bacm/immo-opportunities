# Immo Opportunities — Spécification produit et technique

**Version :** 1.0 — **provisoire jusqu'au verdict de H3**
**Statut :** référence, réécrite le 15 septembre 2026 sur décision [ADR-016](./docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md)
**Remplace :** la version 0.2 du 3 août 2026, conservée dans l'historique git (`git show a32d439:SPEC.md`)
**Zone :** Ille-et-Vilaine (35) ; les autres départements bretons ne sont pas en périmètre tant qu'un abonné du 35 n'existe pas

---

## 1. Résumé

Immo Opportunities produit, à partir de données publiques françaises, une **intelligence de
marché immobilier locale** que les professionnels ne trouvent nulle part sous cette forme : ce que
rapporte réellement une revente selon le prix d'entrée, ce que vaut réellement une passoire
énergétique, quand un bien mis en vente part, à quel rythme un territoire mute. Chaque chiffre est
reproductible depuis les sources, recompté avant publication, et porte son effectif.

Le premier produit est **un baromètre du marché du 35 par EPCI** (V5). Le second, conditionné à un
avis juridique et au verdict des premiers professionnels rencontrés, est **un radar hebdomadaire
de mise en vente** (V2) fondé sur le dépôt des diagnostics de performance énergétique.

Ce que le produit n'est plus : une plateforme cartographique de détection de candidats off-market
pour marchands de biens. Cette plateforme existe dans le dépôt, elle est **gelée** (§11), et cette
spécification dit pourquoi.

---

## 2. Vision et promesse

### 2.1 Vision

Donner aux professionnels de l'immobilier d'un territoire une lecture de leur marché qui vient des
actes et des diagnostics, pas des annonces ni des estimations : des faits datés, agrégés
honnêtement, avec leurs limites écrites.

### 2.2 Promesse

> Savoir ce que le marché local fait réellement, avant d'y engager de l'argent.

### 2.3 Ce que le produit ne promet pas

- désigner un bien à acheter ;
- prédire qu'un bien précis sera vendu ;
- donner accès à un propriétaire personne physique ;
- estimer la valeur d'un bien non vendu ;
- interpréter un règlement d'urbanisme ;
- remplacer une expertise immobilière, urbanistique ou juridique.

---

## 3. Utilisateurs

### 3.1 Cible du baromètre (V5)

Tout professionnel qui engage du capital ou du temps sur le marché résidentiel du 35 : marchands
de biens, investisseurs-rénovateurs, aménageurs-lotisseurs, constructeurs de maisons individuelles,
agents immobiliers, géomètres-experts. Le baromètre ne suppose aucun outil, aucun compte, aucune
installation : c'est un document.

### 3.2 Cible du radar (V2), provisoire

Agents immobiliers cherchant des mandats et marchands de biens voulant arriver avant l'annonce.
**Provisoire** : H3 dit si cette cible existe et ce qu'elle paierait.

### 3.3 Ce que l'on sait des utilisateurs

Rien de mesuré. Au 15 septembre 2026, aucun entretien n'a eu lieu. H3 en fait cinq. Les
questions ouvertes de §25 restent ouvertes jusque-là.

---

## 4. Problème à résoudre

Les données qui décrivent un marché local — mutations DVF, diagnostics DPE, cadastre — sont
publiques, volumineuses, sales, et jamais croisées. Un professionnel raisonne donc sur son réseau,
sur les annonces et sur des estimateurs dont il ne voit ni les sources ni les effectifs.

Trois chiffres que le dépôt sait déjà produire et qu'aucun outil grand public ne publie sur le 35 :

| Question du professionnel | Réponse mesurée | Source |
|---|---|---|
| Où est la marge d'un marchand ? | dans le prix d'entrée : plus-value nette × 1,90 sous 60 % du marché, × 1,01 au prix | `docs/data/pistes-analyse-marche-35.md` §5.2 |
| Une passoire s'achète-t-elle décotée ? | à peine : 3 à 4 % pour E et F, rien de visible pour G | idem |
| Quand un bien mis en vente part-il ? | 35 % de mutation à 12 mois après un premier DPE, contre 3 % de base | `docs/data/dpe-signal-vente-35.md` |

Ces chiffres sont **non recomptés** au 15 septembre. H1 les rend reproductibles et les recompte.

---

## 5. Hypothèses à valider

Les hypothèses H1 à H6 de la version 0.2 supposaient une plateforme et un classement. Elles sont
remplacées par celles que H3 peut réellement mesurer avec cinq professionnels.

| ID | Hypothèse | Mesure | Signal |
|---|---|---|---|
| HB1 | Le baromètre apprend au professionnel quelque chose qu'il ne savait pas | verbatims : ce qu'il conteste, ce qu'il reconnaît | au moins trois des cinq nomment un chiffre nouveau pour eux |
| HB2 | Le professionnel paierait le baromètre | prix chiffré demandé en fin d'entretien | au moins deux prix déclarés, non nuls |
| HR1 | Le radar de mise en vente intéresse | réaction à la description en une phrase, prix chiffré | au moins deux prix déclarés |
| HR2 | Le signal DPE tient dans le temps | taux à 12 mois sur trois cohortes annuelles | écart inférieur à cinq points entre cohortes couvertes |
| HP | Le goulot du métier est trouver, acheter au bon prix, ou obtenir l'autorisation | question ouverte, réponse classée | oriente V1, V2 ou V3 |

Ces seuils sont des objectifs de validation avec cinq personnes : ils n'autorisent aucun
pourcentage ni aucune inférence statistique, et H3 le dit.

---

## 6. Périmètre

### 6.1 Inclus

- **V5, le baromètre du marché du 35** : mesures reproductibles (§7, §13.4), document par EPCI
  (§7.4), entretiens (H3).
- **V2, le radar de mise en vente**, conditionné à H4 (avis juridique) et H3 (verdict) : §8.
- Le référentiel spatial du 35 et les quatre sources métier importées, qui alimentent les deux.

### 6.2 Gelé

La plateforme : Explorer carte/liste/fiche, moteur de score, workflow de qualification, scénarios
financiers, administration régionale, multi-tenant OIDC/RLS, tuiles, déploiement VPS. Elle existe,
elle est décrite en §11, et rien n'y est ajouté tant que H3 n'a pas rendu son verdict.

### 6.3 Différé, ouvert

- **V1** — gisement foncier divisible assumé comme produit parcellaire (audit §14.2).
- **V3** — off-market personnes morales par MAJIC PM × BODACC × Sirene.
- **V4** — prestation pour un EPCI ayant droit des Fichiers fonciers et de LOVAC.
- **V6** — vente de la couche morphologie et qualité aux outils nationaux.

Chacune s'ouvre par une ADR, pas par un ticket.

### 6.4 Hors périmètre

- propriétaire personne physique, sous toute forme (§13.6) ;
- scraping d'annonces ou d'annuaires ;
- prospection automatisée et contact de particuliers ;
- prédiction certaine de vente ou de vacance ;
- indice de vacance, LOVAC et données à accès restreint ;
- estimation de la valeur d'un bien non vendu ;
- règlement d'urbanisme interprété ;
- France entière, marketplace, API commerciale publique ;
- extension aux 22, 29 et 56 avant un abonné du 35.

---

## 7. Produit V5 — le baromètre du marché

### 7.1 Ce qu'il est

Un document par EPCI du 35, plus un document départemental, régénéré à chaque nouveau millésime
DVF ou extrait DPE, qui répond à quatre questions : le marché (volumes, prix), la marge (plus-value
par prix d'entrée), l'énergie (décote par étiquette), le tempo (délai de vente et taux de mutation
après DPE).

### 7.2 Les mesures

Registre `BAR-*` en §13.4. Toutes sont agrégées ; **aucune parcelle, aucune adresse, aucune
mutation individuelle** n'apparaît dans le baromètre.

### 7.3 Règles de construction

- **Le filtre de chaque cohorte est écrit dans la sortie** : relations bâtiment ↔ parcelle
  retenues, premier DPE par parcelle, types exclus. Un effectif sans son filtre n'est pas
  reproductible — leçon de l'écart 14 532 / 9 754 de `dpe-signal-vente-35.md`.
- **Un taux ne paraît jamais sans son effectif.** Un seuil de support est un paramètre déclaré,
  pas un seuil de sens métier.
- **Aucune cohorte dont les douze mois ne sont pas couverts par DVF** n'entre dans un taux à
  douze mois. DVF s'arrête au 31 décembre 2025.
- **La réforme DPE du 1er janvier 2026** est une rupture de série : les mesures par étiquette
  distinguent avant et après, ou portent la réserve.
- **Les DPE d'appartement générés depuis un DPE d'immeuble** sont exclus des mesures de conversion
  (0,6 % de conversion, mesuré) ; l'exclusion est comptée.
- Aucune valeur manquante n'est convertie en zéro ; une commune sans support l'affiche.
- Contrôle commune × année seulement : pas de modèle hédonique, pas de pondération.

### 7.4 Forme

HTML autonome imprimable en A4, graphiques SVG sans dépendance réseau, une page par EPCI avec
support, mentions de sources, millésimes, date de génération, attribution Licence Ouverte 2.0.
Détail dans [H2](./docs/backlog/H2-barometre-document-publiable.md).

### 7.5 Ce qu'il n'est pas

Pas un score, pas une liste, pas un classement, pas une estimation. Pas une application : aucun
compte, aucune carte, aucune API.

---

## 8. Produit V2 — le radar de mise en vente (provisoire)

Cette section est **provisoire** : elle décrit l'intention. Ses colonnes sont fixées par H4, sa
cadence et son canal par H3.

### 8.1 Ce qu'il est

Chaque semaine, pour un secteur choisi, la liste des parcelles bâties dont un premier DPE de
maison a été déposé depuis le dernier envoi, avec l'âge du dépôt, la chance résiduelle de vente
observée sur la cohorte de référence, l'étiquette, le taux de la commune et la dernière mutation
connue.

### 8.2 Ce qu'il repose sur

Un fait administratif : un DPE est obligatoire pour vendre, son dépôt est daté et public. Mesuré
sur le 35 (`docs/data/dpe-signal-vente-35.md`) : le dépôt précède l'acte de 169 jours en médiane,
et 35 % des parcelles à premier DPE mutent dans les douze mois contre 3 %. Ce n'est pas un
modèle : rien n'est appris, aucun seuil n'est inventé, chaque ligne s'explique par sa date.

### 8.3 Règles

- **La cadence est une release** : chaque extrait ADEME est épinglé, checksumé, importé sous sa
  version de transformation. Pas d'alias, pas de « dernier extrait ».
- **La fenêtre se compte depuis la date d'extrait**, jamais depuis l'horloge.
- **Âge et étiquette sont deux lectures indépendantes**, jamais combinées en un score.
- **Les colonnes nominatives sont celles que H4 autorise.** Si l'avis interdit l'adresse, la ligne
  porte la parcelle et la commune ; si l'avis interdit la chance individuelle, elle porte le taux
  communal.
- Deux envois consécutifs ne contiennent aucun doublon.

### 8.4 Ce qu'il n'est pas

Pas de l'off-market : un DPE frais désigne un bien qui entre sur le marché. Le document le dit en
première ligne. Pas une prédiction sur un bien : une fréquence observée sur une cohorte.

---

## 9. Exigences fonctionnelles

### 9.1 Baromètre

| ID | Exigence | Critère |
|---|---|---|
| BR-001 | Régénérer le baromètre à l'identique depuis la base | même graine, mêmes filtres écrits, même sortie |
| BR-002 | Publier chaque taux avec son effectif et sa période | aucune valeur sans effectif |
| BR-003 | Afficher « support insuffisant : n » plutôt qu'une valeur | testé sur fixture |
| BR-004 | Écrire le filtre de chaque cohorte dans la sortie | lisible en clair dans le rapport |
| BR-005 | Ne contenir aucune parcelle ni adresse | test négatif sur identifiant cadastral et adresse |
| BR-006 | Distinguer avant et après la réforme DPE 2026 | réserve ou séparation par période |
| BR-007 | Passer `recompte-preuve` avant publication | mention datée en tête du rapport |

### 9.2 Radar (provisoire)

| ID | Exigence | Critère |
|---|---|---|
| RD-001 | Une release DS-07 par extrait hebdomadaire | manifeste, checksum, version de transformation |
| RD-002 | Aucun doublon entre deux envois consécutifs | test sur deux releases |
| RD-003 | Colonnes nominatives limitées à celles de l'avis juridique | citées en tête du rapport |
| RD-004 | Taux et courbe de référence issus du baromètre recompté | référence croisée |
| RD-005 | Première ligne : « ce n'est pas de l'off-market » | présente dans chaque envoi |

### 9.3 Plateforme gelée

FR-001 à FR-016 de la version 0.2 décrivaient l'Explorer, le scoring, le workflow, les exports
et les alertes. Elles ne sont ni abandonnées ni actives : voir §11.

---

## 10. Ce que les données ont établi sur le 35

Résultats mesurés, datés, à ne pas redécouvrir. Les rapports sont dans `docs/data/`.

### 10.1 Résultats positifs, non recomptés

| Résultat | Mesure | Source |
|---|---|---|
| Dépôt DPE → mutation à 12 mois | 35,1 à 35,7 % contre 3,03 % ; lift × 11,8 ; 2023 : 34,2 % | `dpe-signal-vente-35.md`, `pistes-analyse-marche-35.md` §5.1 |
| Délai dépôt → acte | médiane 169 jours, Q1 113, Q3 282 | idem |
| Courbe de conversion | 2 % à 3 mois, 20 % à 6 mois, 35 % à 12 mois, 43 % à 24 mois | idem |
| Par étiquette | courbe en U : F et G convertissent 40 % de plus que C et D | idem |
| Plus-value nette par prix d'entrée | × 1,90 sous 60 % du marché, × 1,23 entre 60 et 80 %, × 1,01 au prix | §5.2 |
| Décote énergétique, maisons | 3 à 4 % pour E et F, invisible pour G (202 ventes) | §5.2 |
| Extension de surface | ratio prix total × 1,37, prix au m² × 1,00 (205 paires) | §5.2 |

### 10.2 Résultats négatifs, établis

| Résultat | Mesure | Source |
|---|---|---|
| Adresse ↔ parcelle | 24 % d'erreur, irréductible par containment, proximité ou distance | `spatial-matching-manual-review-35.md` |
| Bâtiment ↔ parcelle | 37 % d'erreur avant BUG-09 ; 400 706 relations sur 1,24 M à recouvrement < 10 % | idem |
| Unité foncière | une par parcelle ; la contiguïté donne des grappes de 3 494 parcelles | `docs/backlog/BUG-11` |
| DPE rattaché au bâtiment | 59 % ; 10 % non rattachés | `dpe-matching-35.md` |
| DVF sans prix allouable | 65,5 % des mutations | `dvf-quality-35.md` |
| Zone inondable typée | aucune source sur le 35 | `georisques-coverage-35.md` |
| Profils de règles d'urbanisme | zéro ; D2b estimé à quatre années-personne à l'échelle nationale | `gpu-coverage-35.md` |
| Usage du bâti par morphologie seule | 2 candidats d'intérêt sur 10 | `docs/backlog/E8b` |

Ces négatifs sont la raison du gel : ils rendent l'objet « bien » inconstructible avec les données
autorisées, et la stratégie rénovation-revente infondée.

---

## 11. La plateforme gelée

### 11.1 Ce qui existe

Un Explorer React/MapLibre (recherche d'adresse réelle, fiches parcelle et bâtiment, mutations DVF
et diagnostics DPE par parcelle, bannière de couverture), une API FastAPI de 45 routes, un moteur
de score reproductible à deux définitions, un workflow de qualification, des scénarios financiers,
une administration régionale, une authentification OIDC Keycloak avec isolation par organisation
en RLS, des tuiles vectorielles Martin, un déploiement Ansible jamais exécuté. Le détail est dans
[`ARCHITECTURE.md`](./ARCHITECTURE.md) §11 et dans [l'audit](./docs/audit-critique-2026-09-15.md) §7 à §10.

### 11.2 Pourquoi elle est gelée

Aucun `OpportunitySnapshot` n'a jamais été publié et le moteur n'a aucun appelant ; les quatre
écrans qui portent la promesse sont vides ; personne ne l'a vue ; et l'objet qu'elle score, une
parcelle, n'est pas un bien. Construire davantage avant un verdict client serait spécifier une
seconde fois sans client.

### 11.3 Conditions de dégel

Le gel se lève par une ADR, après H3, et seulement si les conditions suivantes sont réunies :

- un professionnel a demandé une carte, une fiche ou un workflow, et l'a dit avec un prix ;
- les défauts bloquants de l'audit sont corrigés avant tout déploiement : authentification sur
  toutes les routes, rôle base de moindre privilège, `statement_timeout`, banc PostGIS en CI,
  sauvegarde hors site ;
- la définition de score à publier est fondée sur un profiling observé, pas sur les seuils en dur
  du moteur.

---

## 12. Vacance

Retirée. Aucun module, aucun indice, aucun feature flag. Toute reprise passe par V4 et un
partenariat avec un ayant droit de LOVAC.

---

## 13. Données

### 13.1 Sources et état réel

| ID | Dataset | Producteur | État au 15 septembre 2026 | Rôle |
|---|---|---|---|---|
| DS-01 | Cadastre Etalab, PCI Vecteur | DGFiP / Etalab | **acceptée**, publiée, 1 333 327 parcelles | référentiel spatial |
| DS-02 | Référentiel National des Bâtiments | RNB | **acceptée**, 514 859 bâtiments physiques | identité bâtiment |
| DS-03 | BDNB Open | CSTB | `display_only` | attributs bâtiment, sans rattachement RNB |
| DS-04 | BD TOPO bâti et routes | IGN | `display_only` | usage, hauteur, année ; identité BD TOPO ↔ RNB acceptée 60/60 |
| DS-05 | Base Adresse Nationale | BAN / IGN | `display_only` | recherche ; adresse ↔ parcelle à 24 % d'erreur |
| DS-06 | DVF géolocalisé Etalab 2021-2025 + archive DGFiP 2014-2020 | DGFiP / Etalab | `display_only`, 285 k mutations | **baromètre, radar** |
| DS-07 | DPE logements existants, extrait API | ADEME | `display_only`, 208 k diagnostics, rattachés à 59 % | **baromètre, radar** |
| DS-08 | Géoportail de l'urbanisme, CNIG | collectivités / GPU | `display_only`, 152 documents sur 184, sans checksum | contexte ; gelé |
| DS-09 | Géorisques, dix familles | DGPR / BRGM | `display_only` | contexte ; gelé |
| DS-10 | Sitadel, autorisations d'urbanisme | SDES | **réservé**, aucun contrat | vérité terrain ex post de V1 |
| DS-11 | MAJIC personnes morales | DGFiP | **réservé**, aucun contrat | propriétaire personne morale, V3 |
| DS-12 | BODACC et Sirene | DILA / INSEE | **réservé**, aucun contrat | procédures collectives, V3 |

La version 0.2 attribuait DS-10 à OCS GE, DS-11 à BD ORTHO, DS-12 à `CandidateReview` et DS-13 à
LOVAC. Ces quatre sont retirées ; l'identifiant DS-10 était attribué trois fois dans le dépôt.

### 13.2 Ce qui n'a pas de source

Deux motifs de rejet relevés en relecture terrain n'ont aucune source dans le dépôt : la couverture
du sol (« déjà goudronné », OCS GE non importé) et les constructions surfaciques (« il y a une
piscine », couche BD TOPO non importée). Une liste morphologique plafonnera toujours à ce que la
photo aérienne ou la visite lève.

### 13.3 Catégories d'utilisation

- **Dans le baromètre** : DS-06, DS-07, le référentiel DS-01 et DS-02 pour rattacher un diagnostic
  à une parcelle bâtie.
- **Dans le radar** : les mêmes, plus DS-05 pour l'adresse si H4 l'autorise, DS-08 pour le zonage
  comme contexte.
- **Affichées, non classifiantes** : DS-03, DS-04, DS-09, dans la plateforme gelée.
- **Réservées** : DS-10 à DS-12, sans contrat ni import tant qu'une ADR n'ouvre pas V1 ou V3.

### 13.4 Registre des mesures du baromètre

| ID | Mesure | Datasets | Granularité | Support minimal (paramètre déclaré) |
|---|---|---|---|---|
| BAR-001 | volumes de mutations, maisons et appartements | DS-06 | EPCI × année, commune × année | 15 ventes par an |
| BAR-002 | prix médian au m², quartiles | DS-06 | idem | 15 |
| BAR-003 | plus-value nette de marché par prix d'entrée, ventes répétées | DS-06 | département, EPCI | 30 paires |
| BAR-004 | décote ou surcote par étiquette DPE, contrôle commune × année | DS-06, DS-07 | département, EPCI | 30 ventes par étiquette |
| BAR-005 | délai dépôt DPE → acte, quartiles | DS-06, DS-07 | commune, EPCI | 200 parcelles |
| BAR-006 | taux de mutation à 12 mois après premier DPE, par cohorte | DS-06, DS-07 | commune, EPCI, département | 200 |
| BAR-007 | courbe de conversion mensuelle, dernière cohorte couverte | DS-06, DS-07 | EPCI, département | 200 |
| BAR-008 | effet de l'extension de surface sur le prix | DS-06 | département | 30 paires |
| BAR-009 | part des mutations sans prix allouable, part des DPE non rattachés | DS-06, DS-07 | commune | — |

Les supports sont des paramètres du script, affichés dans la sortie, et contestables. Ils ne sont
pas des seuils de sens métier.

### 13.5 Features de la plateforme gelée

Les registres LAND-*, BLD-*, URB-*, MKT-*, RISK-*, REN-* et FIN-* de la version 0.2 vivent dans
`contracts/features/` et `contracts/scoring/`. Ils sont gelés avec la plateforme. L'audit §8.4
note que douze contrats sur quatorze ne sont lus par aucun code.

### 13.6 Données et features interdites

- âge, nom, coordonnées ou catégorie supposée d'un **propriétaire personne physique** ;
- variables socio-économiques individuelles ou prédictions de ménage ;
- données scrapées depuis des annonces ou annuaires ;
- fichier des personnes décédées de l'INSEE, sous toute forme ;
- DPE ou prix simulés ;
- absence de DPE utilisée comme preuve de vacance ou de dégradation ;
- « pas de mutation depuis N ans » comme propension du propriétaire à vendre — contexte seulement ;
- texte de règlement d'urbanisme interprété automatiquement ;
- combinaison de signaux en un score de mise en vente sans profiling écrit ;
- données créées après la date d'un extrait dans une mesure rétrospective.

Le propriétaire **personne morale** (MAJIC PM) n'est pas interdit ; il est réservé à V3, et son
usage sera autorisé ou non par H4.

### 13.7 Politique des valeurs manquantes

Une valeur manquante reste manquante avec un motif. Jamais convertie en zéro, jamais imputée. Un
taux sans support n'est pas un taux à zéro. Vocabulaire des motifs : `source_value_missing`,
`source_not_accepted`, `not_applicable`, `ambiguous_match`, `support_insufficient`,
`cohort_not_covered`.

### 13.8 Critères d'acceptation d'un dataset

Inchangés depuis la version 0.2 : licence enregistrée, ressource reproductible, millésime
identifiable, schéma versionné, couverture mesurée par commune, champs documentés, distributions
analysées, appariement évalué sur échantillon, règle de fraîcheur. Une source `display_only` peut
alimenter le baromètre **si le baromètre écrit sa limite** (rattachement à 59 %, prix non allouable
à 65 %) ; elle ne peut pas alimenter un score.

### 13.9 Contrat de source et reproductibilité

Chaque source possède un contrat `contracts/datasets/DS-*/v1.json` et un manifeste par release.
Règles non négociables : SHA-256 avant import, pas d'alias `latest` enregistré comme URL d'import,
version de transformation dans la clé d'idempotence et l'identifiant de run, copie archivée nommée
au manifeste quand l'URL amont n'est pas immuable. Deux exceptions connues et à résorber : DS-01
ne porte pas de version de transformation dans sa clé ; DS-08 n'a ni checksum ni archive.

### 13.10 Qualité

Copie brute immuable, transformations versionnées, quarantaine par attribut (BUG-03), couverture
par commune, motifs de manquant, séparation absence / nullité / non-applicabilité / erreur. Un
chiffre publié dans `docs/data/` passe par `recompte-preuve`.

### 13.11 Résolution des entités, état réel

Adresse ↔ parcelle ↔ bâtiment ↔ transaction ↔ DPE. Les liens portent méthode, confiance et
version. L'état mesuré (§10.2) fixe ce que le baromètre peut faire : rattacher un DPE à une
parcelle bâtie par `id_rnb` et relation certaine, jamais par adresse seule. Une chaîne
adresse → parcelle → bâtiment → transaction porte une incertitude composée que le baromètre
contourne en n'agrégeant qu'à la commune.

---

## 14. Modèle de données

Neuf schémas PostgreSQL : `meta` (releases, imports, appariements, quarantaine), `reference`
(zones, adresses, parcelles, bâtiments, unités), `observation` (transactions, DPE, urbanisme,
risques), `feature`, `scoring`, `market`, `app`, `tiles`, `audit`. 85 tables, dont 30 vides au 15
septembre : tout `app.*`, `scoring.*` et `market.*`, c'est-à-dire la plateforme gelée.

Le baromètre n'ajoute aucune table : il lit `observation.transaction`,
`observation.energy_assessment`, `reference.*` et écrit des fichiers. Le radar ajoutera une
release DS-07 par semaine dans `meta.dataset_release` et rien d'autre.

---

## 15. Sorties et interfaces

- **Baromètre** : fichiers Markdown, CSV et HTML dans `docs/data/barometre-marche-35/`, régénérés
  par `make market-barometer` et `make market-barometer-kit`. Aucune API.
- **Radar** : un fichier par secteur et par semaine, canal fixé par H3. Aucune API tant qu'un
  abonné n'existe pas.
- **API et tuiles de la plateforme** : gelées ; l'API reste servie en local pour la vérification
  des données (fiches parcelle, mutations, diagnostics), sans authentification, ce qui interdit
  tout déploiement public en l'état.

---

## 16. Architecture

Définie dans [`ARCHITECTURE.md`](./ARCHITECTURE.md). En une phrase : PostgreSQL/PostGIS porte les
données, des scripts Python reproductibles les importent et produisent des documents ; la
plateforme applicative existe autour et est gelée.

---

## 17. Exigences non fonctionnelles

- **Reproductibilité** avant performance : même base, même graine, même sortie.
- **Recompte adversarial** avant publication de tout chiffre.
- **Aucune donnée nominative** dans le baromètre ; colonnes du radar bornées par H4.
- **Réforme DPE 2026** traitée comme rupture de série.
- **Ressources** : la base du 35 pèse 29 Go ; le baromètre tourne sur la base locale ; aucun
  déploiement n'est requis pour V5.
- Les exigences de performance, disponibilité et accessibilité de la version 0.2 s'appliquent à la
  plateforme gelée et sont suspendues avec elle.

---

## 18. Confidentialité, conformité et usage responsable

### 18.1 Principes

Minimisation, finalités documentées, séparation stricte entre données ouvertes et données
restreintes, vérification des licences, aucun scraping. Inchangés.

### 18.2 Prospection

Le produit n'automatise pas le contact de particuliers. Depuis le 11 août 2026, le démarchage
téléphonique B2C sans consentement est interdit ; un outil qui désigne des logements de
particuliers à des professionnels engage une responsabilité que H4 qualifie.

### 18.3 Présentation des résultats

- aucune étiquette « vacant », « abandonné », « propriétaire vendeur », ni « probablement en
  vente » sur un logement identifiable avant H4 ;
- le baromètre n'identifie aucun bien ;
- vocabulaire de fréquence observée, jamais de probabilité individuelle ;
- limites et effectifs écrits sur chaque page.

### 18.4 Cadre légal de DVF

Loi 2018-727, décret 2018-1350, article L112 A du LPF : finalité de transparence des marchés,
**interdiction de réidentification** ayant pour objet ou pour effet de remonter au vendeur ou à
l'acheteur. Le baromètre, agrégé, est conforme par construction. Une fiche parcellaire montrant les
mutations d'une parcelle identifiée avec son adresse, comme la plateforme gelée le fait, est
**à qualifier** : question 1 de H4.

### 18.5 Revue juridique

Exigée depuis le 3 août 2026 par la version 0.2, jamais faite. C'est [H4](./docs/backlog/H4-avis-juridique-donnees.md),
verrou humain, préalable au radar. Ses cinq questions couvrent DVF rapproché d'une parcelle,
l'inférence de mise en vente à une adresse, la responsabilité sur le démarchage, l'API ADEME, et
MAJIC PM × BODACC.

---

## 19. Administration

Il n'y a pas d'interface d'administration pour V5. Les gestes sont des cibles `make` :
`market-barometer`, `market-barometer-kit`, et les imports existants (`dvf-import`, `dpe-pin`,
`dpe-import`). L'administration régionale de la plateforme est gelée.

---

## 20. Mesures de succès

| Produit | Mesure | Où |
|---|---|---|
| Baromètre | cinq entretiens tenus, prix déclarés, verbatims | `docs/data/entretiens-professionnels-35.md` |
| Baromètre | nombre de destinataires du document par édition | journal d'envoi, hors dépôt |
| Radar | abonnés payants sur le 35 | hors dépôt |
| Radar | précision observée ex post : part des lignes envoyées mutées dans les 12 mois, mesurée au millésime DVF suivant | `docs/data/` |

La north star metric de la version 0.2 (« candidats qualifiés par heure ») est retirée : elle
supposait une plateforme et un classement.

---

## 21. Plan et roadmap

Celle d'[ADR-016](./docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md) :

```text
H1 baromètre 35 → H2 document publiable → H3 cinq entretiens ─┬─► H5 radar (H4 avis juridique)
                                                              └─► H6 documentation (ce ticket)
```

Après H3, une ADR tranche : poursuivre V5 et V2, ouvrir V1 ou V3, dégeler la plateforme, ou
arrêter. Aucune extension géographique avant un abonné du 35.

---

## 22. Monétisation, provisoire

Les prix de la version 0.2 (79 / 249 € / sur devis) venaient d'un brainstorm et n'ont jamais été
confrontés à personne. Ils sont retirés. Repères de marché relevés le 15 septembre 2026 (audit
§4.2) : outils de données publics 25 à 90 €/mois (Prospect+, Géofoncier, Immo Data), pige 29 à
100 €/mois, leaders de la prospection foncière sur devis.

Hypothèses à poser en H3, sans les défendre :

| Offre | Forme | Prix à demander |
|---|---|---|
| Baromètre EPCI | document trimestriel, ou à chaque millésime | prix unitaire et abonnement annuel |
| Radar secteur | envoi hebdomadaire | abonnement mensuel |
| Baromètre départemental gratuit | page publique | 0 €, canal d'acquisition |

Le modèle économique réel — nombre de clients, plafond régional, rétention — est écrit après H3,
pas avant.

---

## 23. Risques

| Risque | Impact | Réponse |
|---|---|---|
| Les professionnels connaissent déjà ces chiffres | critique | H3 le mesure ; si vrai, V5 n'est pas un produit et V1 ou V3 remontent |
| Le signal DPE ne tient pas hors 2023-2024 | élevé | HR2, trois cohortes ; DVF 2026 au prochain millésime |
| L'inférence de mise en vente est jugée illicite | élevé | H4 avant H5 ; repli sur le taux communal |
| L'écart de comptage du signal DPE n'est pas explicable | élevé | H1 le recompte ; sinon le taux publié est celui du filtre écrit |
| Rattachement DPE à 59 % biaise les mesures | moyen | biais écrit dans chaque page ; mesure de sensibilité avec et sans relations ambiguës |
| Réforme DPE 2026 rend les étiquettes non comparables | moyen | rupture de série déclarée |
| Le marché régional plafonne bas | moyen | assumé : c'est un produit de niche jusqu'à preuve du contraire |
| La plateforme gelée est déployée par erreur | élevé | 41 routes anonymes, rôle propriétaire : aucun déploiement sans les corrections de §11.3 |

---

## 24. Décisions prises

- ADR-001 à ADR-015 restent valides pour la plateforme gelée ([`ARCHITECTURE.md`](./ARCHITECTURE.md) §23).
- **ADR-016** : intelligence de marché d'abord, radar ensuite, plateforme gelée.
- Le propriétaire personne physique reste hors périmètre ; la personne morale est réservée à V3.
- La rénovation-revente sort du MVP : la décote énergétique mesurée ne la soutient pas.
- Aucune combinaison de signaux en score sans profiling écrit.
- `SPEC.md` est réécrit, pas amendé, et relu par H3.

---

## 25. Questions encore ouvertes

Elles n'empêchent pas H1 ni H2 ; elles conditionnent H5 et la suite.

1. Que sait déjà un marchand de biens du 35 de sa marge et de ses délais ? (HB1)
2. Le goulot du métier est-il trouver, acheter au bon prix, ou obtenir l'autorisation ? (HP)
3. Combien de lignes par semaine un agent ou un marchand veut-il recevoir, et pour quel secteur ?
4. Quel canal : courriel, PDF, CSV, page ?
5. Le même radar est-il vendu à plusieurs professionnels d'un même secteur, ou exclusif ?
6. Que vaut légalement l'adresse dans le radar ? (H4)
7. Existe-t-il quelques centaines de cibles personnes morales sur le 35 ? (V3, à sonder)
8. Une DP de division suit-elle réellement les parcelles jugées divisibles ? (V1, Sitadel)

---

## 26. Definition of Done

### 26.1 Baromètre (V5)

- H1 : mesures BAR-001 à BAR-009 régénérables à l'identique, filtres écrits, tests sur fixture,
  recompte passé, écart 14 532 / 9 754 expliqué ou remplacé ;
- H2 : un document par EPCI avec support, aucune parcelle ni adresse, lisible imprimé ;
- H3 : cinq entretiens, méthode actuelle relevée avant présentation, prix déclarés, verbatims
  conservés, conclusion explicite.

### 26.2 Radar (V2)

- H4 : avis écrit, cinq questions répondues en trois valeurs ;
- H5 : deux semaines produites depuis deux releases distinctes sans doublon, colonnes autorisées
  citées, taux et courbe issus du baromètre recompté ;
- un abonné du 35, ou un refus explicite documenté.

### 26.3 Dégel de la plateforme

Voir §11.3. Aucun critère de la DoD de la version 0.2 (quatre départements, carte Bretagne, trois
professionnels sur la plateforme) n'est repris tant que le gel n'est pas levé.

---

## 27. Références de données et conformité

Sources en contrat : cadastre.data.gouv.fr ; RNB sur data.gouv.fr ; BDNB Open et son modèle
(bdnb.io) ; BD TOPO (geoservices.ign.fr) ; BAN (adresse.data.gouv.fr) ; DVF géolocalisé Etalab
(files.data.gouv.fr/geo-dvf) et archives DGFiP ; DPE ADEME (data.ademe.fr, API data-fair) ;
Géoportail de l'urbanisme et standard CNIG ; Géorisques.

Sources réservées : Sitadel (SDES) ; fichiers MAJIC des personnes morales (data.gouv.fr) ; BODACC
(bodacc.fr, API) ; Sirene (INSEE).

Cadre légal et accès : loi 2018-727 et décret 2018-1350 sur DVF ; vade-mecum du groupe DVF sur le
cadre légal ; doc-datafoncier.cerema.fr pour les Fichiers fonciers et LOVAC (ayants droit
seulement) ; CNIL, réutilisation de données publiques à des fins de démarchage ; CNIL, prospection
commerciale ; ADEME, FAQ des conditions d'usage.

Marché et concurrence : INSEE, fiche secteur 681 ; audit du 15 septembre 2026 §4 pour le tableau
des outils existants et leurs prix publics.

---

## 28. Glossaire

**Baromètre** : document de mesures de marché agrégées par EPCI ou commune, sans bien identifié.
**Cohorte** : ensemble de parcelles définies par un même événement daté (premier DPE d'une année),
suivies sur une durée fixe.
**Conversion** : part d'une cohorte ayant connu une mutation dans un délai donné.
**Effectif** : nombre d'observations qui fondent un taux ; toujours publié avec lui.
**Filtre de cohorte** : règles d'inclusion écrites dans la sortie, sans lesquelles un effectif n'est
pas reproductible.
**Gel** : état de la plateforme applicative — existante, non développée, non déployée, dégelée par
ADR seulement.
**Plus-value nette de marché** : ratio revente / achat divisé par l'évolution du prix médian de la
commune sur la période.
**Radar** : flux hebdomadaire des parcelles dont un premier DPE vient d'être déposé.
**Recompte** : recalcul d'un chiffre publié depuis les sources, sans lire le code qui l'a produit.
**Rupture de série** : changement de définition d'une donnée source (réforme DPE 2026) qui interdit
de comparer avant et après sans le dire.
**Support** : effectif minimal, déclaré comme paramètre, en dessous duquel une mesure n'est pas
publiée.
