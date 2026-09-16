# Immo Opportunities — Architecture technique

**Version :** 1.0 — réécrite le 15 septembre 2026 sur décision [ADR-016](./docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md)
**Statut :** description de ce qui existe et de ce qui est décidé. Ce qui est souhaité et non décidé est marqué comme tel.
**Remplace :** la version 0.1 du 3 août 2026 (`git show a32d439:ARCHITECTURE.md`)
**Document produit associé :** [SPEC.md](./SPEC.md)

---

## 1. Décision synthétique

Deux architectures cohabitent dans ce dépôt, et ce document les distingue à chaque section.

**L'architecture active** porte le produit décidé par ADR-016 : une base PostgreSQL/PostGIS qui
contient le référentiel spatial du 35 et quatre sources métier, des scripts Python reproductibles
qui importent, mesurent et produisent des documents, et un outillage de preuve (contrats,
manifestes, rapports, recompte). Elle n'a ni utilisateur connecté, ni API publique, ni
déploiement.

**La plateforme** est l'application écrite entre le 4 et le 15 septembre 2026 : SPA
React/MapLibre, API FastAPI, moteur de score, multi-tenant OIDC/RLS, tuiles Martin, Dagster,
observabilité, déploiement Ansible. Gelée par ADR-016, elle se développe de nouveau depuis
[ADR-019](docs/decisions/ADR-019-lever-le-gel-de-la-plateforme.md). Elle tourne en local, elle est décrite ici avec ses défauts connus, et elle ne se
déploie pour personne avant les conditions de §25.2.

### Stack réelle

Ce tableau décrit ce qui est dans `uv.lock`, `pnpm-lock.yaml` et `compose.yaml`, pas une cible.

| Couche | Réel | Statut |
|---|---|---|
| Base | PostgreSQL 15 + PostGIS 3.5 (`postgis/postgis:15-3.5`) | active |
| Accès base | SQL brut via `sqlalchemy.text()`, psycopg 3, aucun modèle ORM ; Alembic, 24 révisions | active |
| Scripts d'import et de mesure | Python 3.13, `httpx`, `tenacity`, `shapely`, `pyproj`, `pyshp`, `py7zr`, `ijson`, `minio` | active |
| Orchestrateur | Dagster 1.10, **un asset réel** (DS-01) ; les 25 autres cibles utilisent son image comme interpréteur | sous-employé |
| Stockage brut | MinIO en conteneur, 6 Go d'archives épinglées | actif, remplacement envisagé (§13) |
| API | FastAPI 0.141, Pydantic 2, 45 routes dont 4 authentifiées | local, non déployable en l'état |
| Frontend | React 19, Vite 6, TypeScript strict, MapLibre 6 via `react-map-gl` 8, `oidc-client-ts`, CSS custom, client généré par `openapi-typescript` | outil local de vérification (C4) |
| Tuiles | Martin 1.13, trois fonctions PostGIS | local |
| Identité | Keycloak 26.7, OIDC Authorization Code + PKCE | local, aucun utilisateur |
| Reverse proxy | Caddy 2.11 | local |
| Observabilité | Prometheus, Loki, Grafana, Alloy, node-exporter | sans usage démontré |
| Cache et file | Redis 8 — **référencé par aucun code** | à retirer |
| Packaging | Docker Compose v2, 20 services, 16 conteneurs permanents | actif en local |
| Infrastructure | Ansible + SOPS/age, GitHub Actions ; **jamais exécuté** | non exécuté |
| Outillage | uv 0.10, Ruff, Pyright strict, pytest ; pnpm 10, `tsc`, Playwright | actif |

Ce qui était déclaré dans la version 0.1 et **n'existe pas** : MUI, TanStack Query, Zustand,
React Router, React Hook Form, Zod, Orval, Biome, Vitest, Testing Library, Celery, WAL-G, Polars,
PyArrow, DuckDB, pyogrio, Rasterio, OpenTelemetry, Renovate, registre de conteneurs, tests
d'intégration PostGIS.

### Versions de runtime

Python 3.13, Node.js 24, PostgreSQL 15 (fin de support novembre 2027 — une migration majeure est
à prévoir avant tout déploiement de la plateforme). Les versions exactes sont dans les lockfiles.

---

## 2. Principes architecturaux

### 2.1 Reproductible avant rapide

Toute mesure publiée se régénère depuis la base par une commande `make`, avec graine et filtres
écrits dans la sortie. Toute source s'importe depuis un manifeste checksumé, sous une version de
transformation. C'est le principe qui a survécu à la redéfinition du produit.

### 2.2 Conserver la provenance

Chaque valeur en base relie une release de dataset, un run d'import, une version de
transformation. Chaque chiffre dans `docs/data/` nomme son filtre, sa cohorte et sa date.

### 2.3 Pré-calculer plutôt que recalculer à la lecture

Principe de la plateforme. Pour le baromètre, il n'y a pas de lecture interactive :
une génération de document par millésime.

### 2.4 Une seule source de vérité transactionnelle

PostgreSQL/PostGIS. MinIO est la source de vérité des octets bruts. Redis n'est source de rien.

