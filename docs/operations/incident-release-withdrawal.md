# Runbook — source défectueuse et publication Bretagne

## Détection et confinement

1. Geler les nouveaux imports de la source et relever le `request_id`, la release, le territoire
   et le contrôle en échec.
2. Ne jamais corriger une release ou un snapshot en place. Enregistrer un contrôle bloquant dans
   `meta.data_quality_check` et un verdict `rejected` si le défaut est confirmé.
3. Retirer immédiatement le bundle régional depuis l'administration ou avec
   `POST /api/v1/admin/brittany/withdraw`, avec un motif factuel. L'action nécessite
   `platform_admin` et produit un événement immuable.
4. Vérifier que la liste et les tuiles n'exposent plus le bundle retiré, puis informer les
   organisations concernées sans divulguer leurs données privées.

## Correction et rollback

- Une nouvelle release suit tout le cycle archive → import → contrôles → acceptation.
- Un rollback régional ne vise qu'un bundle historique dont les 36 membres sont encore acceptés,
  sans contrôle bloquant, avec scores et segmentation actifs. Les snapshots publiés doivent
  d'abord être replacés sur leurs versions compatibles avec ce bundle, puis appeler :
  `POST /api/v1/admin/brittany/rollback`.
- Si l'ancien bundle contient lui-même la source défectueuse, il reste interdit ; la plateforme
  demeure retirée jusqu'à une release corrigée.

## Clôture

Archiver chronologie, cause racine, périmètre, événements de retrait/rollback, tests d'isolation,
smoke tests, pertes de données éventuelles et actions préventives. Un incident n'est pas clos sur
la seule disparition de l'alerte.
