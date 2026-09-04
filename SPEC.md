# Immo Opportunities — Spécification produit et technique

**Version :** 0.2  
**Statut :** Draft de référence  
**Date :** 3 août 2026  
**Zone MVP :** Bretagne — Côtes-d'Armor, Finistère, Ille-et-Vilaine et Morbihan  

---

## 1. Résumé

Immo Opportunities est une application B2B qui aide les professionnels de l'immobilier à identifier, classer et qualifier des actifs immobiliers potentiellement sous-exploités avant qu'ils ne soient visibles dans leur flux habituel de recherche.

Le produit croise des données publiques immobilières, cadastrales, urbanistiques, environnementales et énergétiques pour produire une shortlist cartographique de candidats, propre à chaque stratégie d'investissement.

La plateforme ne prétend pas connaître l'intention de vente d'un propriétaire. Elle détecte des **candidats off-market à approfondir**, et non des ventes futures certaines.

La vacance éventuelle est un module expérimental et facultatif. Elle n'entre pas dans le score principal tant que sa valeur prédictive n'a pas été validée.

Le MVP couvre l'ensemble de la région Bretagne. La couverture n'est pas limitée à une commune de démonstration ou à une seule métropole.

---

## 2. Vision

Permettre à un professionnel de passer d'un territoire composé de milliers de bâtiments à une liste courte, explicable et actionnable de candidats adaptés à sa stratégie.

Le produit n'est pas une simple carte de données. Sa valeur repose sur :

- la résolution des entités immobilières ;
- la qualité et la provenance des signaux ;
- le classement par stratégie ;
- l'explication des résultats ;
- les scénarios financiers ;
- la boucle de validation terrain ;
- l'intégration au travail de prospection.

### 2.1 Promesse

> Trouver plus vite les actifs qui méritent une analyse approfondie, comprendre pourquoi ils ressortent et organiser leur qualification.

### 2.2 Ce que le produit ne promet pas

- prédire avec certitude qu'un bien sera prochainement vendu ;
- déclarer qu'un logement est vacant ou abandonné ;
- garantir une constructibilité ou une autorisation administrative ;
- fournir une expertise immobilière, urbanistique ou juridique opposable ;
- garantir un prix d'achat, un coût de travaux ou une marge finale.

---

## 3. Utilisateurs

### 3.1 Utilisateur principal du MVP

**Marchand de biens ou investisseur-rénovateur indépendant opérant en Bretagne.**

Objectifs :

- identifier des maisons et petites propriétés sous-exploitées ;
- détecter un potentiel de division, d'extension ou de rénovation-revente ;
- éliminer rapidement les mauvais dossiers ;
- conserver et suivre les candidats intéressants ;
- réduire le temps passé à croiser plusieurs portails.

### 3.2 Utilisateurs secondaires, après validation

- équipes de marchands de biens ;
- chasseurs immobiliers ;
- promoteurs sur des stratégies foncières adaptées ;
- agences cherchant des mandats ;
- collectivités sur un produit distinct consacré à la vacance.

Les collectivités et les professionnels privés ne partagent pas le même produit, les mêmes droits d'accès aux données ni le même workflow. Leur rapprochement éventuel fera l'objet d'une spec séparée.

---

## 4. Problèmes à résoudre

### 4.1 Problème principal

Les données nécessaires à l'identification d'un candidat sont dispersées entre plusieurs sources. Leur lecture manuelle est longue et difficile à répéter sur un territoire entier.

### 4.2 Problèmes secondaires

- les filtres simples produisent trop de candidats ;
- les données sont de fraîcheur et de qualité variables ;
- les critères diffèrent selon la stratégie ;
- les estimations donnent souvent une fausse impression de précision ;
- le retour terrain n'est pas structuré ;
- les candidats identifiés ne sont pas reliés à un workflow de qualification.

---

## 5. Hypothèses à valider

| ID | Hypothèse | Méthode de validation | Signal de succès initial |
|---|---|---|---|
| H1 | Les données publiques permettent de mieux classer les candidats qu'un filtre cadastral simple. | Comparaison en aveugle du top 20 avec une baseline. | Précision du top 20 au moins deux fois supérieure à la baseline. |
| H2 | Les professionnels découvrent des candidats qu'ils n'avaient pas identifiés. | Entretiens et revue de listes. | Au moins 30 % du top 20 est nouveau pour le testeur. |
| H3 | L'explication et les sources rendent le score suffisamment crédible. | Tests utilisateurs. | Au moins 80 % des décisions de classement sont comprises. |
| H4 | La plateforme réduit le temps de présélection. | Mesure avant/après sur un territoire identique. | Temps de qualification initiale réduit d'au moins 50 %. |
| H5 | Le résultat justifie un abonnement. | Pilote payant ou lettre d'intention. | Au moins 2 clients pilotes acceptent de payer. |
| H6 | Un indice de vacance apporte un gain incrémental. | Test séparé sur une vérité terrain autorisée. | Gain significatif par rapport au score sans vacance. |

Ces seuils sont des objectifs de validation, pas des performances garanties.

---

## 6. Périmètre

### 6.1 Inclus dans le MVP

- couverture des quatre départements bretons : 22, 29, 35 et 56 ;
- couverture de toutes les communes bretonnes disposant des données critiques minimales ;
- carte interactive et liste synchronisée ;
- recherche par adresse et déplacement sur la carte ;
- parcelles, bâtiments et candidats ;
- stratégies « division/extension » et « rénovation-revente » ;
- filtres métier ;
- score explicable et versionné ;
- confiance, fraîcheur et données manquantes ;
- comparables DVF ;
- contraintes urbanistiques préliminaires ;
- risques principaux ;
- DPE lorsqu'il existe ;
- scénarios financiers modifiables ;
- favoris, statuts, notes et motifs de rejet ;
- collecte structurée des validations professionnelles ;
- administration des imports et de la qualité des données.

### 6.2 Nice to have

- indice expérimental de signaux compatibles avec une vacance ;
- comparaison temporelle d'orthophotos ;
- alertes de nouveaux candidats ou de changement de score ;
- exports CSV/PDF ;
- collaboration en équipe ;
- détection visuelle assistée ;
- intégration CRM.

### 6.3 Hors périmètre initial

- France entière ;
- marketplace ;
- API commerciale publique ;
- base de propriétaires constituée par scraping ;
- prospection automatisée ;
- recommandation d'achat autonome ;
- décision urbanistique opposable ;
- estimation automatisée des désordres intérieurs ;
- prédiction certaine de vente ou de vacance.

---

## 7. Stratégies d'opportunité

Une opportunité n'existe pas indépendamment d'une stratégie. Un même actif peut produire plusieurs snapshots d'opportunité.

### 7.1 Division ou extension

Recherche des propriétés dont la configuration foncière semble laisser une capacité résiduelle.

Signaux possibles :

- surface de terrain ;
- rapport emprise bâtie / surface parcellaire ;
- géométrie et largeur approximative ;
- position du bâti sur la parcelle ;
- accès potentiel à la voie ;
- zonage et premières règles applicables ;
- prescriptions et servitudes connues ;
- voisinage et densité observée ;
- prix local du foncier ou des actifs comparables ;
- risques connus.

Le résultat est un potentiel préliminaire à confirmer par un professionnel compétent.

### 7.2 Rénovation-revente

Recherche des actifs présentant un écart potentiel entre coût total d'acquisition/rénovation et valeur de sortie.

Signaux possibles :

- prix et liquidité du micro-marché ;
- comparables homogènes ;
- ancienneté et caractéristiques du bâti ;
- DPE et éléments énergétiques disponibles ;
- signaux visuels autorisés et suffisamment fiables ;
- surface et typologie ;
- risques ;
- scénario de travaux ;
- durée de portage.

### 7.3 Stratégies futures

- division de lot ;
- démolition-reconstruction ;
- investissement locatif ;
- rénovation énergétique ;
- surélévation ;
- remembrement de parcelles ;
- remise sur le marché de logements vacants pour les collectivités.

---

## 8. Expérience utilisateur

### 8.1 Navigation principale

L'application desktop comporte quatre espaces :

1. **Explorer** : carte et liste des candidats ;
2. **Mes candidats** : favoris et pipeline de qualification ;
3. **Analyses** : comparables et scénarios sauvegardés ;
4. **Paramètres** : territoire, stratégie, hypothèses financières et équipe.

