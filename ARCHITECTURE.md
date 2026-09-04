# Immo Opportunities — Architecture technique

**Version :** 0.1  
**Statut :** Architecture de référence du MVP Bretagne  
**Date :** 3 août 2026  
**Document produit associé :** [SPEC.md](./SPEC.md)  

---

## 1. Décision synthétique

Immo Opportunities utilise une architecture de **monolithe modulaire enrichi de services spécialisés**.

Le domaine, l'API et le scoring restent dans une base de code Python cohérente. Les fonctions qui ont des contraintes techniques propres sont déployées séparément : frontend, API, serveur de tuiles, workers applicatifs et orchestrateur de données.

Cette architecture est dimensionnée pour la Bretagne entière sans introduire prématurément Kubernetes, des microservices, un data warehouse ou une plateforme ML.

### Stack retenue

| Couche | Choix |
|---|---|
| Frontend | React, TypeScript strict, Vite, MUI |
| Cartographie | MapLibre GL JS via `react-map-gl/maplibre` |
| État serveur | TanStack Query |
| État local | URL pour les filtres, Zustand pour l'état éphémère complexe |
| Formulaires | React Hook Form + Zod |
| API | FastAPI, Pydantic, OpenAPI |
| Domaine/persistance | Python 3.13, SQLAlchemy 2, GeoAlchemy2, psycopg 3 |
| Base | PostgreSQL 15 + PostGIS 3.x |
| Recherche | PostgreSQL `pg_trgm`, `unaccent` et index spatiaux |
| Tuiles | Martin, vues/fonctions PostGIS, MVT |
| Pipelines data | Dagster |
| Traitement | Polars, PyArrow, DuckDB Spatial, Shapely, pyogrio, Rasterio/GDAL |
| Tâches applicatives | Celery + Redis |
| Stockage brut | MinIO compatible S3, en conteneur |
| Authentification | Keycloak, OpenID Connect, Authorization Code + PKCE |
| Reverse proxy/TLS | Caddy |
| Observabilité | OpenTelemetry, Prometheus, Loki, Grafana |
| Packaging | Docker, Docker Compose v2 |
| Infrastructure | VPS Ubuntu 24.04 LTS générique, Ansible, GitHub Actions |
| Sauvegarde | WAL-G PostgreSQL + réplication MinIO vers stockage S3 hors site |
| CI/CD | GitHub Actions + registre de conteneurs |
| Python tooling | uv, Ruff, Pyright, pytest |
| Frontend tooling | pnpm, Biome, `tsc`, Vitest, Testing Library, Playwright |

### Versions de runtime

- Python 3.13 ;
- Node.js 24 LTS ;
- PostgreSQL 15 et PostGIS 3.x dans une image Docker versionnée ;
- navigateurs modernes définis par la cible de build Vite.

Les versions exactes des bibliothèques sont figées dans `uv.lock` et `pnpm-lock.yaml`, pas dans ce document. Les montées de version sont réalisées explicitement et testées.

---

## 2. Principes architecturaux

### 2.1 Pré-calculer plutôt que recalculer à la lecture

Les features et scores régionaux sont calculés lors d'une release de données. Déplacer la carte ne déclenche pas un recalcul du score.

La lecture utilise des snapshots immuables et des vues optimisées. Seuls les scénarios financiers personnalisés et les actions utilisateur sont calculés à la demande.

### 2.2 Conserver la provenance

Chaque valeur calculée doit pouvoir être reliée à :

- une release de dataset ;
- une ou plusieurs lignes sources ;
- une transformation versionnée ;
- une définition de feature ;
- une définition de score ;
- un instant de calcul.

### 2.3 Séparer données communes et données client

Les parcelles, bâtiments, observations publiques et scores publiés sont communs à tous les clients autorisés.

Les statuts, notes, recherches, scénarios et exports appartiennent à une organisation. Cette séparation évite de dupliquer le référentiel géographique tout en protégeant les données métier des clients.

### 2.4 Une seule source de vérité transactionnelle

PostgreSQL/PostGIS est la source de vérité des données normalisées, scores publiés et données applicatives.

MinIO est la source de vérité des fichiers bruts et artefacts volumineux. Redis n'est jamais une source de vérité.

### 2.5 Commencer simple, garder des sorties d'évolution

- pas de microservices métier au MVP ;
- pas de Kubernetes au MVP ;
- pas d'Elasticsearch tant que PostgreSQL suffit ;
- pas de data warehouse séparé ;
- pas de feature store ML ;
- interfaces et données versionnées pour permettre ces évolutions plus tard.

### 2.6 Un service par conteneur

Chaque service ou processus long possède son propre conteneur et son propre cycle de vie. PostgreSQL/PostGIS, Redis, MinIO, Keycloak, Caddy, Martin, FastAPI et le frontend ne sont jamais regroupés dans une image omnibus.

Dagster webserver, Dagster daemon, Dagster code location, Celery worker et Celery beat s'exécutent également dans des conteneurs distincts, même lorsque plusieurs d'entre eux réutilisent la même image. Prometheus, Loki, Grafana et Alloy restent quatre services séparés.

---

