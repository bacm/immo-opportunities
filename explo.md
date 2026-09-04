# Plateforme de détection d'opportunités immobilières

## Vision

Créer une plateforme capable d'identifier automatiquement les biens immobiliers présentant un fort potentiel d'investissement avant qu'ils n'arrivent sur le marché.

L'objectif n'est **pas** de construire un simple équivalent d'Immocarto.

L'objectif est de développer un moteur d'intelligence capable de répondre à la question suivante :

> Quels sont les biens ayant la plus forte probabilité d'être vacants, dégradés, sous-exploités ou offrant un fort potentiel de valorisation ?

---

# Proposition de valeur

Pour chaque bâtiment, la plateforme produit :

- un score d'opportunité
- une explication détaillée du score
- une estimation financière
- une analyse urbanistique
- une analyse des risques
- une analyse visuelle
- un potentiel de rénovation
- un potentiel foncier
- un suivi de prospection

L'utilisateur ne cherche plus des maisons.

Il cherche des **opportunités**.

---

# Les utilisateurs

- marchands de biens
- investisseurs
- chasseurs immobiliers
- agences
- promoteurs
- collectivités
- aménageurs

---

# Fonctionnement général

```
Sources publiques
        │
        ▼
Import automatique
        │
        ▼
Normalisation
        │
        ▼
Croisement des données
        │
        ▼
Analyse IA
        │
        ▼
Calcul des scores
        │
        ▼
Carte interactive
        │
        ▼
Prospection
```

---

# Les données

## Cadastre

- parcelles
- bâtiments
- sections
- références cadastrales

Utilisation :

- géométrie
- emprise
- superficie

---

## BAN

Base Adresse Nationale

Utilisation :

- géocodage
- normalisation

---

## DVF

Demandes de Valeurs Foncières

Utilisation

- historique des ventes
- prix
- comparaison
- estimation

---

## DPE

Utilisation

- classe énergétique
- ancienneté
- consommation

---

## Géorisques

Utilisation

- argiles
- inondation
- radon
- cavités
- pollution

---

## PLU

Utilisation

- zonage
- constructibilité
- hauteur
- emprise
- servitudes

---

## IGN

Orthophotos

Utilisation

- analyse visuelle
- comparaison temporelle
- computer vision

---

## BD TOPO

Utilisation

- nature des bâtiments
- hauteur
- occupation

---

## INSEE

Utilisation

- données socio-économiques

---

# Architecture technique

```
React
MapLibre

↓

API Python

↓

PostgreSQL + PostGIS

↓

Workers

↓

Stockage
```

---

## Front

- React
- Typescript
- React Query
- MUI
- MapLibre

---

## API

- APIFlask (ou FastAPI)
- SQLAlchemy
- Pydantic

---

## Base

PostgreSQL

Extension

PostGIS

---

## Workers

- Celery
- Redis

Ils réalisent

- imports
- calculs
- analyses
- IA

---

## Computer Vision

Plus tard

- PyTorch
- segmentation
- classification

---

# Pourquoi MapLibre ?

Google Maps coûte cher.

MapLibre permet

- les couches IGN
- OpenStreetMap
- cadastre
- personnalisation

Google Street View peut simplement être ouvert via un lien.

---

# Modèle de données

```
Area

Address

Parcel

Building

BuildingParcel

Transaction

DPE

Risk

UrbanRule

Orthophoto

VisualObservation

Opportunity

OpportunityScore

ScoreExplanation

UserReview

Project

Contact

Document
```

---

# Entité principale

```python
Opportunity

id

parcel

building

strategy

degradation_score

vacancy_score

financial_score

land_score

overall_score

estimated_purchase

estimated_renovation

estimated_resale

estimated_margin

confidence
```

---

# Les scores

L'application ne possède pas un score.

Elle possède plusieurs scores.

---

# Score dégradation

Exemple

```
Toiture abîmée                +20

Végétation envahissante       +15

Ouvertures condamnées         +10

Terrain en friche             +10

Dépendances dégradées         +10

Différences sur orthophotos   +10

DPE F ou G                    +10

Pas de mutation depuis 25 ans  +5

Bâtiment ancien                +5
```

---

# Score vacance

Exemple

```
Pas de mutation récente

Pas de DPE récent

Maison peu entretenue

Terrain envahi

Indices visuels

Signalement utilisateur

Historique
```

Important

Il ne faut jamais dire

> Cette maison est abandonnée.

Mais

> Cette maison présente plusieurs indices compatibles avec une vacance.