Le MVP est desktop-first. Une version mobile permet au minimum de consulter une fiche, changer un statut et prendre une note sur le terrain.

### 8.2 Carte Explorer

La carte est le cockpit principal.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Recherche     Stratégie      Filtres              Vue carte/liste   Compte │
├───────────────┬───────────────────────────────────────────────┬─────────────┤
│               │                                               │             │
│ Liste triée   │                   Carte                       │ Fiche       │
│ des candidats │                                               │ candidat    │
│               │          parcelles + bâtiments               │ sélectionné │
│ Score         │          + candidats classés                  │             │
│ Confiance     │                                               │ score       │
│ Marge         │                                               │ preuves     │
│ Statut        │                                               │ scénario    │
│               │                                               │ actions     │
└───────────────┴───────────────────────────────────────────────┴─────────────┘
```

#### Comportements

- la carte et la liste partagent le même état de filtres ;
- déplacer la carte actualise la liste, avec une option « Rechercher dans cette zone » ;
- survoler un candidat met en évidence sa parcelle et sa ligne ;
- cliquer ouvre la fiche latérale sans perdre le contexte ;
- le candidat sélectionné et les filtres sont conservés dans l'URL ;
- les résultats sont regroupés à faible zoom et individualisés à fort zoom ;
- les couleurs expriment une classe de score, jamais une certitude de vente ou de vacance ;
- une légende explique la couleur, la confiance et la fraîcheur ;
- les couches lourdes sont désactivées aux niveaux de zoom inadaptés.

#### Couches

- fond de plan clair ;
- orthophoto IGN, à la demande ;
- limites administratives ;
- parcelles cadastrales ;
- bâtiments ;
- candidats d'opportunité ;
- zonage PLU ;
- prescriptions/servitudes disponibles ;
- risques, à la demande ;
- transactions comparables, à la demande.

#### États obligatoires

- chargement initial ;
- mise à jour liée au déplacement ;
- zone non couverte ;
- aucune opportunité ;
- données partielles ;
- source indisponible ;
- résultats périmés ;
- erreur récupérable.

### 8.3 Filtres

Filtres MVP :

- stratégie ;
- score minimum ;
- confiance minimale ;
- surface de parcelle ;
- surface bâtie ;
- rapport d'emprise ;
- estimation d'acquisition ;
- marge centrale ;
- rendement sur coût ;
- classe DPE ou DPE inconnu ;
- zone PLU ;
- niveau de risque ;
- date de dernière transaction disponible ;
- statut utilisateur ;
- données complètes uniquement ;
- candidats déjà examinés ou non.

Un filtre absent ne doit jamais assimiler une donnée inconnue à zéro ou à une réponse négative.

### 8.4 Carte candidat

Une carte compacte dans la liste présente :

- adresse ou localisation ;
- stratégie ;
- score ;
- niveau de confiance ;
- trois principales raisons ;
- fourchette de marge ;
- état de la qualification ;
- date du dernier calcul.

### 8.5 Fiche candidat

Sections :

1. synthèse ;
2. raisons du classement ;
3. parcelles et bâtiments ;
4. marché et transactions ;
5. urbanisme ;
6. risques ;
7. énergie ;
8. observations visuelles ;
9. scénarios financiers ;
10. qualité et sources ;
11. notes et historique.

Chaque donnée importante affiche :

- sa valeur ;
- sa source ;
- sa date ou son millésime ;
- son niveau de qualité ;
- son éventuelle méthode de transformation.

### 8.6 Workflow de qualification

Statuts initiaux :

```text
Nouveau
  ├── À analyser
  │     ├── Retenu
  │     │     ├── Contact à préparer
  │     │     ├── Contacté
  │     │     ├── Visite
  │     │     ├── Offre
  │     │     ├── Acquis
  │     │     └── Perdu
  │     └── Rejeté
  └── Ignoré
```

Motifs de rejet structurés :

- faux positif foncier ;
- urbanisme défavorable ;
- accès impossible ;
- risque trop élevé ;
- estimation trop optimiste ;
- travaux trop importants ;
- déjà connu ;
- hors stratégie ;
- autre, avec commentaire.

---

## 9. Exigences fonctionnelles

| ID | Exigence | Priorité | Critère d'acceptation synthétique |
|---|---|---:|---|
| FR-001 | Rechercher une adresse, commune ou parcelle. | Must | Le résultat correct recentre la carte et affiche les entités liées. |
| FR-002 | Explorer les candidats sur une carte. | Must | Les entités visibles correspondent à l'emprise et aux filtres actifs. |
| FR-003 | Synchroniser carte et liste. | Must | Sélection, survol, tri et filtres restent cohérents. |
| FR-004 | Filtrer et trier les candidats. | Must | Le nombre de résultats et l'URL reflètent les critères. |
| FR-005 | Afficher une fiche candidat complète. | Must | Score, preuves, limites, sources et scénarios sont accessibles. |
| FR-006 | Expliquer chaque score. | Must | Chaque composante possède des contributions positives/négatives sourcées. |
| FR-007 | Distinguer inconnu, non applicable et valeur nulle. | Must | Aucun champ manquant n'est transformé silencieusement en zéro. |
| FR-008 | Modifier les hypothèses financières. | Must | Les résultats sont recalculés sans modifier les données sources. |
| FR-009 | Sauvegarder statut, note et motif de rejet. | Must | L'action est historisée avec auteur et date. |
| FR-010 | Comparer aux transactions DVF pertinentes. | Must | Les critères de comparable et les exclusions sont visibles. |
| FR-011 | Afficher la fraîcheur et la provenance. | Must | Les sources critiques sont disponibles en un clic. |
| FR-012 | Administrer et suivre les imports. | Must | Chaque exécution expose statut, métriques et erreurs. |
| FR-013 | Exporter une sélection. | Should | L'export respecte les filtres et les autorisations. |
| FR-014 | Recevoir une alerte de nouveau candidat. | Should | L'utilisateur contrôle territoire, stratégie et fréquence. |
| FR-015 | Collaborer dans un espace d'équipe. | Should | Les membres partagent statuts et notes selon leurs rôles. |
| FR-016 | Afficher l'indice expérimental de vacance. | Could | Le module est isolé, désactivable et assorti d'avertissements. |

---

## 10. Scoring

### 10.1 Principes

- un score est propre à une stratégie et à une version ;
- il sert à classer, pas à affirmer une probabilité non calibrée ;
- les règles d'éligibilité sont séparées du classement ;
- les signaux corrélés sont regroupés pour éviter le double comptage ;
- les contributions négatives sont visibles ;
- les données manquantes sont visibles et diminuent la confiance ;
- les comparaisons sont normalisées dans un marché local pertinent ;
- aucune modification de poids n'écrase l'historique ;
- les décisions utilisateur ne modifient pas rétroactivement le score affiché.

### 10.2 Pipeline

```text
Sources versionnées
      ↓
Résolution bâtiment/parcelle/adresse
      ↓
Contrôles de qualité
      ↓
Calcul des features
      ↓
Règles d'éligibilité par stratégie
      ↓
Composantes de score
      ↓
Score de classement + confiance
      ↓
