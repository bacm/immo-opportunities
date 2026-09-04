# Rapport de livraison — MVP connecté v0.7

Date de vérification : 7 août 2026.

## Résultat

Le chemin applicatif est connecté aux API, aux tuiles MVT et aux tables privées. La SPA
utilise OIDC Authorization Code + PKCE, charge les opportunités publiées, expose leurs
preuves/comparables/sources, puis persiste scénario, favori, statut, motif de rejet, note et
revue sans modifier le snapshot commun.

L'activation sur un candidat réel reste bloquée par la v0.6 : les deux définitions de score
sont volontairement `publication_eligible=false` tant que le profilage régional et le
backtest ne sont pas acceptés. L'état vide de production l'indique explicitement ; aucune
fixture n'est substituée à une opportunité manquante.

## Matrice exigences → preuves

| Exigence | Implémentation | Test principal |
|---|---|---|
| FR-001 | recherche API adresse/commune/parcelle et recentrage | `real-map.spec.ts` — recherche réelle |
| FR-002 | couche MVT `tiles.opportunities` et liste API | migration `0013`, parcours connecté |
| FR-003 | sélection et filtres synchronisés dans l'URL | deux parcours Playwright |
| FR-004 | stratégie, score, confiance et curseur opaque | `test_opportunity_list_uses_an_opaque_cursor` |
| FR-005 | fiche agrégée score, espace privé, limites | parcours connecté Playwright |
| FR-006 | contributions positives/négatives et qualité visibles | parcours connecté Playwright |
| FR-007 | `Inconnu` distinct de `0` | test Playwright dédié |
| FR-008 | scénario privé recalculé et snapshot inchangé | tests API et parcours connecté |
| FR-009 | statut, favori, rejet, note et historique auteur/date | tests API, migration et parcours connecté |
| FR-010 | comparables inclus/exclus et motif | parcours connecté Playwright |
| FR-011 | release, producteur, date et source indisponible visibles | parcours connecté Playwright |
| FR-012 | imports et qualité, réservés aux administrateurs et audités | `test_admin_requires_repository_role_check_and_carries_request_id` |

## Sécurité

- Le frontend utilise `oidc-client-ts`, `response_type=code`, le stockage de session et le
  renouvellement automatique. Le client Keycloak impose `pkce.code.challenge.method=S256`.
- L'API vérifie signature RS256 via JWKS, issuer, audience, expiration et présence de `sub`.
- L'organisation ne vient ni de l'URL ni d'un en-tête client : elle est résolue depuis
  `organization_membership` après vérification du `sub`.
- Les rôles métier sont `platform_admin`, `organization_admin`, `analyst`, `viewer` ; un
  `viewer` est refusé sur les écritures.
- Les tables privées activent et forcent RLS. Le nom d'auteur est figé dans l'événement
  immuable, ce qui évite d'ouvrir les identités des autres membres.
- Les notes et scénarios ne figurent pas dans la fonction de tuile commune.

Audit PostgreSQL transactionnel, exécuté avec `api_rw` puis annulé :

```text
alpha_visible=1
beta_leak=0
rls_active=true
NOTICE: rls_write_blocked
NOTICE: immutable_update_blocked
```

Le premier essai du chemin de résolution d'acteur a détecté une récursion de politique RLS.
La migration `20260807_0014` la supprime ; le second essai résout successivement utilisateur,
appartenance et organisation sans fuite.

## OIDC et exploitation

Le realm `immo` a été importé dans Keycloak 26.7.0 et son document de découverte a répondu.
Il annonce Authorization Code, Refresh Token et les challenges PKCE `plain`/`S256`; le client
de l'application restreint PKCE à `S256`. Les tests API couvrent jeton absent et session
expirée. La restauration de l'URL après callback et les erreurs de renouvellement sont gérées
dans `auth.ts`.

Keycloak reste l'autorité de création des identités. Après création d'un compte, son `sub`
est associé à une organisation et un rôle sans stocker de mot de passe :

```bash
uv run --package immo-backend python backend/scripts/provision_member.py \
  --subject <sub-keycloak> --organization-id org:<slug> \
  --organization-name <nom> --display-name <nom> --role analyst
```

## Vérifications automatisées

- backend : 58 tests réussis ;
- pipelines : 47 tests réussis ;
- frontend : TypeScript strict et build Vite réussis ;
- Playwright : 3 parcours réussis — recherche réelle, workflow connecté, valeur inconnue et
  contrôle des noms accessibles ; le workflow couvre scénario, statut, note, URL, mobile et
  un budget de 1 s sous API interceptée ;
- accessibilité : navigation clavier héritée, noms accessibles contrôlés automatiquement et
  information jamais portée par la couleur seule ;
- configuration Compose validée ;
- migration `0011 → 0012 → 0013 → 0014` appliquée sur PostgreSQL/PostGIS réel ;
- OpenAPI et client TypeScript régénérés.

La commande officielle `make check` réussit intégralement (format, lint, typage Python,
58 tests backend, 47 tests pipelines, typage/build frontend, OpenAPI et Compose).

Le budget Playwright utilise des réponses interceptées pour rendre le test déterministe. Il
ne constitue pas une mesure p95 de production. Les p95 liste/fiche devront être mesurés avec
des opportunités v0.6 réellement publiées ; cette limite empêche de revendiquer aujourd'hui
la démonstration métier complète sur données réelles.

## Observabilité

Chaque réponse API contient `X-Request-ID` et `Server-Timing`. Le journal d'accès reprend
request ID, méthode, chemin, statut et durée ; Alloy collecte les journaux Docker dans Loki.
Les consultations administratives sensibles écrivent en plus un événement d'audit immuable
avec organisation, acteur et request ID.