---

# Score foncier

```
Grande parcelle

Possibilité de division

Extension possible

Zone tendue

Faible risque

Bonne desserte

Fort potentiel
```

---

# Score financier

Calcul

```
Valeur après travaux

-

Prix d'achat estimé

-

Travaux

-

Frais

-

Fiscalité

-

Financement

=

Marge
```

---

# Score global

```
20 %

Dégradation

+

20 %

Vacance

+

25 %

Potentiel foncier

+

35 %

Rentabilité
```

---

# Explicabilité

Chaque score doit être justifié.

Exemple

```json
{
  "score": 81,
  "reasons": [
    {
      "code": "OLD_TRANSACTION",
      "impact": 8
    },
    {
      "code": "VEGETATION",
      "impact": 12
    }
  ]
}
```

L'utilisateur comprend immédiatement pourquoi le score est élevé.

---

# Carte

La carte affiche

- satellite
- cadastre
- bâtiments
- parcelles
- opportunités

---

# Les filtres

Prix

Surface

Surface terrain

Date de vente

Classe DPE

Zone PLU

Commune

Score

Potentiel

Budget

Rendement

---

# Fiche bien

## Général

Adresse

Parcelle

Bâtiment

Surface

---

## Historique

DVF

Comparables

Prix

---

## Urbanisme

PLU

Servitudes

Division

Extension

---

## Risques

Argiles

Inondation

Pollution

---

## DPE

Classe

Date

Consommation

---

## Analyse visuelle

Toiture

Terrain

Végétation

Piscine

Dépendances

---

## Estimation

Prix achat

Travaux

Valeur finale

Marge

---

# Pipeline

```
Téléchargement

↓

Import

↓

Nettoyage

↓

Normalisation

↓

Croisement

↓

Analyse

↓

Scoring

↓

Publication
```

---

# Computer Vision

Je ne commencerais PAS par de l'IA.

Commencer par des règles.

Exemple

```
Végétation > 40 %

↓

+10
```

Puis

```
Différence toiture

↓

+12
```

Puis

```
Anomalies

↓

+5
```

Seulement ensuite

Machine Learning.

---

# Dataset IA

L'application permet aux utilisateurs de corriger l'IA.

```
Maison entretenue

Maison moyenne

Maison dégradée

Maison probablement vacante
```

Ces validations deviennent le dataset.

C'est probablement l'actif le plus important de la société.

---

# Roadmap

## V0

Une commune

Exemple

Betton

Objectif

Valider le score.

---

## V1

Une métropole

Rennes

Fonctionnalités

- carte
- recherche
- score
- fiches
- favoris

---

## V2

France entière

---

## V3

IA

Détection automatique

---

## V4

CRM

Prospection

Suivi

Historique

---

# Fonctionnalités futures

## Alertes

"Une nouvelle opportunité est apparue."

---

## Monitoring

Un bien change de score.

---

## Comparaison avant/après

Orthophotos

---

## IA

Lecture automatique

- PLU
- DPE
- règlements

---

## Simulation

Division

Extension

Piscine

Surélévation

---

## Rentabilité

Simulation complète

---

## Marketplace

Professionnels

---

## API

Pour les logiciels tiers

---

# Monétisation

Solo

79 €/mois

---

Professionnel

249 €/mois

---

Entreprise

999 €/mois

---

Collectivités

Contrat annuel

---

API

Facturation au volume

---

# Ce qui fera la différence

Le cadastre est public.

DVF est public.

Le DPE est public.

Tout le monde peut les récupérer.

Le vrai avantage concurrentiel sera :

- le moteur de scoring
- les données annotées
- le dataset IA
- les retours utilisateurs
- l'explication des scores
- la qualité des estimations
- la vitesse de calcul

Le produit ne sera pas une carte.

Le produit sera un **moteur d'intelligence immobilière**.

---

# Vision long terme

À terme, la plateforme pourrait devenir le "Bloomberg de l'immobilier physique".

Chaque bâtiment de France disposerait d'une fiche enrichie avec :

- son historique,
- son état probable,
- son potentiel foncier,
- son potentiel de rénovation,
- son score de rentabilité,
- son score de vacance,
- son score environnemental,
- son historique d'évolution,
- des alertes,
- des comparables,
- des simulations d'investissement.

L'utilisateur n'aurait plus besoin de chercher des annonces : la plateforme identifierait en permanence les opportunités avant qu'elles ne deviennent visibles sur les portails immobiliers.