Snapshot explicable et immuable
```

### 10.3 Score division/extension V0

| Composante | Poids initial | Features principales |
|---|---:|---|
| Capacité foncière apparente | 40 % | `LAND-001` à `LAND-010`, `BLD-001` à `BLD-003` |
| Faisabilité préliminaire | 25 % | `URB-001` à `URB-004` ; `URB-005` agit sur la confiance |
| Attractivité économique | 25 % | `MKT-001` à `MKT-005`, `FIN-001`, `FIN-002` |
| Risques et complexité | 10 % | `RISK-001` à `RISK-004` |

Répartition initiale à l'intérieur des composantes :

- capacité foncière : surface non bâtie proxy 25 %, emprise relative 20 %, largeur 15 %, distances aux limites 15 %, accès apparent 10 %, compacité 10 %, complexité bâtie 5 % ;
- faisabilité : profil de zone 40 %, emprise résiduelle préliminaire 35 %, contraintes superposées 25 % ;
- attractivité économique : marge et rendement du scénario 50 %, niveau de marché/sortie 25 %, liquidité 15 %, dispersion 10 % ;
- risques : calcul par pénalités plafonnées selon type, intensité, recouvrement et qualité de la donnée.

### 10.4 Score rénovation-revente V0

| Composante | Poids initial | Features principales |
|---|---:|---|
| Économie du scénario | 40 % | `FIN-101` à `FIN-106`, `MKT-101` |
| Besoin/potentiel de rénovation | 25 % | `REN-001` à `REN-007` ; `REN-008` agit sur la confiance |
| Liquidité du marché | 20 % | `MKT-102` à `MKT-105` |
| Risques et complexité | 15 % | `RISK-101`, dispersion de `FIN-102`, contraintes `URB` applicables |

Répartition initiale à l'intérieur des composantes :

- économie : marge nette 50 %, rendement sur coût 30 %, marge de sécurité sur le prix d'achat 20 % ;
- rénovation : énergie observée 40 %, caractéristiques d'enveloppe 25 %, période de construction 20 %, cohérence et complétude bâtimentaire 15 % ;
- liquidité : nombre de comparables 35 %, dispersion 30 %, récence 25 %, tendance locale 10 % ;
- risques/complexité : risques géographiques 60 %, incertitude de travaux 25 %, contraintes urbanistiques pertinentes 15 %.

Les poids initiaux sont des hypothèses configurables. Ils doivent être confrontés à une baseline simple et aux validations professionnelles.

### 10.5 Transformation des features

- les variables continues de marché et de morphologie sont transformées en percentiles dans un segment local comparable ;
- le segment est défini par stratégie, type de bien, zone géographique et, si le volume le permet, classe de surface ;
- les valeurs extrêmes sont contrôlées avant transformation et ne sont jamais supprimées silencieusement ;
- les règles urbanistiques et les risques utilisent des barèmes discrets versionnés ;
- les métriques financières sont comparées aux seuils configurés par l'organisation ;
- chaque transformation déclare son sens attendu, sa plage valide et son comportement hors plage ;
- une relation non monotone utilise une règle par intervalles plutôt qu'un simple percentile ;
- les paramètres exacts sont figés dans `ScoreDefinition` après le profiling stratifié de la Bretagne.

Il serait artificiel de fixer aujourd'hui les seuils absolus de surface, largeur ou prix sans avoir observé leurs distributions et les règles locales. La spec fixe les datasets, les features, les formules et les poids ; le spike données fixe les seuils versionnés.

La Bretagne n'est pas traitée comme un marché homogène. Les normalisations et comparables distinguent au minimum :

- les pôles métropolitains et urbains denses ;
- les villes moyennes ;
- les couronnes périurbaines ;
- les marchés littoraux et touristiques ;
- les territoires ruraux.

Un candidat n'est jamais comparé à l'ensemble de la région lorsque son segment local fournit suffisamment d'observations.

### 10.6 Échelle

- `0–39` : faible priorité ;
- `40–59` : à examiner si la stratégie le justifie ;
- `60–79` : candidat intéressant ;
- `80–100` : priorité élevée.

Cette échelle exprime un rang synthétique. Elle ne signifie jamais « 80 % de chance d'être une opportunité ».

### 10.7 Confiance

La confiance est séparée du score.

Elle dépend de :

- la qualité de l'appariement entre les entités ;
- la couverture des features critiques ;
- la fraîcheur des sources ;
- la cohérence entre sources ;
- la qualité des comparables ;
- la validation historique du modèle pour ce type de bien et cette zone.

Niveaux :

- **Haute** : entités bien appariées, données critiques disponibles et cohérentes ;
- **Moyenne** : une incertitude importante mais résultat encore exploitable ;
- **Faible** : plusieurs données critiques manquent ou se contredisent ;
- **Non publiable** : qualité insuffisante pour classer le candidat.

### 10.8 Explication

Une contribution de score contient au minimum :

```json
{
  "code": "LOW_BUILDING_FOOTPRINT_RATIO",
  "label": "Faible emprise bâtie",
  "direction": "positive",
  "impact": 11.5,
  "value": 0.14,
  "comparison": "percentile_88_local_market",
  "source": "cadastre",
  "source_vintage": "2026-Q2",
  "quality": "high",
  "explanation": "L'emprise bâtie représente environ 14 % de la surface étudiée."
}
```

Le texte généré doit provenir de gabarits contrôlés. Une IA générative ne doit pas inventer d'explication ou de règle d'urbanisme.

### 10.9 Validation du score

Jeux de comparaison :

- échantillon aléatoire ;
- baseline par filtres simples ;
- classement moteur ;
- sélection historique d'un professionnel, si disponible.

Mesures :

- précision à `K` ;
- lift par rapport à la baseline ;
- taux de rejet par motif ;
- accord entre experts ;
- couverture ;
- stabilité du classement ;
- erreur des estimations financières ;
- conversion dans le workflow métier.

Une validation doit être réalisée sur des exemples non utilisés pour ajuster les règles.

---

## 11. Estimation financière

### 11.1 Objectif

Produire un ordre de grandeur transparent et modifiable, pas une valeur unique présentée comme certaine.

### 11.2 Scénarios

- prudent ;
- central ;
- optimiste ;
- personnalisé par l'utilisateur.

### 11.3 Entrées

- prix d'acquisition estimé ou saisi ;
- frais d'acquisition ;
- honoraires ;
- travaux par poste ou enveloppe au m² ;
- études et diagnostics ;
- aléas travaux ;
- financement ;
- durée de portage ;
- charges, assurances et taxes de portage ;
- coût de commercialisation ;
- fiscalité paramétrée par l'utilisateur ;
- valeur de sortie et fourchette.

### 11.4 Sorties

- coût total du projet ;
- marge brute et marge nette paramétrée ;
- rendement sur coût ;
- marge au m² ;
- seuil de prix d'achat ;
- sensibilité au prix de sortie, aux travaux et à la durée ;
- fourchette basse, centrale et haute.

### 11.5 Comparables

Les comparables affichent leurs critères de sélection :

- distance ;
- date ;
- type de bien ;
- surface ;
- terrain ;
- nombre de lots inclus dans la mutation ;
- exclusions et corrections ;
- dispersion statistique.

Une transaction multi-biens ne doit pas être utilisée comme comparable simple sans traitement explicite.

---

## 12. Module expérimental de vacance

### 12.1 Statut

Nice to have, sous feature flag `vacancy.experimental`.

Il ne contribue pas au score principal par défaut. Il apparaît dans une section séparée réservée aux utilisateurs autorisés.

### 12.2 Formulation

Formulation autorisée :

> Plusieurs signaux sont compatibles avec une occupation incertaine. Une vérification est nécessaire.

Formulations interdites :

- « ce logement est vacant » ;
- « cette maison est abandonnée » ;
- « le propriétaire souhaite vendre ».

### 12.3 Signaux envisageables

- observation terrain autorisée et datée ;
- signalement utilisateur qualifié ;
- données fiscales ou LOVAC fournies légalement par un client habilité ;
- incohérences ou changements temporels observables ;
- absence prolongée de transaction uniquement lorsque l'historique est suffisant ;
- indices visuels aériens limités et accompagnés d'une confiance.

L'absence de DPE n'est pas, seule, un signal positif de vacance. Elle signifie principalement « donnée non disponible ».

### 12.4 Sortie

Le module produit un `vacancy_signal_index`, pas une probabilité, tant qu'une calibration sur vérité terrain n'est pas disponible.

Il affiche :

- signaux favorables ;
- signaux contradictoires ;
- données manquantes ;
- date de chaque observation ;
- source et droits d'utilisation ;
- confiance ;
- avertissement de vérification.

### 12.5 Promotion éventuelle dans le produit

Le module ne peut devenir une composante standard que si :

- une base légale et des droits d'usage sont documentés ;
- une vérité terrain suffisamment fiable est disponible ;
- le gain incrémental est démontré hors échantillon ;
- les faux positifs sont acceptables ;
- les formulations et accès ont été validés juridiquement ;
- un mécanisme de contestation/correction existe.

---

## 13. Données

### 13.1 Sources envisagées

| Source | Usage | MVP | Limites principales |
|---|---|---:|---|
| Cadastre/PCI | parcelles, bâtiments, géométrie | Oui | représentation fiscale, appariement nécessaire |
| BAN | adresses et liens spatiaux | Oui | plusieurs adresses ou bâtiments possibles |
| RNB | identifiant bâtiment pérenne et historique | Oui | référentiel encore évolutif, rapprochements à contrôler |
| BDNB Open | socle bâtiment déjà croisé et attributs observés | Oui | agrégation possible au groupe de bâtiments, ne pas confondre données observées et prédites |
| BD TOPO | bâti, hauteur, usage, attributs | Oui | géométrie différente du cadastre, champs incomplets |
| DVF/DVF+ | transactions et comparables | Oui | historique limité, mutations complexes, zones non couvertes |
| DPE ADEME | énergie et caractéristiques déclarées | Oui | parc incomplet et non représentatif |
| Géoportail de l'urbanisme | zonages, prescriptions, règlements | Oui | règles écrites complexes, interprétation non opposable |
| Géorisques | aléas et risques disponibles | Oui | granularité et signification variables |
| OCS GE | couverture et usage du sol | Après contrôle | millésimes et précision à qualifier localement |
| IGN orthophotos | contexte visuel aérien | Should | date, saison, résolution et droits à tracer |
| LOVAC détaillé | validation de vacance | Partenariat seulement | accès et finalités restreints |

### 13.2 Sélection arrêtée des datasets

Le score V0 n'est pas un classifieur entraîné. C'est un moteur de règles et de classement alimenté par des features calculées à partir des datasets ci-dessous.

Chaque dataset reçoit un identifiant stable interne. Une nouvelle version source ne remplace jamais implicitement la précédente : elle crée un nouveau `DatasetRelease` et déclenche une comparaison avant publication.

| ID | Dataset exact | Producteur | Rôle dans le MVP | Utilisé dans le score |
|---|---|---|---|---:|
| DS-01 | Cadastre Etalab consolidé issu du PCI Vecteur | DGFiP / Etalab | géométrie et référence des parcelles, emprise cadastrale du bâti | Oui |
| DS-02 | Référentiel National des Bâtiments, export départemental | RNB | identifiant bâtiment pérenne, géométrie et historique d'identité | Indirectement |
| DS-03 | BDNB Open, dernier millésime validé | CSTB | socle de rapprochement bâtiment/adresse/parcelle et caractéristiques bâtimentaires observées | Oui, champs autorisés seulement |
| DS-04 | BD TOPO, thème Bâti et réseau routier | IGN | morphologie, hauteur/usage disponibles et proximité apparente d'une voie | Oui |
| DS-05 | Base Adresse Nationale, CSV avec identifiants BAN | BAN / IGN | recherche, normalisation, géocodage et rattachement spatial | Non, qualité seulement |
| DS-06 | DVF+ open-data | DGFiP / Cerema | mutations géolocalisées, comparables et métriques de marché | Oui |
| DS-07 | DPE Logements existants depuis juillet 2021 | ADEME | performance énergétique et caractéristiques déclarées | Oui si observé |
| DS-08 | Exports du Géoportail de l'urbanisme au standard CNIG | collectivités / GPU | zonages, prescriptions, servitudes et règlements | Oui |
| DS-09 | API et téléchargements Géorisques | DGPR / BRGM | aléas naturels, technologiques et pollution des sols | Oui |
| DS-10 | OCS GE, millésimes disponibles | IGN | couverture/usage du sol et changements observables | Après validation locale |
| DS-11 | BD ORTHO et millésimes historiques disponibles | IGN | affichage et futures observations visuelles | Non en V0 |
| DS-12 | CandidateReview, dataset interne versionné | Immo Opportunities | labels professionnels et résultats du workflow | Validation, puis apprentissage futur |
| DS-13 | LOVAC détaillé ou vérité terrain équivalente | Cerema / partenaire habilité | validation expérimentale de l'indice de vacance | Jamais dans le score principal V0 |

#### Choix du socle bâtiment

La BDNB Open sert d'accélérateur d'intégration car elle propose déjà un croisement à la maille bâtiment entre plusieurs sources publiques. Le RNB fournit l'identifiant bâtiment à privilégier lorsqu'il est disponible.

Règles :

- conserver les identifiants BDNB, RNB, BD TOPO et cadastraux ;
- ne pas considérer automatiquement un groupe BDNB comme un bâtiment physique unique ;
- recalculer les features critiques à partir de la source primaire lorsqu'elle est disponible ;
- stocker le champ de provenance original de chaque valeur BDNB ;
- exclure du score V0 les prédictions BDNB Expert, les DPE simulés et les prédictions socio-économiques ;
- ne jamais utiliser deux fois la même information via la BDNB et sa source primaire ;
- mesurer manuellement la qualité des liens adresse–bâtiment–parcelle sur l'échantillon pilote.

### 13.3 Catégories d'utilisation

#### Données utilisées directement dans le score V0

- géométries parcellaires et bâties ;
- caractéristiques bâtimentaires observées ;
- transactions DVF+ correctement qualifiées ;
- DPE réellement déposé et correctement apparié ;
- zonage, prescriptions et règles GPU validées ;
- expositions Géorisques à une granularité compatible ;
- hypothèses financières explicites.

#### Données utilisées pour l'identité, la recherche ou la confiance

- BAN ;
- RNB ;
- scores d'appariement ;
- fraîcheur et couverture des datasets ;
- contradictions entre géométries BDNB, BD TOPO et cadastre.

Ces données peuvent réduire la confiance ou empêcher une publication, mais elles ne rendent pas une opportunité économiquement meilleure.

#### Données affichées mais non classifiantes en V0

- orthophotos ;
- documents PLU bruts ;
- couches détaillées de risques ;
- informations non structurées ou non validées.

#### Données expérimentales

- observations visuelles calculées ;
- OCS GE tant que sa contribution n'est pas validée sur un échantillon représentatif de la Bretagne ;
- indice de vacance ;
- signaux ou données fournis par un partenaire sous convention.

### 13.4 Registre des features — division/extension

Les features ci-dessous constituent la liste candidate pour la V0. Leur activation finale dépend de l'audit régional et des validations réalisées dans les quatre départements. Une feature rejetée reste documentée avec son motif.

| ID | Feature | Dataset(s) | Calcul V0 | Usage |
|---|---|---|---|---|
| LAND-001 | `parcel_area_m2` | DS-01 | aire projetée de l'unité analysée | éligibilité et capacité foncière |
| LAND-002 | `building_footprint_m2` | DS-01, DS-03, DS-04 | union des emprises bâties rattachées, après contrôle des doublons | capacité foncière |
| LAND-003 | `footprint_ratio` | LAND-001/002 | emprise bâtie / surface foncière | faible ratio favorable, dans des bornes locales |
| LAND-004 | `unbuilt_area_proxy_m2` | LAND-001/002 | surface foncière moins emprise bâtie | proxy, jamais présenté comme surface constructible |
| LAND-005 | `parcel_compactness` | DS-01 | `4π × aire / périmètre²` | pénalise certaines formes très contraintes |
| LAND-006 | `parcel_width_proxy_m` | DS-01 | largeur de rectangle orienté et coupes géométriques | aide à détecter les parcelles trop étroites |
| LAND-007 | `building_boundary_distance_m` | DS-01/04 | distances minimales du bâti aux limites | espace résiduel et implantation apparente |
| LAND-008 | `road_access_proxy` | DS-01/04 | longueur de limite proche d'une voie publique connue | filtre d'accès apparent, non juridique |
| LAND-009 | `building_count` | DS-01/03/04 | nombre de bâtiments principaux et annexes | complexité et dépendances |
| LAND-010 | `light_construction_ratio` | DS-04 | part d'emprise identifiée comme construction légère | qualification de l'emprise |
| BLD-001 | `building_use` | DS-03/04 | usage observé avec provenance et confiance | éligibilité résidentielle |
| BLD-002 | `building_height_m` | DS-03/04 | hauteur source, sans combler automatiquement les absences | potentiel/complexité |
| BLD-003 | `dwelling_count_observed` | DS-03/04 | nombre de logements disponible et qualifié | exclusion ou ajustement selon stratégie |
| URB-001 | `urban_zone_code` | DS-08 | intersection représentative avec le zonage opposable publié | éligibilité |
| URB-002 | `zone_rule_profile` | DS-08 + table validée | règles structurées et validées par document d'urbanisme breton | faisabilité préliminaire |
| URB-003 | `known_constraint_overlap` | DS-08 | nombre, type et surface des prescriptions/servitudes superposées | pénalité ou revue obligatoire |
| URB-004 | `residual_footprint_proxy_m2` | LAND + URB | estimation géométrique après règles structurées disponibles | capacité préliminaire |
| URB-005 | `urban_rule_completeness` | DS-08 | part des règles nécessaires effectivement structurées | confiance, pas attractivité |
| MKT-001 | `local_land_value_level` | DS-06 | médiane robuste des mutations foncières comparables | attractivité économique |
| MKT-002 | `exit_value_estimate_range` | DS-06 | fourchette issue des comparables filtrés | scénario financier |
| MKT-003 | `comparable_count` | DS-06 | nombre de mutations retenues après exclusions | confiance marché |
| MKT-004 | `market_dispersion` | DS-06 | dispersion robuste des prix normalisés | incertitude/pénalité |
| MKT-005 | `market_liquidity_proxy` | DS-06 | volume récent rapporté au stock observable local | liquidité relative |
| RISK-001 | `clay_exposure_2026` | DS-09 | classe d'exposition RGA 2026 à la parcelle | risque/coût potentiel |
| RISK-002 | `flood_overlap` | DS-09 | intersection avec zonages disponibles et type de zonage | risque/revue |
| RISK-003 | `soil_pollution_proximity` | DS-09 | intersection SIS ou distance aux sites connus | risque/revue |
| RISK-004 | `cavity_proximity` | DS-09 | distance aux cavités recensées, avec couverture connue | risque/revue |
| FIN-001 | `division_scenario_margin_range` | features + hypothèses | valeur de sortie moins acquisition, travaux, frais et portage | score économique |
| FIN-002 | `division_return_on_cost` | features + hypothèses | marge / coût total | score économique |

Précautions :

- `LAND-004` n'est pas une surface libre réellement utilisable ;
- `LAND-008` ne prouve ni une desserte, ni un droit de passage, ni la faisabilité d'un accès ;
- `URB-004` ne doit être calculé que lorsque les règles indispensables ont été structurées et validées ;
- les métriques de marché sont calculées par segments comparables, pas sur toute la commune indistinctement ;
- les risques communaux ne sont pas transformés en exposition parcellaire lorsqu'aucune géométrie fine n'est disponible.

### 13.5 Registre des features — rénovation/revente

| ID | Feature | Dataset(s) | Calcul V0 | Usage |
|---|---|---|---|---|
| REN-001 | `construction_period` | DS-03/04 | période observée ou intervalle, avec provenance | scénario de travaux |
| REN-002 | `building_area_proxy_m2` | DS-03/04 | surface connue ou proxy clairement identifié | normalisation et scénario |
| REN-003 | `building_height_floors_consistency` | DS-03/04 | contrôle hauteur/nombre d'étages lorsqu'ils existent | qualité |
| REN-004 | `energy_label_observed` | DS-07 | étiquette du dernier DPE apparié valide | potentiel énergétique |
| REN-005 | `energy_consumption_observed` | DS-07 | consommation conventionnelle du DPE retenu | potentiel énergétique |
| REN-006 | `dpe_age_months` | DS-07 | âge du diagnostic | confiance/fraîcheur |
| REN-007 | `envelope_characteristics` | DS-07 | murs, fenêtres, isolation et équipements renseignés | aide au scénario, poids limité |
| REN-008 | `dpe_match_confidence` | DS-03/05/07 | confiance du lien DPE–adresse–bâtiment | confiance, jamais attractivité |
| MKT-101 | `comparable_sale_price_m2` | DS-06 | médiane pondérée de comparables retenus | valeur de sortie |
| MKT-102 | `comparable_count` | DS-06 | nombre de comparables utilisables | confiance |
| MKT-103 | `comparable_dispersion` | DS-06 | écart interquartile/MAD des prix | fourchette d'estimation |
| MKT-104 | `transaction_recency` | DS-06 | récence des comparables et éventuelle mutation du candidat | confiance/contexte |
| MKT-105 | `local_price_trend` | DS-06 | tendance robuste uniquement avec historique suffisant | sensibilité, poids limité |
| RISK-101 | `renovation_risk_profile` | DS-09 | synthèse explicable des risques disponibles | aléas travaux/valeur |
| FIN-101 | `purchase_estimate_range` | DS-06 + saisie | fourchette modèle ou valeur utilisateur | scénario |
| FIN-102 | `works_cost_range` | REN + hypothèses | enveloppe par poste ou au m², jamais déduite du seul DPE | scénario |
| FIN-103 | `resale_estimate_range` | MKT + hypothèses | fourchette de sortie | scénario |
| FIN-104 | `net_margin_range` | FIN | revente moins acquisition, travaux, frais, financement et portage | score économique |
| FIN-105 | `return_on_cost` | FIN | marge / coût total | score économique |
| FIN-106 | `break_even_purchase_price` | FIN | prix d'acquisition maximal pour objectif utilisateur | décision |

Règles DPE :

- seuls les DPE réellement déposés sont utilisés en V0 ;
- un DPE simulé ou prédit est exclu ;
- l'absence de DPE produit une contribution neutre et réduit la confiance ;
- plusieurs DPE à une même adresse ne sont pas agrégés sans résolution du bâtiment ou du logement ;
- une classe F/G indique un besoin énergétique potentiel, pas une dégradation physique générale.

### 13.6 Features explicitement interdites en V0

- « pas de mutation depuis 25 ans », faute d'historique national ouvert suffisant ;
- absence de DPE utilisée comme preuve de vacance ou de dégradation ;
- âge, nom, coordonnées ou catégorie supposée du propriétaire ;
- variables socio-économiques individuelles ou prédictions de ménage ;
- données scrapées depuis des annonces ou annuaires ;
- DPE ou prix simulés issus d'un fournisseur tiers sans modèle et provenance séparés ;
- texte PLU interprété automatiquement sans contrôle du document et de la zone concernés ;
- observation visuelle non validée présentée comme un fait ;
- données créées après la date du snapshot dans un backtest.

### 13.7 Politique des données manquantes

Chaque feature est déclarée `required`, `optional` ou `confidence_only` pour une stratégie.

- une feature requise absente empêche la publication du score concerné ;
- une feature optionnelle absente produit une contribution neutre, pas une contribution négative ;
- l'absence diminue le taux de couverture et potentiellement la confiance ;
- aucun poids n'est redistribué silencieusement vers les features restantes ;
- la fiche expose la liste des features manquantes ;
- les candidats de niveaux de couverture très différents ne sont pas comparés sans avertissement.

Features requises initiales pour division/extension :

- géométrie parcellaire valide ;
- emprise bâtie résolue ;
- zonage GPU disponible ;
- profil de règles minimal validé ;
- données de marché suffisantes ou scénario utilisateur explicite.

Features requises initiales pour rénovation/revente :

- unité bâtiment/parcelle suffisamment résolue ;
- usage résidentiel probable avec source ;
- surface exploitable ou proxy accepté ;
- données de marché suffisantes ;
- scénario financier complet.

Le DPE n'est pas requis.

### 13.8 Construction du dataset interne de validation

`CandidateReview` est un dataset produit par l'usage du logiciel, distinct des données sources.

Chaque observation contient :

```text
review_id
property_unit_id
strategy_id
opportunity_snapshot_id
reviewer_id pseudonymisé
reviewer_profile
reviewed_at
decision
rejection_reasons[]
confidence_of_review
field_visit_performed
contact_attempted
offer_made
acquisition_outcome
observed_margin, si connue et autorisée
```

Labels successifs :

1. `worth_deeper_analysis` — label primaire du MVP ;
2. `worth_contacting` ;
3. `visit_requested` ;
4. `offer_made` ;
5. `acquired` ;
6. résultat économique observé.

Le premier label est disponible rapidement mais reste subjectif. Les labels d'offre, d'acquisition et de marge sont plus proches de la valeur métier, mais plus rares et retardés.

Règles de constitution :

- guide d'annotation commun ;
- échantillons mélangeant top score, baseline et aléatoire ;
- évaluateur aveugle à la méthode de sélection lorsque possible ;
- double évaluation d'un sous-échantillon ;
- conservation des désaccords ;
- séparation temporelle et géographique entre apprentissage et validation ;
- prévention des fuites de données, notamment transactions postérieures au snapshot ;
- possibilité de retirer ou corriger une annotation sans réécrire l'historique.

Un futur modèle supervisé aura une cible distincte par stratégie. Il ne devra pas apprendre un label générique mélangeant division, rénovation, vacance et intention de vente.

### 13.9 Matrice dataset → composantes

| Dataset | Capacité foncière | Urbanisme | Marché/finance | Rénovation | Risques | Confiance | Vacance exp. |
|---|---:|---:|---:|---:|---:|---:|---:|
| DS-01 Cadastre | Principal | Support spatial | Support | Support | Support spatial | Oui | Non |
| DS-02 RNB | Non | Non | Non | Non | Non | Principal | Non |
| DS-03 BDNB Open | Secondaire | Support | Non | Principal | Support | Principal | Non |
| DS-04 BD TOPO | Principal | Support | Non | Secondaire | Support spatial | Oui | Non |
| DS-05 BAN | Non | Non | Non | Non | Non | Principal | Non |
| DS-06 DVF+ | Non | Non | Principal | Support marché | Non | Oui | Très limité |
| DS-07 DPE | Non | Non | Support | Principal énergie | Non | Oui | Non |
| DS-08 GPU | Support | Principal | Support | Support | Support | Oui | Non |
| DS-09 Géorisques | Support | Support | Support | Support | Principal | Oui | Non |
| DS-10 OCS GE | Expérimental | Support | Non | Non | Support | Oui | Expérimental |
| DS-11 BD ORTHO | Non en V0 | Affichage | Non | Affichage | Affichage | Non | Expérimental |
| DS-12 Reviews | Validation | Validation | Validation | Validation | Validation | Non | Validation |
| DS-13 LOVAC | Non | Non | Non | Non | Non | Non | Validation uniquement |

### 13.10 Critères d'acceptation d'un dataset

Un dataset ne peut alimenter le score de production que si :

- sa licence et ses conditions de réutilisation sont enregistrées ;
- la ressource est téléchargeable ou interrogeable de façon reproductible ;
- son millésime est identifiable ;
- son schéma est versionné ;
- sa couverture est mesurée pour chaque département, EPCI et commune de Bretagne ;
- les champs retenus possèdent une définition documentée ;
- les distributions et valeurs aberrantes sont analysées ;
- la méthode d'appariement est évaluée sur échantillon ;
- l'effet de la feature sur le classement est explicable ;
- sa suppression peut être simulée par un test d'ablation ;
- une règle de fraîcheur et de repli existe.

### 13.11 Contrat de source

Chaque source possède :

- propriétaire/producteur ;
- URL et licence ;
- version ou millésime ;
- couverture géographique ;
- fréquence théorique et fréquence observée ;
- schéma attendu ;
- checksum des fichiers ;
- date d'import ;
- contrôles qualité ;
- transformations ;
- politique de rétention ;
- conditions d'utilisation et d'affichage.

### 13.12 Règles de qualité

- conserver une copie brute immuable de chaque livraison ;
- ne jamais modifier silencieusement une valeur source ;
- versionner les transformations ;
- mesurer la couverture par commune et par champ critique ;
- mettre en quarantaine les enregistrements invalides ;
- détecter les changements de schéma ;
- rendre chaque feature traçable jusqu'à la source ;
- séparer absence, nullité, non-applicabilité et erreur ;
- publier un candidat seulement si les contrôles minimaux passent.

### 13.13 Résolution des entités

L'appariement relie :

```text
Adresse ↔ Parcelle ↔ Bâtiment ↔ Local/logement ↔ Transaction ↔ DPE
```

Il combine :

- identifiants stables lorsqu'ils existent ;
- relations officielles ;
- intersections géographiques ;
- proximité ;
- normalisation d'adresse ;
- cohérence temporelle ;
- règles propres aux mutations multi-parcelles.

Chaque lien possède une méthode, un score de confiance et une version. Les appariements ambigus sont conservés comme tels et peuvent empêcher la publication du score.

---

## 14. Modèle de données conceptuel

### 14.1 Référentiel

```text
Area
Address
Parcel
Building
BuildingParcel
PropertyUnit
PropertyUnitMember
```

`PropertyUnit` représente l'unité analysée par le moteur. Elle peut contenir plusieurs parcelles et bâtiments selon la stratégie et les données disponibles.

### 14.2 Sources et ingestion

```text
DataSource
DatasetRelease
ImportRun
RawAsset
TransformationRun
DataQualityCheck
EntityMatch
```

### 14.3 Données métier

```text
Transaction
TransactionProperty
EnergyAssessment
UrbanDocument
UrbanZone
UrbanConstraint
RiskObservation
ImageryAsset
VisualObservation
MarketArea
MarketMetric
```

### 14.4 Scoring

```text
Strategy
FeatureDefinition
FeatureValue
ScoreDefinition
OpportunitySnapshot
ScoreComponent
ScoreEvidence
EstimateScenario
```

### 14.5 Utilisateurs

```text
Organization
User
Role
CandidateReview
CandidateStatusHistory
SavedSearch
Alert
Note
Document
```

### 14.6 Contraintes essentielles

- un `OpportunitySnapshot` est immuable ;
- il référence une stratégie, une définition de score et un instant de calcul ;
- un recalcul crée un nouveau snapshot ;
- les annotations utilisateur ne réécrivent pas les données sources ;
- les données propres à une organisation sont isolées ;
- les sources et preuves restent consultables après un changement de score.

---

## 15. API

API REST versionnée sous `/api/v1`.

### 15.1 Lecture

```text
GET /areas
GET /search
GET /parcels/{id}
GET /buildings/{id}
GET /property-units/{id}
GET /opportunities
GET /opportunities/{id}
GET /opportunities/{id}/history
GET /opportunities/{id}/evidence
GET /opportunities/{id}/comparables
GET /opportunities/{id}/sources
GET /score-definitions/{id}
GET /tiles/v1/opportunities/{z}/{x}/{y}.mvt
GET /tiles/v1/parcels/{z}/{x}/{y}.mvt
```

Les routes `/tiles` sont exposées par le même gateway mais servies par Martin, pas par les processus FastAPI.

### 15.2 Actions

```text
POST  /opportunities/{id}/reviews
PATCH /opportunities/{id}/status
POST  /opportunities/{id}/notes
POST  /opportunities/{id}/scenarios
POST  /saved-searches
POST  /exports
```

### 15.3 Administration

```text
GET  /admin/import-runs
GET  /admin/import-runs/{id}
GET  /admin/data-quality
POST /admin/recompute
```

### 15.4 Principes

- pagination par curseur pour les grandes listes ;
- filtres validés et bornés ;
- erreurs structurées ;
- identifiant de requête ;
- contrôle d'accès par organisation et rôle ;
- journalisation des exports et consultations sensibles ;
- cache cohérent avec la version des données ;
- documentation OpenAPI générée.

---

## 16. Architecture

L'architecture de référence, les décisions ADR, les rôles des services et la séquence d'implémentation sont définis dans [ARCHITECTURE.md](./ARCHITECTURE.md).

Le produit repose sur un monolithe modulaire. Les services séparés répondent uniquement à des contraintes techniques spécifiques : frontend, API, tuiles, pipelines et tâches applicatives.

```text
Sources publiques
      ↓