### 2.5 Commencer simple

Pas de microservices, pas de Kubernetes, pas de data warehouse, pas de feature store, pas de
ML. Ce principe de la version 0.1 n'a pas été appliqué à la plateforme (16 conteneurs pour zéro
utilisateur) ; il s'applique au produit actif.

### 2.6 Un service par conteneur

Règle de la plateforme, tenue. Sa conséquence — 19 chaînes d'approvisionnement à patcher pour
un produit sans utilisateur — a été un des motifs du gel d'ADR-016.

---

## 3. Vue d'ensemble

### 3.1 Architecture active

```text
Sources publiques (DVF, DPE, cadastre, RNB, BAN, BD TOPO, BDNB, GPU, Géorisques)
        │  manifeste épinglé, SHA-256, copie archivée MinIO
        ▼
pipelines/scripts/import_*.py  ── version de transformation, run idempotent
        │
        ▼
PostgreSQL 15 + PostGIS  (29 Go pour le 35)
   reference · observation · meta · feature
        │
        ▼
pipelines/scripts/*_report.py, market_barometer.py (H1), market_listing_candidates.py
        │
        ▼
docs/data/*.md, CSV, HTML autonome  ── recompte-preuve avant publication
```

### 3.2 Plateforme

```text
                    Caddy (TLS, routage)
        ┌──────────────┼─────────────────┐
   React SPA       FastAPI            Martin
   MapLibre        45 routes          3 fonctions MVT
        │              │                  │
        └──────────────┴────────┬─────────┘
                          PostgreSQL/PostGIS
                     app · scoring · market · tiles  (vides)
   Keycloak (OIDC) · Dagster ×3 · MinIO · Redis · Prometheus · Loki · Grafana · Alloy
```

---

## 4. Style d'architecture applicative

### 4.1 Ce qui existe

`backend/src/immo/` est un module Python plat : un fichier par domaine (`explorer.py`,
`scoring.py`, `review.py`, `spatial.py`, `market_data.py`, `connected_mvp.py`,
`brittany_pilot.py`, `accounts.py`, `cadastre.py`) contenant SQL et sérialisation, et
`api/routes/*.py` qui les exposent. Il n'y a ni couche domaine, ni repositories, ni cas d'usage
séparés : la version 0.1 décrivait quatre couches qui n'ont jamais été construites.

`pipelines/src/immo_pipelines/` est une bibliothèque (`cadastre/`, `spatial/`, `market_data/`,
`scoring/`, `progress.py`) appelée par `pipelines/scripts/*.py`. `spatial/importer.py` (2 969
lignes) porte l'essentiel du SQL PostGIS du projet.

### 4.2 Règles tenues

- les pipelines n'appellent jamais l'API HTTP ;
- l'API ne déclenche aucun traitement régional ;
- le moteur de score ne lit jamais de fichier brut ;
- aucune injection SQL : toutes les valeurs passent par des paramètres liés (audit §7.4).

### 4.3 Transactions

Un script d'import commite élément par élément et reprend depuis l'état en base (§10.6). Une
publication de release déplace un pointeur dans une transaction courte. Les écritures
utilisateur de la plateforme sont courtes et positionnent le contexte RLS par `set_config`.

---

## 5. Organisation du dépôt

```text
immo-opportunities/
├── apps/web/                 # SPA React (outil de vérification) : src/App.tsx, sheets/, review/, api.ts, auth.ts
├── backend/
│   ├── src/immo/             # modules plats + api/routes/
│   ├── migrations/versions/  # 24 révisions Alembic, 5 925 lignes de SQL
│   ├── scripts/              # provision_member.py (mort, voir audit §7.4)
│   └── tests/                # 29 fichiers, aucun ne touche PostgreSQL
├── pipelines/
│   ├── src/immo_pipelines/   # cadastre/ spatial/ market_data/ scoring/ assets/ progress.py
│   ├── scripts/              # 28 scripts : import_*, pin_*, compute_*, *_report, listes, kit terrain
│   └── tests/                # 32 fichiers, fixtures et FakeConnection
├── contracts/
│   ├── datasets/DS-01..DS-09 # v1.json + releases/*.json (manifestes épinglés)
│   ├── features/             # morphology-v1, market-data-v1 (déclaratifs, non lus)
│   ├── scoring/              # feature-registry, deux définitions draft
│   └── openapi/v1.json       # généré, vérifié en CI
├── map/styles/real-map-v1.json   # seul artefact de map/ ; les fonctions MVT sont dans les migrations
├── config/                   # caddy, keycloak, postgres, prometheus, loki, grafana, alloy
├── docker/                   # api, pipelines, web, ops
├── infra/ansible/            # rôles base, storage, secrets, immo_stack ; jamais exécuté
├── scripts/                  # outillage : backlog-status, check-*, backup-platform, restore-drill…
├── docs/
│   ├── backlog/              # tickets, README généré
│   ├── data/                 # rapports datés, preuves
│   ├── decisions/            # ADR-015, ADR-016
│   ├── operations/           # runbooks
│   ├── versions/             # versions d'implémentation v0.1 à v0.8
│   ├── archive/              # explo d'août 2026
│   └── audit-critique-2026-09-15.md
├── compose.yaml, compose.dev.yaml, compose.prod.yaml, compose.observability.yaml
├── Makefile, pyproject.toml, uv.lock, pnpm-workspace.yaml
├── SPEC.md, ARCHITECTURE.md, CLAUDE.md, DEPLOYMENT.md, README.md
```