## 3. Vue d'ensemble

```text
                            Internet
                               │
                               ▼
                        ┌─────────────┐
                        │    Caddy    │ TLS, routage, auth des tuiles
                        └──────┬──────┘
                 ┌─────────────┼─────────────────┐
                 ▼             ▼                 ▼
          ┌────────────┐ ┌────────────┐   ┌────────────┐
          │ React SPA  │ │  FastAPI   │   │   Martin   │
          │ MapLibre   │ │ API métier │   │ tuiles MVT │
          └────────────┘ └─────┬──────┘   └─────┬──────┘
                               │                │ lecture seule
                               ▼                ▼
                        ┌────────────────────────────┐
                        │ PostgreSQL 15 + PostGIS    │
                        │ référentiel, scores, app   │
                        └──────────────┬─────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
           ┌────────────┐       ┌────────────┐       ┌────────────┐
           │  Dagster   │       │  Celery    │       │   Redis    │
           │ pipelines  │       │ jobs app   │       │ queue/cache│
           └─────┬──────┘       └────────────┘       └────────────┘
                 │
                 ▼
          ┌──────────────┐
          │    MinIO     │ fichiers bruts, exports, images
          │ S3 compatible│
          └──────────────┘

     Keycloak fournit l'identité OIDC ; l'API gère organisations et rôles.
```

---

## 4. Style d'architecture applicative

### 4.1 Monolithe modulaire

Le backend suit quatre couches logiques :

```text
API / adapters entrants
        ↓
Application / cas d'usage
        ↓
Domaine
        ↓
Infrastructure / SQL / services externes
```

Règles de dépendance :

- le domaine ne dépend ni de FastAPI, ni de SQLAlchemy, ni de Dagster ;
- l'application orchestre les cas d'usage et les transactions ;
- l'infrastructure implémente les repositories et accès externes ;
- FastAPI ne contient pas de logique métier ;
- les pipelines réutilisent les définitions du domaine et des features, sans appeler l'API HTTP ;
- le scoring ne lit jamais directement des fichiers bruts ;
- l'API ne déclenche jamais un traitement régional dans le processus web.

### 4.2 Modules métier

```text
identity
organizations
geography
buildings
transactions
energy
urbanism
risks
features
scoring
opportunities
financial_scenarios
reviews
prospecting
exports
administration
```

Les modules communiquent par appels internes explicites. Un bus de messages métier n'est pas nécessaire au MVP.

### 4.3 Transactions

- un cas d'usage applicatif définit une transaction ;
- les écritures utilisateur sont courtes ;
- aucun téléchargement ou calcul géospatial lourd ne se déroule dans une transaction API ;
- les snapshots sont publiés atomiquement ;
- les tâches Celery utilisent des clés d'idempotence ;
- les imports Dagster sont relançables sans produire de doublons.

---

## 5. Organisation du dépôt

Un monorepo est retenu.

```text
immo-opportunities/
├── apps/
│   └── web/                    # React/Vite
├── backend/
│   ├── pyproject.toml
│   ├── src/immo/
│   │   ├── api/
│   │   ├── application/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   ├── scoring/
│   │   └── workers/
│   ├── migrations/            # Alembic
│   └── tests/
├── pipelines/
│   ├── pyproject.toml
│   ├── src/immo_pipelines/
│   │   ├── assets/
│   │   ├── resources/
│   │   ├── checks/
│   │   └── schedules/
│   └── tests/
├── map/
│   ├── styles/
│   ├── sprites/
│   ├── martin/
│   └── sql/                    # fonctions MVT versionnées
├── contracts/
│   ├── datasets/
│   ├── features/
│   └── openapi/
├── docker/
│   ├── api/
│   ├── web/
│   ├── postgres/              # PostGIS + WAL-G
│   ├── dagster/
│   └── ops/                   # Ansible, SOPS, age
├── infra/
│   ├── ansible/
│   ├── secrets/
│   └── monitoring/
├── docs/
├── compose.yaml
├── compose.dev.yaml
├── compose.prod.yaml
├── compose.observability.yaml
├── Makefile
├── pnpm-workspace.yaml
├── pyproject.toml              # workspace uv
├── uv.lock
├── SPEC.md
├── ARCHITECTURE.md
└── DEPLOYMENT.md
```

`contracts/datasets` contient les mappings de schémas par release. `contracts/features` contient les définitions déclaratives des features et leurs règles de données manquantes.

---

## 6. Frontend

### 6.1 Choix

Une SPA React/Vite est retenue. Le produit est une application authentifiée et cartographique ; le rendu serveur et le SEO de Next.js n'apportent pas de valeur suffisante au MVP.

Bibliothèques :

- React ;
- TypeScript en mode strict ;
- Vite ;
- React Router ;
- MUI ;
- `react-map-gl/maplibre` et MapLibre GL JS ;
- TanStack Query ;
- TanStack Table pour les listes riches ;
- Zustand pour l'état éphémère non serveur ;
- React Hook Form et Zod ;
- `oidc-client-ts` pour le flux OIDC.

### 6.2 Répartition de l'état