MinIO S3 brut et versionné, dans Docker
      ↓
Dagster : import, normalisation, features, scoring
      ↓
PostgreSQL + PostGIS
      ↓
Snapshots publiés + vues de tuiles
      ↓
FastAPI ───────────── Martin / MVT
      ↓                         ↓
React / TypeScript / MapLibre
```

### 16.1 Frontend

- React ;
- TypeScript strict ;
- Vite ;
- MapLibre GL JS ;
- `react-map-gl/maplibre` ;
- TanStack Query ;
- MUI ;
- React Router ;
- React Hook Form + Zod ;
- état des filtres dans l'URL ;
- tests unitaires et tests de parcours critiques.

### 16.2 Backend

- FastAPI ;
- Pydantic ;
- SQLAlchemy 2 + GeoAlchemy2 + psycopg 3 ;
- Alembic ;
- PostgreSQL 15 + PostGIS 3.x ;
- Dagster pour les imports et recalculs régionaux ;
- Redis pour cache et file applicative ;
- Celery uniquement pour exports, alertes et tâches déclenchées par les utilisateurs ;
- MinIO compatible S3 pour sources, documents et images ;
- Martin pour les tuiles MVT depuis PostGIS ou PMTiles ;
- Keycloak pour l'identité OIDC ;
- Caddy pour TLS et routage.

Le scoring régional est pré-calculé. Les déplacements de carte ne déclenchent jamais de recalcul du moteur.

### 16.3 Environnements

- local ;
- test/CI ;
- staging avec sous-ensemble représentatif ;
- production Bretagne sur serveur Ubuntu 24.04 LTS, entièrement conteneurisée ;
- déploiement sur VPS Ubuntu 24.04 LTS générique via GitHub Actions et Ansible.

Les données personnelles ou sous accès restreint ne sont jamais copiées dans les environnements de développement sans anonymisation et autorisation.

Tous les workloads s'exécutent dans Docker Compose, y compris PostgreSQL/PostGIS, Redis, MinIO, Keycloak, Dagster et l'observabilité. Chaque service ou processus long possède son propre conteneur : aucune image omnibus ne regroupe plusieurs démons. Dagster webserver/daemon/code, Celery worker/beat et chaque composant d'observabilité sont eux aussi séparés. Le VPS et le DNS sont créés chez le fournisseur choisi ; GitHub Actions pilote Ansible par SSH pour préparer l'OS et déployer Compose. La toolchain Ansible/SOPS est elle-même fournie par une image Docker versionnée. Le contrat détaillé de reconstruction sur serveur vierge est défini dans [DEPLOYMENT.md](./DEPLOYMENT.md).

### 16.4 Observabilité

- logs structurés ;
- métriques API et workers ;
- traces sur les parcours critiques ;
- suivi des imports et de leur durée ;
- alertes de fraîcheur ;
- taux d'erreur d'appariement ;
- couverture des features ;
- version de données visible dans l'interface.

---

## 17. Exigences non fonctionnelles

### 17.1 Performance cible MVP

- affichage initial de l'Explorer en moins de 3 secondes au p75 sur une connexion fixe standard ;
- interaction cartographique fluide avec regroupement et tuiles vectorielles ;
- réponse API p95 inférieure à 500 ms pour une liste mise en cache ;
- fiche candidat p95 inférieure à 1 seconde hors médias lourds ;
- recalcul financier interactif inférieur à 300 ms côté client ou API.

### 17.2 Disponibilité et reprise

- objectif opérationnel V1 : 99,5 % mensuel hors maintenance annoncée, non contractuel tant que la production reste sur un serveur unique ;
- archivage WAL continu et base backup quotidienne de PostgreSQL vers une cible hors site ;
- versioning et réplication hors site des objets MinIO durables ;
- RPO cible PostgreSQL inférieur ou égal à 15 minutes ;
- RTO cible inférieur ou égal à 4 heures après validation du runbook ;
- restauration sur serveur vierge testée au moins trimestriellement ;
- imports relançables sans duplication ;
- publication atomique d'un nouveau millésime.

### 17.3 Sécurité

- chiffrement TLS ;
- chiffrement des sauvegardes et secrets ;
- authentification centralisée ;
- rôles organisationnels ;
- principe du moindre privilège ;
- journal d'audit ;
- protection contre l'extraction massive non autorisée ;
- limitation de débit ;
- validation stricte des fichiers et entrées ;
- revue des dépendances.

### 17.4 Accessibilité

- cible WCAG 2.1 AA pour les fonctions principales ;
- toute information portée par une couleur possède un équivalent textuel ;
- la liste permet d'utiliser les fonctions essentielles sans interaction directe avec la carte ;
- navigation clavier des principaux contrôles.

---

## 18. Confidentialité, conformité et usage responsable

### 18.1 Principes

- protection des données dès la conception ;
- finalités documentées ;
- minimisation ;
- durée de conservation définie ;
- gestion des droits et oppositions ;
- accès sensibles journalisés ;
- séparation stricte entre données ouvertes et données restreintes ;
- vérification des licences et conditions de réutilisation ;
- absence de scraping de coordonnées sans analyse et autorisation explicites.

### 18.2 Prospection

Le MVP organise la qualification des candidats mais n'automatise pas le contact de particuliers.

Toute future fonction de prospection devra définir :

- origine et licéité des coordonnées ;
- base légale ;
- information des personnes ;
- consentement lorsqu'il est requis ;
- gestion des oppositions et listes repoussoirs ;
- règles propres au canal utilisé ;
- preuves et historique de conformité.

### 18.3 Présentation des résultats

- aucune étiquette publique « vacant », « abandonné » ou « propriétaire vendeur » ;
- aucune diffusion publique d'une liste de biens suspects ;
- vocabulaire probabiliste uniquement si le modèle est effectivement calibré ;
- avertissement visible pour les informations urbanistiques et financières ;
- correction possible des observations utilisateur ;
- accès au module de vacance restreint et audité.

Une revue spécialisée RGPD, prospection et droit immobilier est requise avant un pilote impliquant des coordonnées de personnes ou des données à accès restreint.

---

## 19. Administration interne

L'équipe doit pouvoir :

- consulter les millésimes disponibles ;
- lancer ou relancer un import ;
- voir les erreurs de schéma ;
- comparer deux imports ;
- voir la couverture par commune ;
- inspecter un appariement ;
- publier ou retirer un snapshot ;
- activer une version de score ;
- lancer un backtest ;
- auditer les exports ;
- gérer les feature flags ;
- désactiver une source défectueuse sans perdre son historique.

---

## 20. Mesures de succès

### 20.1 North star metric

**Nombre de candidats qualifiés « à approfondir » par heure de travail utilisateur.**

Cette mesure combine la qualité du classement et le gain de temps.

### 20.2 Produit

- comptes actifs hebdomadaires ;
- candidats examinés par session ;
- taux de candidats sauvegardés ;
- délai jusqu'à la première valeur ;
- recherches sauvegardées ;
- rétention à 4 et 12 semaines ;
- conversion du pilote en offre payante.

### 20.3 Données et scoring

- couverture par source, département, EPCI et commune ;
- couverture publiable dans chacun des quatre départements ;
- taux d'appariements certains/ambigus ;
- précision au top 10/20/50 ;
- précision par segment de marché breton ;
- lift contre baseline ;
- taux de faux positifs ;
- stabilité du classement ;
- erreur des estimations ;
- proportion de scores à confiance faible ;
- fraîcheur réelle des données.

### 20.4 Workflow métier

- taux `Nouveau → À analyser` ;
- taux `À analyser → Retenu` ;
- taux de rejet par motif ;
- candidats menant à un contact, une visite ou une offre ;
- opportunités acquises et marge observée, lorsque connue.

---

## 21. Plan de validation et roadmap

Le suivi opérationnel est découpé en versions verticales dans [`docs/versions/`](./docs/versions/README.md). Ces fichiers organisent l’exécution et les preuves de livraison ; la présente spécification reste la source de vérité produit.

### Phase 0 — Ingestion Bretagne et audit stratifié

Objectifs :

- importer pour les quatre départements bretons les releases retenues de Cadastre, RNB, BDNB Open, BD TOPO, BAN, DVF+, DPE, GPU et Géorisques ;
- produire le rapport d'acceptation de chacun des datasets DS-01 à DS-09 ;
- mesurer la couverture par département, EPCI et commune ;
- construire les appariements ;
- produire une table auditable des parcelles/bâtiments ;
- calculer et profiler chaque feature LAND, BLD, URB, MKT, RISK, REN et FIN ;
- tester les tuiles et performances de la carte ;
- auditer un échantillon de communes urbaines, périurbaines, littorales et rurales dans chaque département ;
- identifier les différences territoriales avant de finaliser les scores.

Critère de sortie : rapport régional de qualité, couverture cartographique de la Bretagne et décision explicite sur les features utilisables par territoire.

### Phase 1 — Prototype de scoring breton hors interface

- stratégies division/extension et rénovation-revente ;
- baseline simple ;
- première version des features ;
- segmentation des marchés locaux bretons ;
- revue en aveugle par des professionnels dans les quatre départements ;
- ajustement des règles sans utiliser le jeu final de validation.

Critère de sortie : lift mesurable contre baseline au niveau régional, absence de dégradation critique dans un département ou segment et motifs d'erreur documentés.

### Phase 2 — MVP cartographique Bretagne

- Explorer carte/liste ;
- navigation sur l'ensemble de la Bretagne ;
- filtres département, EPCI et commune ;
- filtres ;
- fiche candidat ;
- preuves et sources ;
- comparables ;
- scénarios ;
- workflow de qualification ;
- administration minimale.

Critère de sortie : des professionnels couvrant plusieurs marchés bretons testent le produit sur des cas réels et au moins deux acceptent un pilote payant ou un engagement équivalent.

### Phase 3 — Consolidation régionale

- correction des écarts de couverture entre départements et communes ;
- amélioration des segmentations locales ;
- mesure continue de généralisation des scores ;
- alertes ;
- collaboration ;
- amélioration des comparables ;
- durcissement sécurité et exploitation.

Critère de sortie : performances conservées sur les principaux segments bretons et rétention utilisateur démontrée.

### Phase 4 — Expérimentations

- indice de vacance sous feature flag ;
- orthophotos temporelles ;
- signaux visuels ;
- nouveaux types de stratégie ;
- intégrations CRM.

Chaque expérimentation possède sa propre baseline, son dataset de validation et une décision `promouvoir / maintenir expérimental / abandonner`.

### Phase 5 — Extension géographique

L'expansion au-delà de la Bretagne n'est lancée qu'après validation :

- du marché ;
- du score ;
- de la qualité des données ;
- de l'économie d'infrastructure ;
- de la capacité d'exploitation ;
- des différences territoriales et réglementaires.

---

## 22. Monétisation à tester

Hypothèse initiale :

| Offre | Cible | Contenu indicatif | Prix hypothétique |
|---|---|---|---:|
| Solo | indépendant | 1 utilisateur, territoire limité, favoris et scénarios | 79 €/mois |
| Pro | petite équipe | collaboration, alertes et exports | 249 €/mois |
| Entreprise | réseau/équipe étendue | territoires multiples, gouvernance, intégrations | sur devis |

Ces prix ne font pas partie des acquis de la spec. Ils doivent être validés avec des pilotes payants.

Les limites d'offre peuvent porter sur :

- utilisateurs ;
- territoires ;
- alertes ;
- exports ;
- intégrations ;
- historique ;
- support.

Le produit ne doit pas limiter artificiellement l'accès aux preuves et à la confiance : ces éléments sont nécessaires à un usage responsable du score.

---

## 23. Risques

| Risque | Impact | Réponse |
|---|---:|---|
| Les données ne prédisent pas mieux qu'un filtre simple. | Critique | Baseline et validation avant interface complète. |
| Trop de faux positifs. | Élevé | Règles d'éligibilité, confiance, feedback structuré. |
| Appariements incorrects. | Critique | Scores de match, contrôles, blocage des cas ambigus. |
| Urbanisme surinterprété. | Élevé | Potentiel préliminaire, preuves et avertissements. |
| Estimations trop précises. | Élevé | Fourchettes, scénarios, sensibilité. |
| Absence de signal d'intention de vente. | Élevé | Promesse « candidats », pas « futures ventes ». |
| Données restreintes ou réutilisation illicite. | Critique | Inventaire des droits, minimisation, revue juridique. |
| Carte lente à grande échelle. | Moyen | Tuiles vectorielles, agrégation, cache, tests de charge. |
| Feedback utilisateur biaisé. | Moyen | Guide d'annotation, échantillonnage, accord inter-évaluateurs. |
| Même lead vendu à trop d'utilisateurs. | Moyen | Étudier territoires, fraîcheur et différenciation, sans promettre d'exclusivité. |
| Coûts de couverture nationale. | Élevé | Expansion par gates, import incrémental, mesure des coûts. |

---

## 24. Décisions prises

- la carte est l'interface principale, mais chaque fonction essentielle existe aussi dans la liste ;
- le MVP vise un utilisateur et deux stratégies proches ;
- le score dépend d'une stratégie ;
- score et confiance sont séparés ;
- l'opportunité est un snapshot versionné ;
- la vacance est expérimentale et extérieure au score principal ;
- l'absence de DPE n'est pas une preuve de vacance ;
- le produit détecte des candidats off-market, pas une intention de vente ;
- le workflow de qualification fait partie du MVP ;
- aucune donnée de propriétaire n'est requise pour prouver la valeur initiale ;
- la France entière dépend de critères de passage explicites.

---

## 25. Questions encore ouvertes

Ces questions n'empêchent pas le spike données :

- Quel rayon d'activité et quel volume hebdomadaire cible le premier marchand de biens ?
- Quelle stratégie doit être prioritaire entre division/extension et rénovation-revente ?
- Quelles hypothèses financières doivent être configurées par organisation ?
- Quel niveau de détail urbanistique est acceptable au MVP ?
- Quelle méthode terrain permettra de constituer le jeu de validation ?
- Quel partenaire pourrait fournir légalement une vérité terrain de vacance ?
- Les candidats sont-ils partagés entre clients ou différenciés par territoire/stratégie ?
- Quel niveau de mobilité est nécessaire pendant une visite ?

---

## 26. Definition of Done du MVP

Le MVP est terminé lorsque :

- les sources critiques des quatre départements bretons sont importées, versionnées et auditées ;
- chacun des datasets DS-01 à DS-09 possède un rapport `accepté / affichage seulement / rejeté` ;
- chaque feature activée possède un mapping source, une formule testée et une règle de valeur manquante ;
- la couverture et les limites sont documentées par département, EPCI et commune ;
- la carte couvre toute la Bretagne et signale explicitement les zones non publiables ;
- la résolution des entités possède des métriques mesurées ;
- les deux scores sont reproductibles, versionnés et explicables ;
- une baseline permet de mesurer leur valeur ;
- les performances sont mesurées séparément sur les segments urbains, périurbains, littoraux et ruraux ;
- la carte, la liste et la fiche sont synchronisées ;
- les scénarios financiers sont transparents et modifiables ;
- un utilisateur peut qualifier un candidat de bout en bout ;
- les données inconnues et les avertissements sont visibles ;
- les parcours critiques sont testés ;
- sauvegarde, sécurité minimale et observabilité sont opérationnelles ;
- la stack complète a été redéployée par GitHub Actions/Ansible et restaurée sur un VPS vierge ;
- trois professionnels ont utilisé le produit sur des cas réels ;
- une décision documentée `poursuivre / pivoter / arrêter` est prise sur les résultats.

---

## 27. Références de données et conformité

- Cadastre Etalab/PCI : <https://cadastre.data.gouv.fr/datasets>
- Référentiel National des Bâtiments : <https://www.data.gouv.fr/datasets/referentiel-national-des-batiments>
- BDNB Open : <https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments>
- Dictionnaire et modèle BDNB : <https://bdnb.io/documentation/modele_donnees/>
- BD TOPO : <https://geoservices.ign.fr/bdtopo>
- Base Adresse Nationale : <https://adresse.data.gouv.fr/outils/telechargements>
- DVF+ open-data : <https://www.data.gouv.fr/datasets/dvf-open-data>
- DVF brute et limites de couverture : <https://cadastre.data.gouv.fr/dvf>
- DPE ADEME : <https://data.ademe.fr/datasets/meg-83tjwtg8dyz4vv7h1dqe>
- Géoportail de l'urbanisme : <https://www.geoportail-urbanisme.gouv.fr/>
- API Géoportail de l'urbanisme : <https://www.geoportail-urbanisme.gouv.fr/api/>
- Standard CNIG PLU : <https://cnig.gouv.fr/geostandard-plan-local-d-urbanisme-plu-a28539.html>
- API Géorisques : <https://www.georisques.gouv.fr/doc-api>
- Bases de données Géorisques : <https://www.georisques.gouv.fr/donnees/bases-de-donnees>
- OCS GE : <https://www.data.gouv.fr/datasets/ocs-ge>
- BD ORTHO : <https://geoservices.ign.fr/bdortho>
- Documentation Datafoncier/LOVAC : <https://doc-datafoncier.cerema.fr/doc/fiche_descriptive/lovac>
- Recommandations CNIL sur les données publiées en ligne : <https://www.cnil.fr/fr/recommandations-reutilisateurs-donnees-internet>
- Prospection commerciale, CNIL : <https://www.cnil.fr/fr/la-prospection-commerciale>

---

## 28. Glossaire

**Actif ou unité analysée** : regroupement logique de parcelles et bâtiments utilisé pour une stratégie.  
**Baseline** : méthode simple servant de comparaison au moteur.  
**Candidat** : actif méritant potentiellement une analyse ; ce terme n'implique ni vente ni vacance.  
**Confiance** : qualité estimée des données et du résultat, distincte du score.  
**Feature** : variable calculée à partir d'une ou plusieurs sources.  
**Off-market** : non identifié dans le flux d'annonces observé ; ne signifie pas que le propriétaire souhaite vendre.  
**OpportunitySnapshot** : résultat immuable d'un calcul pour un actif, une stratégie, une date et une version.  
**Précision à K** : part des `K` premiers candidats jugés effectivement pertinents selon le protocole.  
**Score** : indice relatif servant au classement pour une stratégie.  
**Vérité terrain** : observation ou résultat indépendant utilisé pour valider le moteur.