---

## 6. Frontend — outil local de vérification

### 6.1 Ce qui existe

Depuis C4 ([ADR-018](docs/decisions/ADR-018-degel-restreint-explorer.md)), l'Explorer est l'outil
local de vérification des données du 35 : recherche d'adresse et de parcelle, carte des parcelles
et bâtiments avec orthophoto, fiches adresse, parcelle et bâtiment, mutations DVF et diagnostics
DPE par parcelle, pastille de couverture avec infobulle, revue B4 dans un `<dialog>` modal. Deux colonnes, carte
et fiche à onglets (Aperçu, Ventes DVF, Diagnostics DPE, Sources). Depuis C5, `App.tsx` (~200
lignes) ne porte que la coquille et l'état de navigation ; `Search.tsx`, `sheets/`, `review/`,
`ui.tsx` (composants de base) et `format.ts` portent le reste. Jetons de style dans `:root`,
plancher typographique à 12 px. État local par `useState`, sélection et cadrage dans l'URL,
chargements par le client `api.ts` et `AbortController`. Aucune bibliothèque d'état,
aucun routeur, aucune bibliothèque de composants.

### 6.2 Ce qui a été retiré

Liste, filtres et fiche candidat, workflow de qualification, scénarios financiers, recherches
sauvegardées, couche des opportunités, panneau d'administration régionale, sélecteur de
département : environ 700 lignes inatteignables faute de score publié, retirées par C4. Les
routes d'API correspondantes existent toujours ; le code front se récupère au commit de C4.

### 6.3 Défauts connus

Corrigés par C4 : vue initiale à lon 0 / lat 0, carte vide sans explication sous le zoom 13,
inconnu peint comme zéro (la couche a disparu), `fetch` bruts qui affichaient « aucune donnée »
sur un 500, typographie à 8-9 px, modale sans piège de focus. Reste : renouvellement OIDC
silencieux bloqué par `X-Frame-Options: DENY`. Détail d'origine : audit §9.

### 6.4 Règle

Rester sur `App.tsx` + CSS custom + MapLibre, ou décider par ADR une convergence vers une
bibliothèque. Pas les deux. Les écrans de candidats retirés par C4 se reprennent de l'historique
quand un score publié existe.

---

## 7. API et backend

### 7.1 Ce qui existe

FastAPI, REST sous `/api/v1`, 45 routes dans dix routeurs, OpenAPI généré et vérifié par
`make openapi-check`. Validation Pydantic rigoureuse (`Literal`, bornes, validateurs croisés).
Douze routes joignent des tables vides et ne peuvent retourner que du vide ; douze autres ne sont
appelées par aucun code front.

### 7.2 Accès à PostgreSQL

SQLAlchemy 2 synchrone, psycopg 3, `text()` partout, pool de 5 connexions, `pool_pre_ping`. Aucun
`statement_timeout`. Le rôle de connexion est `immo`, propriétaire de la base et membre de
`migration_owner`, `api_rw` et `pipeline_rw` ; l'API n'endosse jamais `api_rw` (§9.5).

### 7.3 Défauts bloquants avant tout déploiement public

| Défaut | Preuve |
|---|---|
| 41 routes sur 45 sans authentification, dont `POST /api/v1/review/verdicts` | `backend/src/immo/main.py`, aucune dépendance globale |
| Rôle base propriétaire, RLS désarmable par le processus API | `config/postgres/init/10-init-databases.sh:50` |
| Aucun rate limiting, aucun `statement_timeout`, bbox de 1° × 1° acceptée | `routes/explorer.py:68-69` |
| Un seul logger, erreurs SQL converties en 503 sans journal corrélé | `api/errors.py`, `api/middleware.py` |

### 7.4 Recherche

PostgreSQL `pg_trgm` et `unaccent` sur 437 441 adresses BAN. Fonctionne. Aucun moteur externe
n'est envisagé.

---

## 8. Architecture cartographique

Martin sert trois fonctions PostGIS (`tiles.parcels`, `tiles.buildings`,
`tiles.opportunities`) depuis des tables de rendu en EPSG:3857 (`tiles.*_render_v1`),
reconstruites intégralement à chaque publication de release. Rôle `martin` membre de `tiles_ro`,
sans `SELECT` direct sur les tables, auto-publication désactivée : le cloisonnement PostgreSQL est
correct et testé.

En amont, Caddy proxifie `/tiles/v1/*` vers Martin **sans authentification** ; la fonction
`tiles.opportunities` expose `score`, `confidence_level` et `property_unit_id`. Dès qu'un score
serait publié, il serait extractible anonymement à partir du zoom 10. La version 0.1 prévoyait un
`forward_auth` Caddy ; il n'a jamais été écrit.

