# Comptes et accès — se connecter à l'application

**Mis à jour le 11 septembre 2026** · Résout [BUG-10](../backlog/BUG-10-aucun-compte-utilisateur.md).

Avant ce document, personne ne pouvait se connecter, et la raison n'était écrite nulle part. Le
réalm ne contenait aucun compte, l'inscription était fermée, les trois tables applicatives étaient
vides, et l'existence même d'un administrateur Keycloak n'était connue de personne.

## En une commande

```bash
make dev                      # la pile doit tourner
./scripts/provision-dev-accounts
./scripts/check-oidc-login     # vérifie le vrai chemin, de bout en bout
```

Deux comptes de développement sont alors utilisables, dans **deux organisations distinctes** —
l'isolation ne se teste qu'à deux :

| Compte | Organisation | Rôle | Mot de passe |
|---|---|---|---|
| `dev-alpha` | `org:dev-alpha` | `analyst` | `secrets/dev/keycloak_dev_alpha_password` |
| `dev-beta` | `org:dev-beta` | `analyst` | `secrets/dev/keycloak_dev_beta_password` |

## L'administrateur Keycloak

Il existe depuis le premier démarrage et s'appelle **`immo-dev-admin`**, dans le réalm `master`.
Ses identifiants sont dans `secrets/dev/keycloak_admin_user` et
`secrets/dev/keycloak_admin_password`, générés par `scripts/init-dev-secrets`. La console est sur
<http://localhost:8080/auth/admin/>.

Ces secrets sont en base64. Pour obtenir un jeton à la main, **encoder les paramètres** :

```bash
curl -X POST http://localhost:8080/auth/realms/master/protocol/openid-connect/token \
  -d client_id=admin-cli -d grant_type=password \
  --data-urlencode "username=$(cat secrets/dev/keycloak_admin_user)" \
  --data-urlencode "password=$(cat secrets/dev/keycloak_admin_password)"
```

Avec `-d` au lieu de `--data-urlencode`, un `+` du mot de passe devient une espace et la réponse
est `invalid_grant / Invalid user credentials` — un message qui accuse le mot de passe alors que
la faute est dans la requête.

## Ouvrir l'accès à un compte réel

L'application **ne provisionne rien à la première connexion**, et c'est un choix : l'accès est
nominatif, et un compte qui se crée seul est un compte que personne n'a décidé d'ouvrir. Un
utilisateur authentifié mais non provisionné reçoit un **403 explicite**, jamais un accès partiel.

Une fois le compte créé dans Keycloak, relever son identifiant — c'est le `sub` du jeton — puis :

```bash
docker compose exec api python -m immo.accounts \
  --subject 3744923a-e0f9-4561-94d2-d9068186816d \
  --display-name "Prénom Nom" \
  --email personne@exemple.fr \
  --organization-id org:mon-organisation \
  --organization-name "Mon organisation" \
  --role analyst
```

Rôles acceptés : `platform_admin`, `organization_admin`, `analyst`, `viewer`. La commande est
idempotente.

## Pourquoi cette commande n'a besoin d'aucun privilège

Les trois tables portent une RLS **forcée**, qui s'applique même au propriétaire :

| Table | Condition de la politique |
|---|---|
| `app.organization` | `id = current_setting('app.current_organization_id')` |
| `app.app_user` | `external_subject = current_setting('app.current_subject')` |
| `app.organization_membership` | l'utilisateur **et** l'organisation courants |

Créer la première organisation paraît donc impossible, et c'est ce qui a laissé la base vide. Mais
les politiques comparent à des **variables de session**, pas à un état déjà présent : il suffit de
se déclarer être ce qu'on s'apprête à insérer.

La commande tourne donc avec le rôle applicatif ordinaire. Pas de `BYPASSRLS`, pas de
superutilisateur, pas de politique désactivée le temps du provisionnement — et un test échoue si
quelqu'un les réintroduit. La conséquence est voulue : **on ne peut créer qu'un compte dont on
prend l'identité dans la même transaction.**

## Ce que `check-oidc-login` vérifie, et pourquoi il existe

Il suit le flux du navigateur — code d'autorisation avec PKCE sur le client public `immo-web` —
pour les deux comptes, puis appelle l'API avec chaque jeton et vérifie que les acteurs résolus
appartiennent à **deux organisations différentes**.

Il existe parce que rien ne l'exerçait. `auth.py` court-circuite OIDC en `development` et `test`,
et le front en fait autant (`import.meta.env.DEV`). Tout passait par un principal fabriqué, et la
chaîne réelle n'avait jamais servi.

Aucun assouplissement n'a été nécessaire : pas de *direct access grant* ouvert pour les besoins du
contrôle, ce qui aurait affaibli le réalm pour prouver qu'il fonctionne.

Il est **hors de `make check`** : il exige la pile locale complète.

### Deux pièges rencontrés, et leurs messages trompeurs

| Symptôme | Cause réelle |
|---|---|
| `cookie_not_found` | Keycloak pose ses cookies en `Secure; SameSite=None`. Un client HTTP ne les renvoie pas en clair ; un navigateur, si, car il traite la boucle locale comme un contexte sûr. |
| `invalid_request`, connexion pourtant réussie | Compte sans prénom ni nom : Keycloak impose une action `VERIFY_PROFILE` et n'émet aucun code. Le fichier de réalm portait ces champs, la création par API les omettait. |
| `401` sur l'API avec un jeton valide | Jeton émis sur le port direct du conteneur. L'API valide l'émetteur contre `oidc_issuer`, qui passe par Caddy. Le rejet est correct. |

## Installation neuve contre base existante

`kc.sh --import-realm` n'importe **que les réalms absents**. Ajouter un compte à
`config/keycloak/realm-immo.json` ne produit donc rien sur une base déjà initialisée.

Le fichier reste la déclaration de référence pour une installation neuve ;
`provision-dev-accounts` réconcilie l'existant par l'API d'administration. Keycloak attribue
lui-même les identifiants et ignore ceux qu'on propose : le script résout donc chaque compte par
son nom d'utilisateur plutôt que de figer un `sub` qui ne vaudrait qu'à l'import initial.

## Ce qui reste ouvert

- **Aucun rôle de réalm n'est déclaré**, et `auth.py` n'en lit aucun. L'autorisation vient
  entièrement de `organization_membership.role`. C'est cohérent et volontairement minimal, mais à
  revoir si une décision doit un jour être prise avant la résolution de l'acteur.
- **`registrationAllowed` reste à `false`**, et doit le rester : l'accès est nominatif B2B.
- **Le pilote [G8](../backlog/G8-pilote-trois-professionnels.md)** demandera trois comptes réels,
  dans une ou trois organisations selon le protocole retenu. La procédure ci-dessus suffit.
