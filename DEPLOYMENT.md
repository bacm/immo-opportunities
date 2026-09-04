# Immo Opportunities — contrat de déploiement VPS

**Statut :** infrastructure initiale du MVP Bretagne  
**Cible :** VPS Ubuntu 24.04 x86_64 générique  
**Orchestrateur de déploiement :** GitHub Actions + Ansible + Docker Compose

## 1. Périmètre

Le fournisseur livre uniquement un VPS Ubuntu accessible en SSH et le DNS public. Le dépôt ne dépend d'aucune API cloud et ne provisionne ni compte fournisseur, ni VM, ni facturation.

À partir du serveur vierge, le dépôt automatise :

- la configuration SSH, UFW, fail2ban et les mises à jour de sécurité ;
- l'installation de Docker Engine et Compose v2 ;
- la création des répertoires persistants ;
- le déchiffrement en mémoire des secrets SOPS côté runner ;
- l'installation des secrets sur le VPS en fichiers `0400` ;
- le déploiement Compose et l'attente des healthchecks ;
- le démarrage de la stack au reboot via systemd.

## 2. Topologie

```text
GitHub Actions
  └─ conteneur ops (Ansible + SOPS + age)
       └─ SSH avec vérification known_hosts
            └─ VPS Ubuntu 24.04
                 ├─ Caddy : 80/443
                 ├─ PostgreSQL/PostGIS
                 ├─ Redis
                 ├─ MinIO + init
                 ├─ Keycloak
                 ├─ FastAPI + migration Alembic
                 ├─ Martin
                 ├─ Dagster webserver, daemon et code location
                 └─ Prometheus, Loki, Grafana, Alloy
```

Un conteneur héberge un seul service long. PostgreSQL, Redis, MinIO et chaque composant d'observabilité ont chacun leur conteneur et leur stockage propre.

Seuls 80/443 sont publics dans Compose. Les services de données communiquent par réseaux internes. SSH est géré par l'hôte et le pare-feu du fournisseur.

## 3. Persistance

Par défaut :

| Donnée | Chemin VPS |
|---|---|
| PostgreSQL | `/srv/immo/postgres` |
| Objets MinIO | `/srv/immo/objects` |
| Redis et Caddy | `/srv/immo/runtime` |
| Secrets | `/etc/immo/secrets` |
| Manifests déployés | `/opt/immo` |

Les répertoires sont des bind mounts du disque du VPS. Des disques additionnels peuvent être montés par UUID avec le rôle `storage`, uniquement lorsqu'ils sont explicitement déclarés. Un disque existant n'est jamais reformaté implicitement.

## 4. Flux GitHub Actions

Le workflow [deploy-vps.yml](./.github/workflows/deploy-vps.yml) possède trois modes :

- lancement manuel `staging` ou `production` avec `bootstrap=true` pour un Ubuntu vierge ;
- lancement manuel sans bootstrap vers l'un des deux environnements ;
- push sur `main` vers `production`, pour un déploiement idempotent.

Le job cible l'environnement GitHub sélectionné, utilise uniquement `contents: read`, refuse les
paramètres manquants, conserve la vérification stricte de la clé d'hôte et sérialise les
déploiements par environnement avec `concurrency`.

Les credentials sont matérialisés uniquement dans le répertoire temporaire du runner, montés en lecture seule dans le conteneur opérateur, puis supprimés avec `if: always()`.

## 5. Configuration GitHub

Variables : `VPS_HOST`, `VPS_USER`, `VPS_SSH_PORT`, `APP_DOMAIN`, `ACME_EMAIL`, `ADMIN_CIDRS_JSON`.

Secrets : `VPS_SSH_PRIVATE_KEY`, `VPS_SSH_HOST_KEY`, `SOPS_AGE_KEY`.

Le fichier `secrets/production.sops.yaml` chiffré doit être commité. Les valeurs déchiffrées et la clé privée `age` ne doivent jamais entrer dans Git.

Il est recommandé d'activer une approbation obligatoire sur l'environnement `production`.

## 6. Réseau SSH

Un runner GitHub hébergé doit pouvoir joindre le port SSH du VPS. Deux stratégies sont supportées :

1. SSH accessible publiquement, authentification par clé uniquement, root et mots de passe désactivés, fail2ban actif ;
2. runner auto-hébergé ou réseau privé disposant d'un CIDR fixe, renseigné dans `ADMIN_CIDRS_JSON`.

La deuxième stratégie offre une meilleure réduction de surface réseau. La première reste le chemin de démarrage le plus simple pour un VPS générique.

## 7. Sauvegarde et restauration

Une restauration complète exigera :

1. créer un Ubuntu 24.04 vierge et y installer la clé SSH de déploiement ;
2. faire pointer le DNS vers sa nouvelle IP ;
3. vérifier et remplacer `VPS_SSH_HOST_KEY` ;
4. lancer le workflow avec `bootstrap=true` ;
5. restaurer PostgreSQL et MinIO depuis la cible hors site ;
6. exécuter les smoke tests et contrôler l'observabilité.

Le déploiement installe les timers `immo-backup.timer` et `immo-pilot-metrics.timer`. PostgreSQL et
les objets MinIO sont sauvegardés ensemble dans `/srv/immo/backups`; la réplication MinIO hors site
reste configurée avec des identifiants dédiés. La procédure, le test en conteneurs jetables et les
conditions de preuve sont détaillés dans
[`docs/operations/backup-restore.md`](./docs/operations/backup-restore.md).

Le code du mécanisme ne vaut pas preuve de restauration. La production reste interdite tant qu'un
rapport de drill sur une sauvegarde réelle et un redéploiement VPS vierge n'ont pas mesuré RPO/RTO.