Performances mesurées sur le 35 (`docs/data/real-map-performance.md`) : tuiles parcelles p95 6 ms
froid, 3,7 ms chaud ; liste API 100 unités 1 839 ms au premier appel.

Systèmes de coordonnées : Lambert-93 (EPSG:2154) pour les calculs, WGS84 pour l'échange, Web
Mercator pour le rendu. Tenu.

---

## 9. Base de données

### 9.1 Schémas

```text
meta          releases, imports, appariements, quarantaine par attribut, revue manuelle   ~11 Go
reference     zones, adresses, parcelles, bâtiments, bâtiments physiques, unités           ~5,5 Go
feature       définitions et 19,9 M de valeurs                                              ~8,5 Go
observation   transactions, DPE, urbanisme, risques, routes                                 ~2,1 Go
tiles         tables de rendu et fonctions MVT                                              ~1,7 Go
scoring       17 tables, toutes vides                                                       plateforme
market        3 tables, vides                                                               plateforme
app           11 tables, vides                                                              plateforme
audit         1 table, vide                                                                 plateforme
```

85 tables, 30 vides. 29 Go pour le seul département 35, doublés en huit jours par l'ajout de
DS-06 à DS-09. Aucun mécanisme ne purge une release remplacée (BUG-08).

### 9.2 Géométries

Canonique en EPSG:2154, géométrie invalide en quarantaine, 13 index GiST, géométrie de rendu
séparée. Tenu.

### 9.3 Rôles

```text
migration_owner   DDL
api_rw            lecture métier, écritures app        — jamais endossé par l'API
pipeline_rw       staging, référentiel, publication    — endossé 21 fois par les pipelines
tiles_ro          lecture du schéma tiles              — endossé par Martin
immo              propriétaire, membre des trois       — rôle de connexion de l'API
```

La matrice de privilèges de la migration 0001 est correcte et décorative tant que l'API se
connecte en `immo`. Correction : un rôle de connexion dédié ou `SET LOCAL ROLE api_rw` en tête de
chaque transaction, avant tout déploiement (§25.2).

### 9.4 Multi-tenant

`ENABLE` + `FORCE ROW LEVEL SECURITY` sur les tables `app.*`, contexte positionné par
`set_config` depuis le `sub` du JWT. Correctement écrit, jamais testé contre une base en CI, et
désarmable par le rôle propriétaire (§9.3).

### 9.5 Partitionnement

Aucun. Envisagé pour `feature.feature_value` et les tables de rendu si quatre départements
étaient importés ; non décidé.

---

## 10. Pipelines de données

### 10.1 Orchestration réelle

Les imports sont des **scripts CLI** lancés par `make` dans le conteneur `dagster-code` utilisé
comme interpréteur Python. Dagster n'orchestre que DS-01 (`assets/cadastre.py`) ; le daemon et le
webserver tournent sans objet. BUG-02 propose de porter les imports vers Dagster ; il est de nouveau
disponible, et la question de garder Dagster est ouverte (§22).

Vingt-cinq cibles `make` couvrent les neuf datasets, les bâtiments physiques, les features
morphologiques et urbaines, les rapports, les listes E8 et E8f, le kit terrain. La séquence
complète de reconstitution du 35 est dans
[`docs/operations/referentiel-local-35.md`](./docs/operations/referentiel-local-35.md).

### 10.2 Étapes réelles

```text
pin (constituer un artefact épinglable quand le producteur n'en publie pas)
  ↓
manifeste : URL datée ou copie archivée nommée, SHA-256   — refus avant téléchargement sinon
  ↓
téléchargement, vérification, archive MinIO, raw_asset
  ↓
staging, normalisation, quarantaine par attribut
  ↓
appariement (identifiants déclarés d'abord, géométrie ensuite, confiance mesurée)
  ↓
acceptation (accepted / display_only / rejected) puis publication : deux gestes manuels distincts
  ↓
features, rapports, listes, documents
```

`cadastre/manifest.py` porte la garde de reproductibilité et sert sept imports sur huit ;
`import_gpu_release.py` la contourne (DS-08 sans checksum ni archive, choix assumé pour 430 Go,
conséquence non écrite jusqu'à l'audit).

### 10.3 Bibliothèques

`httpx`, `tenacity`, `shapely`, `pyproj`, `pyshp`, `py7zr`, `ijson`, `minio`, psycopg 3 avec
`COPY`. PostGIS fait les jointures spatiales. Rien d'autre : ni Polars, ni DuckDB, ni GDAL.

### 10.4 Publication

Une release est importée non publiée ; l'acceptation est un jugement écrit dans
`meta.dataset_release` ; la publication déplace un pointeur et reconstruit référentiel et tables
de rendu dans une transaction (2 min 11 s pour DS-01 sur le 35). Le rollback réactive la release
précédente sans réimport. Tenu.

### 10.5 Qualité

`meta.data_quality_check` (2 021 contrôles), `meta.attribute_quarantine` (40 892 lignes, BAN et
DPE seulement — RNB, BDNB, BD TOPO, DVF, GPU, Géorisques n'écrivent aucune ligne de quarantaine
par attribut), `meta.dataset_coverage_metric` par commune, rapports régénérables dans
`docs/data/`. Pas de Dagster Asset Checks : les contrôles sont dans les scripts.

