# Immo Opportunities — déploiement VPS

**Statut :** jamais exécuté ; interdit pour un tiers tant que les conditions d'`ARCHITECTURE.md` §25.2 ne sont pas remplies ([ADR-019](./docs/decisions/ADR-019-lever-le-gel-de-la-plateforme.md)).
**Cible décrite :** VPS Ubuntu 24.04 x86_64 générique, GitHub Actions + Ansible + Docker Compose.

Le produit actif (baromètre V5) n'a besoin d'aucun déploiement : il tourne sur la base locale et
produit des documents. Ce contrat redevient pertinent si le radar (V2) exige un envoi
automatisé, ou quand la plateforme, de nouveau développée, visera un premier déploiement. Il est
conservé tel quel, avec ses bloqueurs.

## 1. Ce qui est écrit

Les rôles Ansible `base`, `storage`, `secrets` et `immo_stack` (`infra/ansible/`) automatisent
SSH, UFW, fail2ban, mises à jour, Docker, répertoires persistants, installation des secrets SOPS
déchiffrés en mémoire, déploiement Compose et unité systemd. Le workflow
`.github/workflows/deploy-vps.yml` les pilote depuis un conteneur opérateur (`docker/ops`).

Topologie visée : Caddy 80/443 devant web, API, Martin et Keycloak ; PostgreSQL, Redis, MinIO,
Dagster et l'observabilité sur réseaux internes ; persistance sous `/srv/immo`, secrets sous
`/etc/immo/secrets`, manifestes sous `/opt/immo`.

## 2. Pourquoi ça ne déploie pas

Reproduit le 15 septembre 2026 (audit §10.3) :

1. **Aucune image applicative n'est construite ni poussée.** `compose.prod.yaml` exige
   `API_IMAGE`, `PIPELINES_IMAGE` et `WEB_IMAGE` ; le gabarit `immo.env.j2` ne les définit pas ;
   aucun workflow ne fait `docker push`. Le rendu Compose de production échoue sur
   `required variable API_IMAGE is missing`.
2. **Aucune tâche ne charge les données.** Le runbook de reconstitution est local ; 29 Go ne
   s'importent pas en une session SSH.
3. **Les secrets seront illisibles.** Installés `0400 root:root`, bind-montés dans des conteneurs
   UID 10001 ; VirtioFS masque le défaut sur macOS, pas Ubuntu.
4. **`ENV=production` est codé en dur** dans les quatre appels `make` du workflow : choisir
   `staging` déploie en production, et tout merge sur `main` déclenche un déploiement production
   sans approbation.
5. `secrets/production.sops.yaml` n'existe pas ; le workflow est rouge à chaque push depuis le 4
   septembre.
6. `ACME_EMAIL` n'est pas transmis au conteneur Caddy : certificat sans contact.

## 3. Ce qui manque avant un premier déploiement réel

- une chaîne de build et de publication d'images (GHCR), et la variable de version dans le `.env`
  déployé ;
- un chemin de chargement des données : restauration d'un dump et de `raw-sources`, ou imports
  planifiés ;
- les corrections de sécurité de `ARCHITECTURE.md` §7.3 et §9.3, sans quoi 41 routes et les
  tuiles sont publiques ;
- une sauvegarde hors site et une restauration chronométrée (`docs/operations/backup-restore.md`
  : RPO et RTO non mesurés ; `keycloak` et `dagster` non sauvegardés ; dumps sur la machine
  sauvegardée, sans rétention) ;
- une décision sur la pile à déployer (`ARCHITECTURE.md` §22.2) : dix conteneurs sur seize n'ont
  aucun usage démontré.

## 4. Configuration GitHub, si le chemin est repris

Variables : `VPS_HOST`, `VPS_USER`, `VPS_SSH_PORT`, `APP_DOMAIN`, `ACME_EMAIL`,
`ADMIN_CIDRS_JSON`. Secrets : `VPS_SSH_PRIVATE_KEY`, `VPS_SSH_HOST_KEY`, `SOPS_AGE_KEY`. Le
fichier `secrets/production.sops.yaml` chiffré doit être commité ; la clé privée `age` jamais.
Activer l'approbation obligatoire sur l'environnement `production`. Ne pas copier l'exemple
d'inventaire tel quel : il ouvre SSH à `0.0.0.0/0`.

## 5. Dimensionnement estimé

Audit §10.6, grilles non revérifiées, ± 25 % : 25 à 45 €/mois pour le 35 avec une pile
dégraissée sur 4 vCPU / 8 Go ; 49 à 113 € avec la pile actuelle sur 8 vCPU / 16 Go ; 300 à
400 Go de disque à quatre départements. PostgreSQL 15 atteint sa fin de support en novembre 2027.