| État | Emplacement |
|---|---|
| filtres partageables | URL |
| emprise, zoom et sélection | URL ou état de carte synchronisé |
| données API | cache TanStack Query |
| préférences persistantes | API et base |
| ouverture de panneaux/interaction | Zustand |
| formulaire non sauvegardé | React Hook Form |

Les entités métier ne sont pas dupliquées dans un store global.

### 6.3 Contrat API

FastAPI publie OpenAPI. Un client TypeScript est généré avec Orval.

Le code frontend n'écrit pas manuellement des types représentant les réponses API. Une modification incompatible échoue lors de la génération ou du typecheck.

### 6.4 Cartographie

- MapLibre affiche des sources raster externes autorisées et les tuiles MVT internes ;
- les parcelles, bâtiments et candidats ne sont pas chargés comme un GeoJSON régional complet ;
- les interactions utilisent l'identifiant de feature MVT ;
- le détail complet est chargé par l'API après sélection ;
- les statuts propres à l'organisation sont récupérés par API pour l'emprise courante ;
- les couches et niveaux de zoom sont définis dans un style versionné ;
- l'attribution des producteurs reste visible.

### 6.5 Fond de carte

Le MVP utilise les fonds et orthophotos IGN compatibles avec leurs conditions de diffusion. Les couches métier sont produites en interne.

L'application ne dépend pas de Google Maps ou de Google Street View pour son fonctionnement principal.

---

## 7. API et backend

### 7.1 API

FastAPI est retenu pour :

- les contrats Pydantic ;
- la génération OpenAPI ;
- l'intégration avec l'écosystème Python du traitement de données ;
- l'exécution ASGI ;
- la possibilité de générer le client TypeScript.

L'API est REST, versionnée sous `/api/v1`. GraphQL n'est pas retenu.

### 7.2 Accès à PostgreSQL

- SQLAlchemy 2 en mode synchrone ;
- psycopg 3 ;
- GeoAlchemy2 pour les types géographiques ;
- Alembic pour les migrations ;
- pool de connexions borné par processus ;
- requêtes spatiales complexes écrites explicitement en SQL lorsque nécessaire.

Le mode synchrone est volontaire : les tuiles ne transitent pas par FastAPI et le volume API du MVP ne justifie pas la complexité d'un ORM asynchrone. Plusieurs workers web fournissent la concurrence.

### 7.3 Processus web

- serveur ASGI : Uvicorn ;
- gestion des processus : plusieurs workers dans le conteneur ou plusieurs réplicas ;
- validation des entrées Pydantic ;
- sérialisation contrôlée ;
- pagination par curseur ;
- timeout explicite des requêtes ;
- limite de taille des réponses et exports asynchrones.

### 7.4 Recherche

La première version utilise PostgreSQL :

- `pg_trgm` pour la recherche approchée ;
- `unaccent` pour la normalisation ;
- index B-tree pour codes et identifiants ;
- index GiST pour les géométries ;
- index plein texte si nécessaire.

Elasticsearch/OpenSearch ne sera introduit que si des mesures montrent que PostgreSQL ne répond plus au besoin.

---

## 8. Architecture cartographique

### 8.1 Serveur de tuiles

Martin est retenu car il sert des tuiles vectorielles depuis :

- tables et vues PostGIS ;
- fonctions PostgreSQL ;
- fichiers PMTiles/MBTiles si certaines couches deviennent statiques.

Il n'est pas exposé directement à Internet. Caddy contrôle l'accès et route uniquement vers les sources déclarées.

### 8.2 Types de couches

| Type | Exemple | Source |
|---|---|---|
| statique/versionnée | limites, zonages stables | PMTiles ou vue release |
| dynamique commune | candidats et scores publiés | fonction PostGIS via Martin |
| privée organisation | statuts et annotations | API GeoJSON bornée à l'emprise |
| raster externe | orthophoto IGN | service IGN autorisé |

Les données privées d'une organisation ne sont pas placées dans une tuile partagée ou mise en cache publiquement.

### 8.3 Tuiles d'opportunités

La tuile commune contient uniquement les attributs nécessaires au rendu :

```text
opportunity_id
property_unit_id
strategy_code
overall_score
confidence_level
score_class
snapshot_version
geometry simplifiée selon le zoom
```

Le détail, les preuves et les scénarios ne sont jamais embarqués dans les tuiles.

Au MVP, les filtres simples sont appliqués côté MapLibre sur les attributs de la tuile. L'API calcule séparément la liste exacte correspondant aux mêmes filtres.

Si le volume rend cette approche insuffisante, une fonction Martin accepte un `filter_hash` opaque résolu côté serveur. Aucun fragment SQL utilisateur n'est transmis à PostgreSQL.

### 8.4 Cache

- cache mémoire Martin pour les tuiles chaudes ;
- `ETag` basé sur la version du snapshot ;
- URL contenant la release pour permettre l'invalidation ;
- cache privé au reverse proxy pour les données protégées communes ;
- aucune mise en cache partagée des notes, statuts ou scénarios client.

### 8.5 Systèmes de coordonnées