### 10.6 Résistance à la variété des sources

**Règle applicable à tout pipeline nouveau ou modifié.** Référencée par le Makefile,
`progress.py`, `pin_dpe_release.py` et `pin_sup_release.py`.

Une source publique n'est jamais uniforme. Sur le seul import DS-08, 184 documents d'un même
producteur, au même format normalisé, ont présenté six variantes distinctes : un attribut
obligatoire vide, un encodage non déclaré, des géométries invalides, une limitation de débit, une
erreur au message illisible, et un type de document sans la couche attendue. Ces cas sont
inconnaissables d'avance ; ce qui est évitable, c'est de lancer un lot entier en supposant que
tout ressemblera à l'échantillon testé.

**Avant le premier lot** : inventorier la variété sur un échantillon dispersé, jamais sur les
premiers éléments. Compter la présence de chaque couche ou colonne attendue, les encodages
déclarés, les attributs obligatoires vides, les types de géométrie.

**Pendant le lot** :

1. Un élément échoue sans faire échouer le lot ; l'échec est consigné dans le manifeste ou le
   rapport, pas seulement journalisé.
2. Un échec passager (`429`, délai, connexion coupée) n'est pas un échec définitif : temporisation
   croissante, puis code de sortie distinct pour qu'une relance soit une décision.
3. Un service public se temporise, il ne s'insiste pas.
4. Une valeur absente prend un repli documenté ou reste absente, jamais une valeur devinée ; la
   provenance du repli est persistée.
5. Un écrit progressif plutôt qu'un écrit final : un lot long reprend là où il s'est arrêté.
6. Un message d'erreur nomme sa cause.

**Un lot long annonce son avancement** par tranche de 10 %, via `immo_pipelines.progress.Progress` :

```text
[DS-08] 30 % · 55/184 · 0 échec · 12 min écoulées · ~28 min restantes
```

Le total est celui du travail restant, pas du catalogue ; l'estimation suppose un rythme constant,
et l'écart avec le réel signale une temporisation.

**Une reprise se fonde sur l'état écrit, pas sur un journal.** L'import DS-08 a été interrompu
deux fois, dont une par un `make rebuild` lancé pour un autre ticket : une commande
d'infrastructure est globale, aucun découpage de tickets ne protège d'elle. D'où le garde-fou
`check-no-batch` du Makefile, et la règle : chaque élément est committé séparément, la reprise
interroge la base.

**Un lot interactif n'est pas un lot de production.** L'import DS-08 a duré plusieurs heures,
débit effondré de quarante documents à l'heure à deux en vingt minutes par limitation du
producteur. Un lot partiel est un résultat exploitable dès lors que sa couverture est publiée ;
présenter 152 documents sur 184 comme complets ne le serait pas.

**Ce que la règle interdit** : réparer en silence. Une géométrie invalide est comptée et écartée,
pas corrigée ; un attribut manquant reste manquant avec son motif. Un import qui masque la variété
de sa source produit une couverture qui ment.

---

### 10.7 État des sources au 16 septembre 2026

Le rôle de chaque source dans le produit est en `SPEC.md` §13.1 ; ici, son état d'import.

| ID | Dataset | État |
|---|---|---|
| DS-01 | Cadastre | **acceptée**, publiée, 1 333 327 parcelles |
| DS-02 | RNB | **acceptée**, 514 859 bâtiments physiques |
| DS-03 | BDNB Open | `display_only`, sans rattachement RNB |
| DS-04 | BD TOPO | `display_only` ; identité BD TOPO ↔ RNB acceptée 60/60 |
| DS-05 | BAN | `display_only` ; adresse ↔ parcelle à 24 % d'erreur |
| DS-06 | DVF 2014-2025 | `display_only`, 285 k mutations |
| DS-07 | DPE | `display_only`, 208 k diagnostics, rattachés à 59 % |
| DS-08 | GPU | `display_only`, 152 documents sur 184, sans checksum |
| DS-09 | Géorisques | `display_only` |
| DS-10 à DS-12 | Sitadel, MAJIC PM, BODACC/Sirene | réservés, aucun contrat |
| DS-13 | DPE neufs | `display_only`, 39 072 diagnostics, 18 671 conservés, rattachés au bâtiment à 24 % ; même table que DS-07, filtré hors des mesures (ADR-021) |

---

## 11. Tâches asynchrones applicatives

Aucune. Celery n'a jamais été installé ; Redis tourne sans qu'aucun code s'y connecte. La règle
« pas de Celery tant qu'il n'y a ni export ni alerte » reste ; le retrait de Redis du Compose est
envisagé (§22) et non décidé.

---

## 12. Authentification et autorisation

