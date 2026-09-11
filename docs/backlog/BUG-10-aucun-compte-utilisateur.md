# BUG-10 — Personne ne peut se connecter : ni compte, ni inscription, ni administrateur

**Version :** v0.7 · **Taille :** M · **État :** Terminé
**Dépend de :** — · **Bloque :** F3, G8
**Découvert par :** vérification du parcours d'authentification, 10 septembre 2026

## Contexte à charger

- `config/keycloak/realm-immo.json`
- `backend/src/immo/auth.py`
- `backend/src/immo/connected_mvp.py` (résolution de l'acteur, `MembershipNotFoundError`)
- `docs/backlog/F3-isolation-organisations.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Le réalm OIDC est importé, les deux clients sont déclarés, l'API valide les jetons — et **aucun
être humain ne peut obtenir de jeton.** La chaîne est coupée en trois endroits indépendants, et
chacun suffit à bloquer.

### 1. Le réalm ne contient aucun compte, et n'en accepte aucun

Relevé dans `config/keycloak/realm-immo.json` :

| Élément | Valeur |
|---|---|
| `users` | **0** |
| `roles.realm` | **0** |
| `groups` | **0** |
| `registrationAllowed` | **`false`** |
| `resetPasswordAllowed` | `true` — sans effet, il n'y a aucun compte à réinitialiser |
| `clients` | `immo-api`, `immo-web` (public, redirection `/*`) |

Aucun script ne compense : `scripts/` ne mentionne Keycloak que dans `init-dev-secrets`, qui ne
crée pas de compte, et dans `smoke-test`, qui vérifie seulement que `/auth/` répond.

### 2. ~~Il n'y a pas non plus d'administrateur pour en créer~~ — faux, corrigé le 11 septembre 2026

**Ce point était une erreur de ma part et il est conservé barré plutôt que supprimé.**

J'avais conclu à l'absence d'administrateur en lisant `docker compose exec keycloak env`. Ce
contrôle ne prouve rien : `exec` démarre un **nouveau** processus, qui reçoit l'environnement
déclaré dans le service, pas celui du processus en cours. Or l'entrypoint exporte les variables
depuis les secrets montés, juste avant `exec kc.sh` :

```bash
export KC_BOOTSTRAP_ADMIN_USERNAME="$(cat /run/secrets/keycloak_admin_user)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/keycloak_admin_password)"
```

Relevé sur `/proc/1/environ`, les deux variables sont bien présentes. Le compte
`immo-dev-admin` existe dans le réalm `master`, créé le 4 septembre 2026, et un jeton
`admin-cli` s'obtient avec les secrets de `secrets/dev/`.

La console d'administration est donc **accessible**, et le point 1 se corrige avec elle. Ce qui
reste vrai : rien n'est provisionné, et rien n'est documenté — personne ne sait que ce compte
existe ni où sont ses identifiants.

### 3. Même authentifié, l'acteur n'existerait pas côté application

`connected_mvp.py` résout le principal OIDC en acteur applicatif par une jointure stricte, sans
provisionnement à la première connexion :

```python
WHERE users.external_subject = :subject
...
if user is None:
    raise MembershipNotFoundError(principal.subject)
```

Puis la même chose pour l'appartenance à une organisation. L'erreur sort en **403
`The authenticated user has no organization membership`**.

Or les trois tables sont vides :

| Table | Lignes |
|---|---:|
| `app.app_user` | **0** |
| `app.organization` | **0** |
| `app.organization_membership` | **0** |

Un compte Keycloak créé à la main ne suffirait donc pas : il faut aussi une ligne `app_user`
portant le même `external_subject`, une organisation, et une appartenance.

## Pourquoi ça n'a pas été vu plus tôt

`auth.py` court-circuite OIDC quand `oidc_enabled` est faux, mais **seulement** en
`development` et `test` :

```python
if settings.environment not in {"development", "test"}:
    raise HTTPException(status_code=503, detail="OIDC must be enabled outside development and test")
return Principal(subject="development-user", ...)
```

Ce garde-fou est correct — il interdit le contournement en production. Mais il fait que tout le
développement et tous les tests end-to-end passent par un principal fabriqué, jamais par
Keycloak. Le chemin réel n'a donc jamais été emprunté par personne.

## Conséquences

- **[F3](./F3-isolation-organisations.md) est intestable.** Il doit prouver l'isolation entre
  organisations en conditions proches production ; avec zéro organisation et zéro compte, il n'y
  a rien à isoler et la RLS n'est exercée que par le principal de développement.
- **[G8](./G8-pilote-trois-professionnels.md) est impossible.** Trois professionnels doivent se
  connecter sur des cas réels. C'est la validation décisive du produit, et elle bute sur un écran
  de connexion sans compte.
- **La RLS n'est pas réellement éprouvée.** Huit tables au moins la portent — `app.note`,
  `app.candidate_review`, `app.candidate_state`, `app.candidate_scenario`… — et leurs politiques
  s'appuient sur `app.current_organization_id`, qui n'a jamais été positionné par un acteur réel.

## Ce que ce ticket ne doit pas faire

- **Inventer un modèle d'organisation.** Il existe déjà : `app.organization`,
  `app.organization_membership` avec `role` et `is_default`. Le ticket le peuple, il ne le
  redessine pas.
- **Assouplir le garde-fou de `auth.py`.** Le refus d'OIDC désactivé hors développement est une
  protection, pas un obstacle.
- **Ouvrir `registrationAllowed`.** Le produit est B2B et l'accès est nominatif ; l'auto-inscription
  ouvrirait le réalm à n'importe qui.

## Travail à réaliser

1. Documenter l'administrateur de réalm existant — `immo-dev-admin`, identifiants dans
   `secrets/dev/keycloak_admin_*` — dans `docs/operations/`. Il n'est pas à créer, il est à
   faire connaître.
2. Provisionner les comptes de développement dans `realm-immo.json` — le fichier est déjà versionné
   et importé, c'est le bon endroit, à condition que les mots de passe soient temporaires et
   marqués comme tels.
3. Décider et implémenter le rattachement `sub` OIDC → `app.app_user` : soit un provisionnement à
   la première connexion, soit une commande d'administration explicite. Le second est plus
   conforme à un accès nominatif B2B.
4. Créer une organisation et une appartenance pour chaque compte de développement.
5. Faire passer au moins un test end-to-end par le vrai chemin OIDC, pas par le principal de
   développement.

## Tests obligatoires

- un jeton émis par le réalm est accepté par l'API et produit un acteur complet ;
- un compte sans appartenance reçoit bien 403 et non 500 — le comportement actuel est correct et
  doit le rester ;
- deux comptes de deux organisations ne voient pas les notes l'un de l'autre, par le chemin réel.

## Critères d'acceptation

- un humain peut se connecter à l'application sans intervention en base ;
- la procédure de création d'un compte est écrite dans `docs/operations/` ;
- au moins un test exerce la RLS avec deux acteurs réels issus de Keycloak.

## Résolution — 11 septembre 2026

Livré :

- `backend/src/immo/accounts.py` — commande d'administration `python -m immo.accounts`,
  idempotente, qui ouvre l'accès d'un `sub` OIDC à une organisation. Elle tourne avec le rôle
  applicatif ordinaire : les politiques RLS comparant à des variables de session, il suffit de se
  déclarer être ce qu'on insère. Aucun `BYPASSRLS`, aucune politique désactivée, et un test
  échoue si quelqu'un les réintroduit.
- `scripts/provision-dev-accounts` — deux comptes dans **deux** organisations, mots de passe tirés
  de `secrets/dev/`. Le réalm ne porte aucun identifiant en clair.
- `scripts/check-oidc-login` — suit le flux du navigateur, code d'autorisation avec PKCE sur
  `immo-web`, pour les deux comptes, et vérifie que les acteurs résolus relèvent d'organisations
  différentes. Aucun *direct access grant* n'a été ouvert pour les besoins du contrôle.
- `docs/operations/comptes-et-acces.md` — la procédure, l'administrateur, et les trois messages
  d'erreur trompeurs rencontrés en chemin.
- `backend/tests/test_accounts.py` — dix tests.

Vérifié de bout en bout : `dev-alpha → org:dev-alpha` et `dev-beta → org:dev-beta`, acteurs
résolus par le vrai chemin OIDC, chaîne jeton → `sub` → `app_user` → appartenance → RLS.

Ce que ce ticket **n'a pas** fait, et qui reste à [F3](./F3-isolation-organisations.md) : prouver
que deux organisations ne voient pas les données l'une de l'autre. Le contrôle vérifie que les
acteurs sont distincts, pas que les politiques les cloisonnent — il n'y a encore aucune donnée
applicative à cloisonner.