- calculs géométriques de référence : Lambert-93, EPSG:2154 ;
- échange API : WGS84, EPSG:4326 ;
- rendu tuiles : Web Mercator, EPSG:3857 ;
- SRID obligatoire et validé à l'import ;
- géométries de tuiles pré-transformées ou matérialisées lorsque le coût le justifie.

---

## 9. Base de données

### 9.1 Schémas PostgreSQL

```text
meta          releases, imports, transformations, qualité
reference     zones, adresses, parcelles, bâtiments, unités
observation   transactions, DPE, urbanisme, risques
feature       définitions et valeurs calculées
scoring       définitions, snapshots, composantes, preuves
market        segments, comparables, métriques
app           organisations, utilisateurs, statuts, notes, scénarios
tiles         vues matérialisées et fonctions MVT
audit         événements sensibles et exports
```

Le schéma `raw` n'est pas utilisé comme stockage permanent de fichiers. Les fichiers bruts restent dans MinIO. Des tables de staging temporaires ou versionnées sont créées par les pipelines.

### 9.2 Géométries

- géométrie canonique en EPSG:2154 ;
- géométrie valide ou quarantaine ;
- index GiST ;
- simplifications pré-calculées par niveau d'usage ;
- géométrie de rendu séparée de la géométrie d'analyse ;
- aucune simplification ne réécrit la source canonique.

### 9.3 Indexation initiale

- GiST sur toutes les géométries interrogées ;
- B-tree sur identifiants sources, codes INSEE, département, EPCI et release ;
- index composites sur stratégie/version/score ;
- `pg_trgm` sur libellés d'adresse ;
- index partiels sur snapshots publiés ;
- analyse des requêtes avec `EXPLAIN (ANALYZE, BUFFERS)` avant ajout d'index spécialisés.

### 9.4 Partitionnement

Le partitionnement physique n'est pas imposé au démarrage. Les volumes Bretagne peuvent être gérés avec des tables correctement indexées.

Le partitionnement est envisagé pour :

- les grosses tables historiques par release ;
- les valeurs de features par version ;
- les événements d'audit par mois ;
- l'extension nationale par département ou release.

Une table n'est partitionnée qu'après mesure du coût d'écriture, de maintenance et des plans d'exécution.

### 9.5 Rôles PostgreSQL

```text
migration_owner   DDL uniquement
api_rw            lecture métier + écritures app autorisées
pipeline_rw       staging, référentiel, features et publication
tiles_ro          lecture limitée au schéma tiles
dagster_meta      métadonnées Dagster séparées
keycloak_owner    base Keycloak séparée
backup_ro         export contrôlé
```

Martin ne peut pas lire `app`, `audit` ou les tables sources non publiées.

### 9.6 Multi-tenant

- les tables client portent `organization_id` ;
- l'API applique systématiquement l'organisation courante ;
- PostgreSQL Row-Level Security apporte une défense supplémentaire sur les tables sensibles ;
- les rôles métier sont stockés dans l'application ;
- un administrateur d'une organisation ne peut pas déléguer de rôle plateforme.

---

## 10. Pipelines de données

### 10.1 Orchestrateur

Dagster est retenu pour :

- représenter les datasets et tables comme des assets ;
- matérialiser par département et release ;
- suivre la lignée ;
- exécuter des contrôles de qualité ;
- relancer une partition ;
- planifier les mises à jour ;
- réaliser des backfills contrôlés.

Les partitions initiales sont :

```text
dataset_id × dataset_release × département
```

Les agrégats régionaux dépendent explicitement des quatre partitions départementales.

### 10.2 Étapes

```text
discover
  ↓
download
  ↓
checksum + archive raw
  ↓
schema validation
  ↓
normalize/stage
  ↓
entity resolution
  ↓
quality checks
  ↓
feature computation
  ↓
scoring
  ↓
tile views/materialization
  ↓
atomic publication
```

### 10.3 Bibliothèques de traitement

- `httpx` pour les téléchargements/API ;
- `tenacity` pour les reprises bornées ;
- Polars et PyArrow pour les données tabulaires ;
- DuckDB et son extension spatiale pour inspecter et transformer les fichiers volumineux ;
- pyogrio et Shapely pour les vecteurs ;
- Rasterio/GDAL pour les rasters ;
- psycopg `COPY` pour les chargements PostgreSQL ;
- PostGIS pour les jointures et features spatiales canoniques.

Pandas/GeoPandas peuvent être utilisés ponctuellement lorsqu'une bibliothèque l'impose, mais ne constituent pas le moteur tabulaire principal.

### 10.4 Publication atomique

Un pipeline écrit d'abord une release non publiée. Les contrôles doivent réussir avant que le pointeur `active_release` soit déplacé dans une transaction courte.

Une publication invalide le cache via un nouvel identifiant de release. Le rollback consiste à réactiver la release précédente, sans réimporter les données.

### 10.5 Qualité

Les Dagster Asset Checks couvrent :

- schéma ;
- nombre de lignes ;
- couverture géographique ;
- géométries invalides ;
- doublons d'identifiants ;
- taux d'appariement ;
- distributions de features ;
- valeurs aberrantes ;
- fraîcheur ;
- comparaison avec la release précédente.