Keycloak 26.7 fournit l'identité OIDC ; l'API valide les JWT RS256 (`PyJWKClient`, audience,
issuer, claims requis) ; les rôles métier (`platform_admin`, `organization_admin`, `analyst`,
`viewer`) viennent de `app.organization_membership`. Correctement écrit sur 4 routes. Les 41 autres
ne déclarent aucune dépendance de principal. Côté client, `auth.ts` active le renouvellement
silencieux sans `silent_redirect_uri` derrière un `X-Frame-Options: DENY` : la session expirera
en boucle en production. Le realm contient zéro utilisateur ; deux comptes de dev sont provisionnés
par script (`docs/operations/comptes-et-acces.md`).

Ce que la version 0.1 prévoyait et qui n'existe pas : vérification de session par Caddy avant
Martin, MFA, journal d'audit des accès sensibles (`audit.sensitive_access_event` est vide).

---

## 13. Stockage objet

MinIO en conteneur, bucket `raw-sources` avec 6 Go d'archives épinglées : c'est ce qui rend DS-02
réimportable alors que le producteur écrase son fichier. Le backend ne référence pas MinIO ; seuls
les pipelines l'utilisent.

**Envisagé, non décidé** : remplacer MinIO par un bucket S3 compatible chez l'hébergeur. L'audit
§10.6 chiffre l'écart à un facteur 40 à 100 dès qu'on compte le second MinIO qu'exigerait la
réplication hors site. Décision par ADR avant le premier déploiement de la plateforme ou de V2.

---

## 14. Déploiement — jamais exécuté

`DEPLOYMENT.md` décrit le contrat ; `infra/ansible/` et `.github/workflows/deploy-vps.yml`
l'implémentent ; `docs/data/mvp-dod-traceability.md` constate « syntaxe validée, exécution externe
absente ». Trois bloqueurs structurels, reproduits le 15 septembre :

1. **Aucune image n'est construite ni poussée** ; `compose.prod.yaml` exige `API_IMAGE`,
   `PIPELINES_IMAGE`, `WEB_IMAGE` que rien ne définit. Le rendu Compose de production échoue.
2. **Aucune tâche ne fait arriver les données** : le runbook de reconstitution est local, et 29 Go
   ne se réimportent pas en une session.
3. **Les secrets sont installés `0400 root:root`** et bind-montés dans des conteneurs UID 10001 ;
   macOS masque le défaut, Ubuntu ne le fera pas.

S'y ajoutent : `ENV=production` codé en dur dans les quatre appels du workflow (choisir `staging`
déploie en production), déploiement automatique sur tout merge de `main`, `ACME_EMAIL` jamais
transmis à Caddy. Le workflow est rouge à chaque push depuis le 4 septembre.

Le produit actif (V5) n'a besoin d'aucun déploiement. V2 en aura besoin s'il devient un envoi
automatisé ; ce sera l'occasion de décider entre corriger ce chemin ou en choisir un plus court.

### 14.1 Local

`make dev` démarre les 20 services. `compose.dev.yaml` ne monte aucun volume de code : toute
modification backend ou pipeline impose `make rebuild`, qui recrée PostgreSQL. Un Mac 16 Go et
100 Go de disque libre sont le plancher ; PostGIS tourne en émulation x86 sur arm64
(`POSTGRES_PLATFORM=linux/amd64`), ce qui rend les mesures de performance locales non
transposables.

---

## 15. Observabilité

Cinq conteneurs (Prometheus, Loki, Grafana, Alloy, node-exporter) pour : Prometheus qui scrute
Caddy, Keycloak, node-exporter et lui-même — ni l'API, ni Martin, ni PostgreSQL, ni Dagster ;
quatre règles d'alerte sans Alertmanager, donc routées nulle part ; un backend qui n'expose aucun
`/metrics` et ne possède qu'un logger d'accès. Alloy monte le socket Docker en root.

La version 0.1 annonçait OpenTelemetry ; rien n'est instrumenté. G7 (observabilité minimale) est
disponible. `docker logs` suffit tant que rien n'est déployé.

---

## 16. Sécurité

### 16.1 Tenu

Secrets par fichier et SOPS/age, aucun secret dans git, réseaux Compose `internal`,
`no-new-privileges`, UID non-root, images épinglées par tag, aucune injection SQL, validation
d'entrée rigoureuse, UFW et fail2ban dans les rôles Ansible.

### 16.2 Défauts

Voir §7.3 (API), §8 (tuiles), §9.3 (rôle base), §12 (OIDC client), §14 (secrets et workflow).
Plus : API d'administration Caddy sur `0.0.0.0:2019` joignable depuis six conteneurs ; images de
base en tags flottants (`python:3.13-slim`, `node:24-alpine`) donc builds non reproductibles ;
aucun scan de vulnérabilité ; aucune CSP ; polices chargées depuis un CDN tiers ;
`immo_admin_cidrs: 0.0.0.0/0` dans l'exemple de production.

Aucun de ces défauts ne touche le produit actif, qui n'expose rien. Tous bloquent un déploiement
de la plateforme.

---

## 17. Tests et qualité

### 17.1 Ce qui tourne

`make check` en 9 secondes : Ruff lint et format, Pyright strict sur `backend/src` et
`pipelines/src`, 119 tests backend, 334 tests pipelines, 71 tests scripts, `tsc -b`, `vite
build`, vérification OpenAPI, rendu Compose, invariants de diff, budget documentaire.

