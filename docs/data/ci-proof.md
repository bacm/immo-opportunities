# Preuve d'exécution du workflow CI sur GitHub

**Date :** 15 septembre 2026
**Ticket :** [A1](../backlog/A1-preuve-ci-github.md) · **Version :** v0.1 Foundation

## Le run

| | |
|---|---|
| Workflow | `.github/workflows/ci.yml`, job `Quality and contracts` |
| Run | <https://github.com/bacm/immo-opportunities/actions/runs/34928242516> |
| Commit | `7225348` sur `main` |
| Événement | `push` — 85 commits, de `aae5ef1` à `7225348` |
| Résultat | **success** |
| Durée | 48 s, du 15 septembre 2026 à 04:17:16 UTC à 04:18:04 UTC |
| Runner | `ubuntu-24.04` |

Toutes les étapes en succès, dans l'ordre : `Check out repository`, `Install Python 3.13`,
`Install uv`, `Sync Python workspace`, `Check Python`, `Verify OpenAPI contract`, `Install pnpm`,
`Install Node.js 24`, `Install frontend dependencies`, `Check frontend`, `Validate Compose`,
`Check diff invariants`.

## Ce que le run couvre, comparé à `make check`

Le critère d'acceptation d'A1 est que la CI exécute **au moins** les contrôles de `make check`. La
correspondance est exacte, cible par cible :

| Cible de `make check` | Étape CI | Contenu |
|---|---|---|
| `python-check` | Check Python | Ruff lint et format, Pyright strict sur `backend/src` et `pipelines/src`, pytest backend, pipelines et `scripts/tests` |
| `openapi-check` | Verify OpenAPI contract | `contracts/openapi/v1.json` régénéré et comparé |
| `web-check` | Check frontend | `tsc -b` et build Vite |
| `config` | Validate Compose | configurations dev et prod, réglages PostgreSQL déclarés |
| `invariants` | Check diff invariants | interdits de `CLAUDE.md` sur les lignes ajoutées des 85 commits |

Aucun contrôle n'a été réduit ni désactivé pour obtenir ce vert.

## Ce que le run ne couvre pas

À énoncer, sinon un vert se lit comme une couverture qu'il n'a pas :

- **Pas de PostgreSQL ni de PostGIS.** Les tests exécutés sont hors base ; les tests d'intégration
  décrits par [`ARCHITECTURE.md` §18.1](../../ARCHITECTURE.md#18-cicd) n'existent pas encore en CI.
- **Pas de Playwright.** `make e2e` ne tourne qu'en local, contre un serveur Vite.
- **Pas de build d'image ni de scan de vulnérabilités**, également prévus par §18.1.
- **Pas de démarrage de stack.** Les tests obligatoires de v0.1 qui l'exigent — migration et
  rollback, healthchecks, isolation du rôle `tiles_ro` — restent établis par la validation locale
  du 4 août 2026.

## Historique et constat corrigé

Le ticket A1 partait du constat que « le dépôt n'a qu'un seul commit », donc qu'aucun run n'avait
pu être déclenché. C'était faux sur les deux points. Le workflow CI compte **six runs**, dont trois
verts :

| Commit | Résultat | Date |
|---|---|---|
| `7225348` | success | 15 septembre 2026 |
| `615fd98` | success | 8 septembre 2026 |
| `0e033d2` | success | 4 septembre 2026 |
| `d10f9a6`, `7f1687a`, `ac0a57a` | failure | 4 septembre 2026 |

Ce qui manquait n'était donc pas l'exécution mais **son rattachement aux preuves de v0.1** — le
titre du ticket le disait, le diagnostic l'avait perdu de vue. Le run du 15 septembre est retenu
comme preuve parce qu'il est le premier à couvrir l'intégralité de `make check`, l'étape
d'invariants ayant été ajoutée le même jour.

## Un point ouvert, hors A1

Le workflow `deploy-vps.yml` **échoue à chaque push** depuis au moins le 4 septembre, à l'étape
`Validate required deployment settings` : les variables `VPS_*` ne sont pas configurées sur le
dépôt. C'est le comportement attendu d'un dépôt sans cible de production, et A1 exclut
explicitement ce workflow de son périmètre — il relève de [G6](../backlog/G6-exploitation-restauration.md).

Il mérite néanmoins d'être traité, pour une raison qui n'est pas cosmétique : un workflow rouge en
permanence sur la branche par défaut rend invisible le jour où il devient rouge pour une vraie
raison.