---

## 11. Tâches asynchrones applicatives

Celery et Redis sont réservés aux tâches déclenchées par l'application :

- génération d'exports ;
- notifications et alertes ;
- génération de documents ;
- recalcul d'un scénario lourd ;
- petits traitements bornés à une organisation.

Dagster reste responsable des imports, features et recalculs régionaux.

La code location chargée des imports est la seule composante data raccordée au réseau Docker
`ingestion`, non interne, afin de télécharger les sources publiques. Elle conserve en parallèle
ses accès aux réseaux internes `app` (PostgreSQL) et `data` (MinIO). L’API, Martin et les services
web ne rejoignent pas ce réseau d’egress.

Règles :

- une tâche possède une clé d'idempotence ;
- l'état durable est stocké dans PostgreSQL ;
- Redis transporte les messages et caches temporaires ;
- les retries sont bornés ;
- les erreurs définitives sont visibles dans l'administration ;
- aucune tâche régionale n'est lancée via Celery.

Celery peut être omis du tout premier spike data. Il devient obligatoire avant les exports et alertes utilisateurs.

---

## 12. Authentification et autorisation

### 12.1 Identité

Keycloak est le fournisseur OIDC initial.

- Authorization Code Flow avec PKCE ;
- MFA activable ;
- politiques de mot de passe gérées par le fournisseur ;
- l'application ne stocke pas de mot de passe ;
- accès token de courte durée ;
- renouvellement selon les mécanismes OIDC sécurisés retenus.

### 12.2 Autorisation

Keycloak prouve l'identité. L'API décide des droits métier.

Rôles initiaux :

```text
platform_admin
organization_admin
analyst
viewer
```

Chaque accès à une ressource client vérifie l'appartenance à l'organisation et la permission demandée.

### 12.3 Tuiles

MapLibre ajoute le bearer token aux requêtes internes via `transformRequest`. Caddy vérifie la session auprès d'un endpoint léger avant de transmettre à Martin.

Martin utilise une connexion PostgreSQL en lecture seule et ne reçoit jamais les claims utilisateur comme SQL libre.

---

## 13. Stockage objet

MinIO fournit le stockage compatible S3 à l'intérieur de la stack Docker. Il ne dépend d'aucun Object Storage managé pour le fonctionnement normal de l'application.

Buckets séparés :

```text
raw-sources        fichiers sources immuables
derived-assets     PMTiles, extraits, artefacts calculés
user-exports       exports temporaires par organisation
documents          documents autorisés
backups            exports chiffrés contrôlés
```

Règles :

- versioning activé pour les sources ;
- chiffrement au repos ;
- URLs signées à durée courte pour les exports ;
- cycle de vie et suppression par catégorie ;
- aucun bucket public ;
- checksum et métadonnées de provenance ;
- séparation logique des exports par organisation.

Les orthophotos complètes ne sont pas dupliquées sans besoin démontré. Le système conserve d'abord les métadonnées et utilise les services autorisés du producteur.

Les buckets durables sont versionnés et répliqués vers une cible S3 hors site distincte. Cette cible sert à la reprise après sinistre ; elle n'est pas une dépendance du chemin de lecture nominal.

---

## 14. Déploiement

Le contrat exécutable, l'arborescence IaC et les runbooks sont définis dans [DEPLOYMENT.md](./DEPLOYMENT.md).

### 14.1 Local

Docker Compose lance :

- PostgreSQL/PostGIS ;
- Redis ;
- MinIO ;
- Keycloak ;
- API ;
- Martin ;
- Dagster webserver/daemon ;
- worker Celery lorsqu'il est requis ;
- Prometheus, Loki, Grafana et Alloy avec le profil d'observabilité ;
- frontend Vite en développement.

Les jeux de développement utilisent un extrait synthétique ou public réduit. Les données restreintes ne sont pas copiées localement.

### 14.2 Production initiale

Tous les services s'exécutent dans Docker Compose sur un VPS Ubuntu 24.04 LTS créé chez le fournisseur choisi, sans dépendance à une API cloud, une base, un Redis ou un Object Storage managés.

```text
Réseau fournisseur + pare-feu
└── serveur Docker
    ├── edge : Caddy, web, FastAPI, Martin, Keycloak
    ├── data : PostgreSQL/PostGIS, Redis, MinIO
    ├── jobs : Dagster, Celery worker/beat
    ├── ops  : Prometheus, Loki, Grafana, Alloy
    ├── stockage persistant PostgreSQL
    └── stockage persistant MinIO
```

Seuls les ports 80 et 443 sont publics. L'administration SSH est filtrée. PostgreSQL, Redis, MinIO, Martin, Dagster et les workers ne publient aucun port sur l'interface publique.

### 14.3 Environnements

- `local` : données réduites ;
- `test` : services éphémères en CI ;
- `staging` : architecture proche de production, échantillon régional ;
- `production` : données Bretagne complètes.

Les serveurs, volumes, réseaux, bases, buckets MinIO, sauvegardes et secrets sont séparés entre staging et production.

### 14.4 Infrastructure as Code

