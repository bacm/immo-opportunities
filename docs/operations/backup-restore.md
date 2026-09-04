# Sauvegarde et restauration du pilote

## Contrat

Le timer `immo-backup.timer` exécute chaque nuit `scripts/backup-platform`. Une sauvegarde n'est
complète que si son répertoire contient `postgres.dump`, l'arborescence `minio/` et
`manifest.json`. Le répertoire partiel est renommé atomiquement après calcul du SHA-256. Aucun
nettoyage automatique n'est réalisé : la rétention doit être définie avec l'hébergeur avant
production.

Objectifs à valider sur l'infrastructure cible : RPO 26 h maximum, RTO 4 h maximum. Ce sont des
objectifs, pas des mesures acquises. La métrique `immo_backup_last_success_timestamp_seconds`
déclenche une alerte après 26 h.

## Réplication MinIO hors site

Le site secondaire doit être indépendant du VPS principal, utiliser TLS et conserver le
versionnement. Après création des identifiants dédiés :

```bash
BACKUP_MINIO_ENDPOINT=https://minio-backup.example.net \
BACKUP_MINIO_USER_FILE=/etc/immo/secrets/backup_minio_user \
BACKUP_MINIO_PASSWORD_FILE=/etc/immo/secrets/backup_minio_password \
/opt/immo/scripts/configure-minio-replication
```

Le statut retourné par `mc admin replicate status primary` est archivé dans le ticket
d'exploitation. La copie locale produite avec le dump PostgreSQL reste utile pour un exercice
cohérent, mais ne remplace pas la réplication hors site.

## Exercice de restauration

Sur un hôte de test disposant de Docker :

```bash
/opt/immo/scripts/restore-drill /srv/immo/backups/<backup-id> \
  | tee restore-<backup-id>.json
```

Le script utilise uniquement des conteneurs, volumes et réseau temporaires nommés avec le préfixe
`immo-restore-*`. Il restaure PostgreSQL, vérifie les six schémas applicatifs, restaure tous les
buckets MinIO et compare le nombre d'objets. Les ressources temporaires sont supprimées à la fin.
Le JSON final fournit le RTO observé. L'exercice n'est réussi qu'après archivage de ce JSON, du
SHA-256 du manifeste et d'un smoke test applicatif sur un VPS vierge.

## État au 10 août 2026

Le mécanisme, les timers, la réplication configurable, les alertes et le drill sont livrés. Aucun
backup de production ni cible hors site n'est disponible dans le workspace : RPO et RTO restent
donc **non mesurés**, et la restauration ne peut pas être déclarée éprouvée.
