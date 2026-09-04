# Infrastructure VPS exécutable

L'application se déploie sur un VPS Ubuntu générique. Aucun fournisseur cloud, provider OpenTofu ou service Scaleway n'est requis par ce dépôt.

Le VPS est créé chez le fournisseur de votre choix. À partir d'un Ubuntu 24.04 vierge, Ansible automatise le reste : durcissement SSH/UFW, mises à jour de sécurité, fail2ban, Docker Engine, Compose v2, répertoires persistants, secrets SOPS, stack Compose et unité systemd.

## Exécution locale avec OrbStack

```text
cp .env.example .env
make dev-secrets
make dev
make smoke
```

L'image PostGIS est `amd64`. Sur Apple Silicon, OrbStack l'exécute via l'émulation définie par `POSTGRES_PLATFORM=linux/amd64`.

## Préparer le VPS

Le serveur initial doit fournir :

- Ubuntu 24.04 LTS sur architecture x86_64/amd64 ;
- un utilisateur SSH possédant une clé et `sudo` sans mot de passe ;
- au moins les ports TCP 80/443, UDP 443 et le port SSH autorisés par le pare-feu du fournisseur ;
- un enregistrement DNS A/AAAA pointant le domaine vers le VPS ;
- suffisamment de disque pour PostgreSQL et MinIO.

Le bootstrap utilise `/srv/immo/postgres` et `/srv/immo/objects` sur le disque système. Des volumes bloc supplémentaires restent possibles via `immo_data_volumes`, mais ne sont ni requis ni formatés implicitement.

## Configurer GitHub

Créer un environnement GitHub nommé `production`, idéalement protégé par une approbation manuelle.

Variables de l'environnement :

| Variable | Exemple |
|---|---|
| `VPS_HOST` | `203.0.113.20` ou `vps.example.com` |
| `VPS_USER` | `deploy` |
| `VPS_SSH_PORT` | `22` |
| `APP_DOMAIN` | `immo.example.com` |
| `ACME_EMAIL` | `ops@example.com` |
| `ADMIN_CIDRS_JSON` | `["0.0.0.0/0","::/0"]` |

Secrets de l'environnement :

| Secret | Contenu |
|---|---|
| `VPS_SSH_PRIVATE_KEY` | clé SSH privée dédiée au déploiement |
| `VPS_SSH_HOST_KEY` | ligne `known_hosts` du VPS, vérifiée hors bande |
| `SOPS_AGE_KEY` | identité privée `AGE-SECRET-KEY-...` |

Les runners GitHub hébergés n'ont pas une adresse source fixe dédiée au projet. Pour qu'ils puissent joindre directement le VPS, le port SSH doit être accessible depuis leurs adresses ; avec `ADMIN_CIDRS_JSON=["0.0.0.0/0","::/0"]`, l'accès reste protégé par clé uniquement, root et mots de passe désactivés, plus fail2ban. Pour restreindre SSH à un CIDR fixe, utiliser un runner auto-hébergé ou un réseau privé/VPN.

Ne jamais générer silencieusement la clé d'hôte dans le workflow. Récupérer la clé publique, vérifier son empreinte via la console du fournisseur, puis enregistrer la ligne complète dans `VPS_SSH_HOST_KEY`. Pour un port non standard, son format commence par `[hôte]:port`.

## Secrets applicatifs

```text
cp .sops.yaml.example .sops.yaml
cp secrets/production.sops.yaml.example secrets/production.sops.yaml
sops --encrypt --in-place secrets/production.sops.yaml
```

Le fichier chiffré `secrets/production.sops.yaml` est versionné. La clé privée `age` ne l'est jamais et reste dans le secret GitHub `SOPS_AGE_KEY`.

## Premier déploiement

Dans **Actions → Deploy VPS → Run workflow**, sélectionner `bootstrap=true`.

Le workflow :

1. valide les variables et secrets requis ;
2. construit l'image opérateur Ansible/SOPS ;
3. vérifie la clé d'hôte SSH ;
4. prépare le VPS ;
5. installe et démarre chaque service dans son propre conteneur ;
6. attend les healthchecks.

Les pushes suivants sur `main` exécutent uniquement le playbook idempotent de déploiement. La concurrence est sérialisée pour empêcher deux déploiements simultanés.

## Exécution manuelle équivalente

```text
export VPS_HOST=203.0.113.20
export VPS_USER=deploy
export VPS_SSH_PORT=22
export APP_DOMAIN=immo.example.com
export ACME_EMAIL=ops@example.com
export ADMIN_CIDRS_JSON='["0.0.0.0/0","::/0"]'

make inventory ENV=production
make bootstrap ENV=production
make deploy ENV=production
```

Les chemins `AGE_KEY_FILE`, `SSH_PRIVATE_KEY_FILE` et `SSH_KNOWN_HOSTS_FILE` sont surchargeables dans la commande `make`.

## Limites restantes

- la création et la facturation du VPS restent hors de ce dépôt ;
- WAL-G, les sauvegardes MinIO hors site et un test de restauration restent à câbler avant la production ;
- les images API, frontend, Martin, Dagster et Celery seront ajoutées avec la première tranche applicative ;
- la stratégie de support/licence MinIO Community doit être validée avant la production.