- le VPS et le DNS sont créés chez le fournisseur choisi, hors de ce dépôt ;
- Ansible prépare Ubuntu, installe Docker/Compose, prépare le stockage et déploie la stack ;
- GitHub Actions orchestre le bootstrap initial et les déploiements idempotents par SSH ;
- Ansible, SOPS et `age` sont figés dans une image opérateur Docker utilisée en local et en CI ;
- Docker Compose décrit tous les workloads, y compris PostgreSQL, Redis, MinIO, Keycloak et l'observabilité ;
- chaque workload ou processus long correspond à un service Compose et à un conteneur distinct ;
- SOPS avec `age` chiffre les secrets versionnés ; la clé privée est conservée hors dépôt et hors serveur ;
- aucune modification manuelle non documentée n'est considérée comme persistante ;
- les images de production sont immuables et référencées par digest.

### 14.5 Haute disponibilité

Le serveur unique est acceptable pour le prototype et le pilote si cette limite est explicitement annoncée. Il est redéployable, mais il n'est pas hautement disponible.

Avant le pilote :

- archivage WAL PostgreSQL continu et sauvegarde complète quotidienne hors site ;
- réplication versionnée des buckets MinIO hors site ;
- restauration sur serveur vierge testée et chronométrée ;
- supervision, alertes et procédure de rollback ;
- volumes PostgreSQL et MinIO séparés du disque système.

Avant une promesse contractuelle de disponibilité 99,5 % :

- PostgreSQL répliqué avec bascule testée ;
- stockage objet distribué ou répliqué sur un second site ;
- au moins deux nœuds applicatifs derrière un load balancer ;
- séparation et redondance de Keycloak ;
- workers redondants ;
- exercice de reprise documenté.

Kubernetes n'est envisagé que si le nombre de services, l'équipe d'exploitation ou les besoins d'auto-scaling le justifient réellement.

---

## 15. Observabilité

### 15.1 Standard

OpenTelemetry est le standard d'instrumentation pour :

- traces distribuées ;
- métriques ;
- corrélation des logs ;
- propagation d'un `request_id`.

### 15.2 Outils

- Prometheus : métriques ;
- Loki : logs ;
- Grafana : dashboards et alertes ;
- instrumentation OTel FastAPI, psycopg, Celery et frontend lorsque pertinente ;
- alertes de disponibilité externe.

### 15.3 Métriques critiques

API :

- latence p50/p95/p99 ;
- taux d'erreur ;
- saturation du pool PostgreSQL ;
- requêtes lentes ;
- refus d'autorisation.

Carte :

- latence et taille des tuiles par zoom ;
- taux de cache ;
- erreurs de chargement MapLibre ;
- temps avant première carte utile.

Données :

- durée des assets ;
- partitions échouées ;
- fraîcheur ;
- couverture ;
- taux d'appariement ;
- évolution anormale des features ;
- durée de publication.

Métier :

- nombre de candidats publiés ;
- répartition des niveaux de confiance ;
- utilisation par stratégie ;
- taux de qualification.

Les logs ne contiennent ni token, ni données personnelles inutiles, ni contenu de notes utilisateur par défaut.

---

## 16. Sécurité

### 16.1 Réseau

- seul Caddy publie les ports 80/443 et route les endpoints publics nécessaires, dont Keycloak ;
- PostgreSQL, Redis, Martin, Dagster et workers restent privés ;
- MinIO, Grafana et les consoles d'administration restent privés ou protégés par un accès administratif dédié ;
- filtrage réseau par service ;
- administration via bastion/VPN ou tunnel contrôlé ;
- TLS obligatoire.

### 16.2 Secrets

- SOPS avec `age` pour les secrets chiffrés et versionnés ;
- clé privée `age` dans le secret CI et un coffre de reprise hors ligne, jamais dans Git ni sur le VPS ;
- secrets matérialisés en fichiers `0400` par Ansible et montés via Compose sous `/run/secrets` ;
- rotation documentée ;
- credentials distincts par service ;
- aucun secret dans les images, logs ou variables de CI affichées ;
- comptes humains distincts des comptes de service.

### 16.3 Application

- contrôle d'objet systématique ;
- limites de débit ;
- taille maximale d'upload ;
- validation MIME et contenu ;
- protection CSRF selon le mécanisme de session ;
- Content Security Policy compatible MapLibre ;
- dépendances scannées ;
- journal d'audit pour exports et données sensibles.

### 16.4 Données

- minimisation ;
- rétention par catégorie ;
- chiffrement ;
- séparation par organisation ;
- exports temporaires ;
- suppression logique puis physique selon politique ;
- aucune donnée propriétaire ou LOVAC dans les environnements non autorisés.

---

## 17. Tests et qualité

### 17.1 Backend

- Ruff pour formatage et lint ;
- Pyright en mode strict ;
- pytest ;
- tests unitaires du domaine ;
- tests d'intégration PostGIS ;
- tests de migrations ;
- tests de contrat OpenAPI ;
- tests de sécurité des permissions ;
- snapshots contrôlés des explications de score.

### 17.2 Données

