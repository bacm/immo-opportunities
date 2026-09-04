# Immo Opportunities

Plateforme B2B de détection et de qualification de candidats immobiliers en Bretagne.

- [Spécification produit](./SPEC.md)
- [Architecture](./ARCHITECTURE.md)
- [Versions d’implémentation](./docs/versions/README.md)
- [Rapports de données](./docs/data/README.md)
- [Déploiement](./DEPLOYMENT.md)

## Prérequis

- Docker Engine avec Compose v2 ;
- Python 3.13 géré par `uv 0.10.6` ;
- Node.js 24 et pnpm 10.33.

## Développement local

Préparer les dépendances et exécuter les contrôles sans démarrer la stack :

```bash
uv sync --all-packages --all-groups
pnpm install
make check
```

Démarrer tous les services :

```bash
make dev
```

Points d’entrée locaux :

| Service | Adresse |
|---|---|
| Application via Caddy | <http://localhost:8080> |
| API directe | <http://localhost:18000/docs> |
| Martin | <http://localhost:13000> |
| Dagster | <http://localhost:13001> |
| MinIO | <http://localhost:9001> |
| Keycloak | <http://localhost:18081/auth/> |
| Grafana | <http://localhost:3000> |

Les secrets locaux sont générés dans `secrets/dev` et ne doivent jamais être utilisés hors développement.

## Commandes principales

```bash
make check          # Python, frontend, OpenAPI et Compose
make openapi        # régénérer contracts/openapi/v1.json
make migrate        # rejouer les migrations dans un conteneur éphémère
make cadastre-fixture # vérifier DS-01 sur PostGIS et MinIO, sans publication
make mvt-benchmark  # mesurer les p95 MVT froids et chauds
make e2e            # tester recherche, carte, liste, fiche et URL dans Chromium
make smoke          # vérifier une stack démarrée
make down           # arrêter la stack
```

## Cadastre DS-01

Le pipeline cadastral est partitionné dynamiquement dans Dagster par release et département. La
release cible du 35 est `2026-06-01 | 35`. Son import reste invisible de l’API et des tuiles tant
qu’elle n’a pas été explicitement acceptée puis publiée.

Après publication, une parcelle et toute sa provenance sont consultables avec :

```text
GET /api/v1/cadastre/parcels/{identifiant_cadastral}
```

La procédure d’import, d’acceptation et de rollback est documentée dans
[`v0.2-cadastre-35.md`](./docs/versions/v0.2-cadastre-35.md#exploitation-locale).