### 17.2 Ce qui ne tourne pas

**Aucun test ne touche PostgreSQL.** Les 5 925 lignes de SQL des migrations, les politiques RLS,
les fonctions PL/pgSQL, les ~150 requêtes `text()` de l'API et les 2 969 lignes de
`spatial/importer.py` ne sont jamais exécutées par la CI. Douze fichiers de `backend/tests`
vérifient par `grep` que le source contient des chaînes. BUG-09 (400 706 relations fausses) venait
d'une ligne que 305 tests verts n'ont pas pu voir.

Aucun test unitaire front ; 18 tests Playwright hors CI, contre un serveur Vite sans OIDC, dont 6
dépendent d'identifiants réels en base. `pytest-cov` installé, jamais lancé.

### 17.3 Ce qui est décidé

Pour V5 : tests sur fixture de chaque mesure du baromètre, dont « support insuffisant » et
« cohorte non couverte » ; `recompte-preuve` avant publication. Pour la plateforme, avant tout déploiement : un service
PostGIS en CI et une dizaine de tests d'intégration sur migrations, RLS et requêtes spatiales,
en remplacement des tests qui lisent le source.

---

## 18. CI/CD

Un job GitHub Actions, 48 secondes : `make check`, puis `check-diff-invariants` et
`check-commit-ticket` sur la plage poussée. Ne construit aucune image, ne démarre aucune pile, ne
touche pas PostgreSQL, ne lance pas Playwright. `deploy-vps.yml` existe et échoue à chaque push
(§14). Pas de Renovate, pas de SBOM, pas de scan.

---

## 19. Sauvegarde et reprise

`scripts/backup-platform` fait un `pg_dump` de la base `immo` et copie les buckets MinIO dans
`/srv/immo/backups` — sur la machine sauvegardée. Les bases `keycloak` et `dagster` ne sont pas
sauvegardées. Aucune rétention, aucune copie hors site, aucun archivage WAL, restauration jamais
exercée (`docs/operations/backup-restore.md` : RPO et RTO « non mesurés »). ADR-013 (sauvegardes
hors du serveur cible) est acceptée et non appliquée.

Pour le produit actif, la base locale du 35 est reconstituable depuis les sources et MinIO
(`docs/operations/referentiel-local-35.md`) ; MinIO est le seul chemin durable vers les octets de
DS-02. Une copie de `raw-sources` hors de ce poste est le minimum, non fait.

---

## 20. Performance et capacité

Mesuré sur le 35 : base 29 Go, MinIO 6 Go, RSS des 16 conteneurs 4,4 Gio au repos, pic d'import
+3,7 Go, publication DS-01 2 min 11 s, `compute_urban_features` 16 min, import GPU effondré à deux
documents par vingt minutes.

Extrapolation à quatre départements (clé foncière ×4) : 120 Go de base, 150 à 200 Go avec
millésimes et archives, 32 Go de RAM. Coûts d'hébergement estimés dans l'audit §10.6 : 25 à 45 €
par mois pour le 35 avec une pile dégraissée, 49 à 113 € avec la pile actuelle. Rien de tout cela
n'est nécessaire à V5.

---

## 21. Machine learning et vision

Hors périmètre. Aucune plateforme ML, aucun modèle, aucune vision. La règle « pas de ML en
production » reste. Le radar (V2) n'est pas un modèle : une fréquence observée sur une cohorte,
sans combinaison de signaux.

---

## 22. Choix écartés, et révisions envisagées

### 22.1 Écartés, toujours valides

| Choix écarté | Motif |
|---|---|
| Next.js | SSR et SEO sans valeur pour une application authentifiée |
| Google Maps | coût, dépendance |
| Leaflet | rendu vectoriel WebGL moins adapté |
| GeoServer | plus lourd que Martin |
| SQLModel | séparation ORM / contrats préférée — de fait, aucun ORM |
| MongoDB | relationnel et spatial mieux servis par PostGIS |
| Elasticsearch | `pg_trgm` suffit sur 437 k adresses, mesuré |
| Airflow, Celery pour les pipelines | pas de lineage d'assets |
| Kubernetes, microservices | disproportionnés |
| Scoring à la requête | non reproductible |
| Rasters en base | volumétrie |

### 22.2 Envisagés par l'audit, non décidés

Ces révisions demandent chacune une ADR. Elles sont listées pour qu'aucune ne soit faite en
silence.

| Révision | Motif | Condition |
|---|---|---|
| Retirer Redis | référencé par aucun code | immédiat, sans effet fonctionnel |
| Retirer `dagster-webserver` et `dagster-daemon` | un asset, aucune route, aucun healthcheck | sans effet mesurable |
| Retirer la stack d'observabilité | aucun scrutage utile, deux services root | `docker logs` suffit à V5 |
| MinIO → S3 compatible | coût et réplication | si déploiement de V2 |
| Keycloak → JWT signé par l'API | 539 Mio pour zéro utilisateur | si la plateforme reste sans multi-tenant |
| Bind mounts en dev et service Vite | `make rebuild` recrée PostgreSQL | le front se développe de nouveau (ADR-019) |
| PostGIS natif arm64 en local | mesures non transposables | immédiat |
| PostgreSQL 15 → 17 | fin de support 2027 | avant tout déploiement |