- Dagster Asset Checks ;
- tests des adapters de schéma ;
- fichiers golden réduits par source ;
- tests de géométries et SRID ;
- tests de reproductibilité ;
- tests de non-régression des distributions ;
- backtest sans fuite temporelle ;
- test d'ablation des datasets/features.

### 17.3 Frontend

- Biome ;
- `tsc --noEmit` ;
- Vitest ;
- React Testing Library ;
- Playwright pour les parcours critiques ;
- tests visuels ciblés de la carte ;
- tests clavier et accessibilité.

### 17.4 Performance

- test de charge API avec k6 ;
- benchmark des fonctions MVT par zoom ;
- contrôle de taille maximale de tuile ;
- `EXPLAIN ANALYZE` versionné pour les requêtes critiques ;
- test de déplacement rapide de carte sur un extrait régional complet.

---

## 18. CI/CD

### 18.1 Pull request

```text
format/lint
    ↓
typecheck
    ↓
unit tests
    ↓
integration PostGIS/Redis
    ↓
frontend build
    ↓
OpenAPI compatibility
    ↓
container build + security scan
```

### 18.2 Déploiement

- images immuables étiquetées par commit ;
- manifeste de production épinglé par digest ;
- déploiement automatique en staging ;
- migrations compatibles avec la version précédente ;
- validation manuelle pour production au MVP ;
- health checks ;
- rollback vers l'image précédente ;
- changement de release data indépendant du déploiement applicatif.

### 18.3 Dépendances

- Renovate ouvre les mises à jour ;
- les versions majeures ne sont pas fusionnées automatiquement ;
- scan de vulnérabilités des images et lockfiles ;
- SBOM générée pour les images de production.

---

## 19. Sauvegarde et reprise

### Objectifs initiaux

- RPO PostgreSQL cible : 15 minutes avec archivage WAL surveillé ;
- RPO objets MinIO : 24 heures au maximum au prototype, puis mesure du retard de réplication ;
- RTO prototype : une journée ouvrée, cible 4 heures après validation du runbook ;
- les fichiers sources publics sont retéléchargeables mais leurs checksums et releases restent sauvegardés ;
- les notes, statuts et scénarios utilisateur sont prioritaires.

### Mécanismes

- WAL-G intégré à l'image PostGIS : archivage continu des WAL et base backup quotidienne vers une cible S3 hors site ;
- versioning et réplication hors site des buckets MinIO durables ;
- métadonnées Keycloak et Dagster sauvegardées dans PostgreSQL ; realms, dashboards et politiques provisionnés depuis Git ;
- sauvegardes extérieures au serveur décrit ;
- infrastructure logicielle recréable par GitHub Actions, Ansible et Docker Compose ;
- test de restauration trimestriel au minimum ;
- runbook d'incident et de restauration détaillé dans [DEPLOYMENT.md](./DEPLOYMENT.md) ;
- alerte si le dernier WAL archivé ou la réplication objet dépasse son objectif de fraîcheur.

---

## 20. Performance et capacité

### 20.1 Principe de dimensionnement

La charge dominante n'est pas le nombre d'utilisateurs, mais :

- les imports régionaux ;
- les jointures spatiales ;
- le calcul des features ;
- la production de tuiles ;
- le stockage des releases.

L'API utilisateur reste relativement légère si les scores sont pré-calculés.

### 20.2 Optimisations dans l'ordre

1. index et requêtes PostGIS ;
2. vues matérialisées et géométries simplifiées ;
3. cache Martin ;
4. PMTiles pour les couches immuables ;
5. séparation lecture/écriture PostgreSQL ;
6. réplique de lecture ;
7. partitionnement physique ;
8. mise à l'échelle horizontale des services ;
9. plateforme orchestrée type Kubernetes seulement si nécessaire.

### 20.3 Déclencheurs d'évolution

| Symptôme mesuré | Évolution envisagée |
|---|---|
| tuiles p95 trop lentes malgré index | vue matérialisée ou PMTiles |
| DB saturée par les tuiles | réplique de lecture dédiée à Martin |
| import dépasse la fenêtre acceptable | workers Dagster séparés/plus puissants |
| recherche textuelle insuffisante | OpenSearch ciblé |
| API nécessite des déploiements indépendants fréquents | extraction d'un service justifié |
| couverture nationale et historiques volumineux | partitionnement + stockage analytique ciblé |
| plusieurs modèles ML en production | MLflow/registre de modèles et service d'inférence |

---

## 21. Machine learning et vision, hors MVP

Aucune plateforme ML n'est installée au MVP.

Lorsque le dataset interne est suffisant :

- scikit-learn sert de baseline ;
- LightGBM ou équivalent peut classer des features tabulaires ;
- MLflow n'est ajouté que lorsqu'il existe plusieurs expériences/modèles à suivre ;
- l'inférence du score tabulaire reste batch ;
- PyTorch est réservé à la vision ;
- les images et embeddings restent dans MinIO ;
- chaque modèle possède une model card, un dataset versionné et un protocole hors échantillon.

Le futur indice de vacance reste un modèle et un dataset séparés des stratégies d'investissement.

---

## 22. Choix écartés

