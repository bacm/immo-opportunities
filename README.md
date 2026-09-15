# Immo Opportunities

Intelligence de marché immobilier à partir de données publiques, sur l'Ille-et-Vilaine. Le
produit décidé le 15 septembre 2026 ([ADR-016](./docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md))
est un **baromètre du marché par EPCI**, puis un **radar hebdomadaire de mise en vente** fondé sur
le dépôt des diagnostics énergétiques. La plateforme cartographique écrite avant cette décision
existe dans le dépôt et est gelée.

- [Spécification produit](./SPEC.md) — version 1.0, provisoire jusqu'aux premiers entretiens
- [Architecture](./ARCHITECTURE.md) — ce qui existe, ce qui est gelé, ce qui est défectueux
- [Audit du 15 septembre 2026](./docs/audit-critique-2026-09-15.md) — pourquoi
- [Backlog et chemin critique](./docs/backlog/README.md)
- [Rapports de données](./docs/data/README.md)
- [Reconstituer la base du 35](./docs/operations/referentiel-local-35.md)

## État en une ligne

Référentiel spatial du 35 accepté (1,33 M parcelles, 515 k bâtiments physiques), quatre sources
métier importées en `display_only` (285 k mutations, 208 k DPE), aucun utilisateur, aucun score
publié, aucun déploiement. Prochaine étape : [H1](./docs/backlog/H1-barometre-marche-35-mesures.md),
le baromètre.

## Prérequis

- Docker Engine avec Compose v2, 16 Go de RAM et 100 Go de disque libre pour la base du 35 ;
- Python 3.13 géré par `uv` ;
- Node.js 24 et pnpm 10 (plateforme gelée seulement).

## Développement local

```bash
uv sync --all-packages --all-groups
pnpm install
make check          # lint, typecheck, 524 tests, OpenAPI, Compose, invariants — 9 s, sans base
make dev            # démarre les 20 services ; la base part vide
```

La base ne se versionne pas : la séquence qui la reconstitue est dans
[`docs/operations/referentiel-local-35.md`](./docs/operations/referentiel-local-35.md).

Points d'entrée locaux : application via Caddy sur <http://localhost:8080> (utiliser ce nom
d'hôte, pas `127.0.0.1`), API sur <http://localhost:18000/docs>, Dagster sur
<http://localhost:13001>, MinIO sur <http://localhost:9001>, Keycloak sur
<http://localhost:18081/auth/>, Grafana sur <http://localhost:3000>.

## Commandes principales

```bash
make check                # contrôles de qualité, sans base
make backlog              # régénère docs/backlog/README.md
make dod ID=<ticket>      # ce qui est mécanisable de la DoD d'un ticket
make rebuild              # reconstruit les images ; recrée PostgreSQL, vérifier qu'aucun lot ne tourne
make dvf-import           # exemples d'imports ; liste complète dans le Makefile et le runbook
make exploratory-candidates COMMUNE=35051
make biens-en-vente COMMUNE=35051
```

Les cibles du baromètre (`market-barometer`, `market-barometer-kit`) arrivent avec H1 et H2.

## Règles

Toute modification de code passe par un ticket de `docs/backlog/`. Les règles non négociables
(valeur manquante jamais convertie en zéro, aucun seuil inventé, checksum avant import, recompte
avant publication) sont dans [`CLAUDE.md`](./CLAUDE.md).