---

## 23. Décisions ADR

| ID | Décision | Statut | Note |
|---|---|---|---|
| ADR-001 | Monolithe modulaire pour le métier | Acceptée | — |
| ADR-002 | React/Vite plutôt que Next.js | Acceptée | — |
| ADR-003 | FastAPI + SQLAlchemy plutôt qu'APIFlask/SQLModel | Acceptée | — |
| ADR-004 | PostgreSQL/PostGIS comme source de vérité | Acceptée | — |
| ADR-005 | Martin pour les tuiles MVT | Acceptée | — |
| ADR-006 | Dagster pour les pipelines régionaux | Acceptée, non appliquée (un asset) | — |
| ADR-007 | Celery limité aux tâches applicatives | Acceptée, jamais installé | — |
| ADR-008 | Keycloak/OIDC pour l'identité | Acceptée | — |
| ADR-009 | Tous les workloads dans Docker Compose sur VPS générique déployé par GitHub Actions et Ansible | Acceptée, jamais exécutée | — |
| ADR-010 | Scoring régional pré-calculé et snapshots immuables | Acceptée | — |
| ADR-011 | Lambert-93 pour les calculs, WGS84 pour l'échange, Web Mercator pour les tuiles | Acceptée | — |
| ADR-012 | Pas de ML ni de Kubernetes au MVP | Acceptée | — |
| ADR-013 | Sauvegardes obligatoirement hors du serveur cible | Acceptée, non appliquée | — |
| ADR-014 | SOPS + `age` pour les secrets versionnés | Acceptée | — |
| ADR-015 | Boucle de développement : contrôle déterministe, recompte adversarial, verrou humain déclaré | Acceptée | [note](docs/decisions/ADR-015-boucle-autonome.md) |
| ADR-016 | Le produit devient une intelligence de marché (V5), puis un radar de mise en vente (V2) ; la plateforme est gelée | Acceptée ; gel levé par ADR-019 | [note](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md) |
| ADR-018 | Dégel restreint de l'Explorer, réduit à l'outil local de vérification des données | Remplacée par ADR-019 | [note](docs/decisions/ADR-018-degel-restreint-explorer.md) |
| ADR-019 | Le gel de la plateforme est levé ; déploiement, publication de score et fiches DVF restent bornés | Acceptée | [note](docs/decisions/ADR-019-lever-le-gel-de-la-plateforme.md) |
| ADR-020 | L'unité analysée reste la parcelle, sans regroupement, en attendant E1 | Acceptée | [note](docs/decisions/ADR-020-unite-analysee-parcelle.md) |
| ADR-021 | Les DPE de logements neufs entrent comme source distincte DS-13, hors de toute mesure | Acceptée | [note](docs/decisions/ADR-021-dpe-logements-neufs.md) |

Ce tableau est l'état courant. Le raisonnement vit dans [`docs/decisions/`](docs/decisions/), un
fichier daté par décision. ADR-001 à ADR-014 ont été écrites le 3 août 2026 sans fichier de
raisonnement ; elles ne seront documentées que si elles sont révisées. Toute révision de §22.2
s'écrit ici, avec son fichier.

---

## 24. Séquence d'implémentation

Celle d'ADR-016 pour le baromètre et le radar ; la plateforme avance en parallèle, sans ordre
imposé ([ADR-019](docs/decisions/ADR-019-lever-le-gel-de-la-plateforme.md)) :

1. H1 — mesures du baromètre, reproductibles, recomptées.
2. H2 — document publiable par EPCI.
3. H3 — cinq professionnels ; verrou humain.
4. H4 — avis juridique ; verrou humain, en parallèle.
5. H5 — radar hebdomadaire, colonnes fixées par H4.
6. ADR de sortie de H3 : poursuivre, bifurquer vers V9 (vision, abandon), ouvrir V1 ou V3,
   faire de la plateforme le produit, arrêter.

Les révisions de §22.2 se décident au moment où un déploiement ou un ticket de plateforme les
rend nécessaires, pas avant.

---

## 25. Definition of Done architecture

### 25.1 Produit actif

- toute mesure publiée se régénère par une commande `make`, à l'identique ;
- tout import porte manifeste, SHA-256, version de transformation, run idempotent ;
- tout chiffre de `docs/data/` porte son filtre, son effectif, sa date, et a passé le recompte ;
- aucune donnée nominative dans le baromètre ; colonnes du radar bornées par l'avis juridique ;
- la séquence de reconstitution du 35 couvre les neuf datasets et les calculs dérivés.

### 25.2 Conditions de déploiement de la plateforme

- authentification sur toutes les routes hors `/health` ; rôle base de moindre privilège ;
  `statement_timeout` ; bbox bornée ;
- un service PostGIS en CI et des tests d'intégration sur migrations, RLS et requêtes spatiales ;
- une sauvegarde hors site, une restauration chronométrée ;
- une chaîne de build et de publication d'images, un déploiement exécuté une fois ;
- une décision écrite sur chaque ligne de §22.2.