| Choix écarté | Motif |
|---|---|
| Next.js | SSR/SEO peu utiles pour une application métier authentifiée et cartographique |
| Google Maps comme socle | coût, personnalisation et dépendance fournisseur |
| Leaflet | moins adapté au rendu vectoriel WebGL de nombreuses couches |
| GeoServer au MVP | plus lourd que Martin pour le besoin MVT/PostGIS ciblé |
| APIFlask | FastAPI offre un contrat OpenAPI/Pydantic plus direct pour ce projet |
| SQLModel | séparation explicite entre modèles ORM et contrats API préférée |
| MongoDB | modèle relationnel et spatial mieux servi par PostgreSQL/PostGIS |
| Elasticsearch dès le départ | PostgreSQL couvre la recherche initiale |
| Airflow | Dagster correspond mieux au modèle d'assets, partitions et qualité |
| Celery pour les pipelines data | absence de lineage et de gestion d'assets |
| Kubernetes au MVP | coût opérationnel disproportionné |
| microservices métier | complexité de déploiement et transactions distribuées sans bénéfice initial |
| scoring à chaque requête | latence, coût et faible reproductibilité |
| stockage des rasters dans PostgreSQL | volumétrie et distribution mieux adaptées à MinIO |

---

## 23. Décisions ADR

| ID | Décision | Statut |
|---|---|---|
| ADR-001 | Monolithe modulaire pour le métier | Acceptée |
| ADR-002 | React/Vite plutôt que Next.js | Acceptée |
| ADR-003 | FastAPI + SQLAlchemy plutôt qu'APIFlask/SQLModel | Acceptée |
| ADR-004 | PostgreSQL/PostGIS comme source de vérité | Acceptée |
| ADR-005 | Martin pour les tuiles MVT | Acceptée |
| ADR-006 | Dagster pour les pipelines régionaux | Acceptée |
| ADR-007 | Celery limité aux tâches applicatives | Acceptée |
| ADR-008 | Keycloak/OIDC pour l'identité | Acceptée |
| ADR-009 | Tous les workloads dans Docker Compose sur VPS générique déployé par GitHub Actions et Ansible | Acceptée |
| ADR-010 | Scoring régional pré-calculé et snapshots immuables | Acceptée |
| ADR-011 | Lambert-93 pour les calculs, WGS84 pour l'échange, Web Mercator pour les tuiles | Acceptée |
| ADR-012 | Pas de ML ni de Kubernetes au MVP | Acceptée |
| ADR-013 | Sauvegardes obligatoirement hors du serveur cible | Acceptée |
| ADR-014 | SOPS + `age` pour les secrets versionnés | Acceptée |

Toute modification d'une décision acceptée nécessite une note ADR datée indiquant le contexte, les alternatives, la décision et les conséquences.

---

## 24. Séquence d'implémentation

1. Créer le monorepo, les toolchains et les fichiers Docker Compose commun/dev/prod.
2. Créer le workflow GitHub Actions et les rôles Ansible, puis valider un bootstrap sur VPS vierge.
3. Construire PostgreSQL/PostGIS avec WAL-G, migrations, schémas, rôles et sauvegarde hors site.
4. Mettre en place MinIO, versioning, réplication hors site et métadonnées de releases.
5. Créer les assets Dagster pour un dataset et un département.
6. Étendre les partitions aux quatre départements bretons.
7. Construire le référentiel parcelle/bâtiment/adresse.
8. Exposer une première couche MVT via Martin.
9. Créer la SPA MapLibre et afficher la Bretagne.
10. Ajouter FastAPI, recherche et fiche entité.
11. Implémenter features, scoring et publication atomique.
12. Ajouter organisations, OIDC, notes et statuts.
13. Ajouter scénarios, exports et Celery.
14. Déployer staging puis production, restaurer sur un second serveur vierge et mesurer RPO/RTO.
15. Mesurer avant toute optimisation ou extraction de service.

---

## 25. Definition of Done architecture MVP

- environnement local reproductible avec une commande documentée ;
- tous les services de runtime s'exécutent dans Docker, sans base ni cache managés ;
- un VPS Ubuntu vierge est configuré par GitHub Actions et Ansible sans intervention dans les conteneurs ;
- base PostgreSQL/PostGIS migrée automatiquement ;
- rôles et isolation des organisations testés ;
- une release de données peut être importée, validée, publiée et annulée ;
- les pipelines sont partitionnés sur les quatre départements ;
- le score publié est reproductible ;
- Martin ne peut lire que les vues autorisées ;
- la carte utilise des MVT et ne télécharge pas un GeoJSON régional complet ;
- l'API OpenAPI génère le client TypeScript ;
- les tâches longues ne bloquent pas les processus web ;
- sauvegarde PostgreSQL, réplication MinIO et restauration sur serveur vierge sont testées ;
- traces, métriques et logs sont corrélés ;
- les parcours critiques passent en CI ;
- le déploiement staging et le rollback sont automatisés ;
- les sauvegardes et la clé de reprise sont conservées hors du serveur cible ;
- aucun composant hors MVP, notamment ML ou Kubernetes, n'est requis pour lancer le produit.
