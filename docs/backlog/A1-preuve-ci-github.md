# A1 — Exécuter le workflow CI sur GitHub et attacher la preuve

**Version :** v0.1 · **Taille :** S · **État :** À faire
**Dépend de :** — · **Bloque :** clôture de v0.1 uniquement (hors chemin critique données)

## Contexte à charger

- `.github/workflows/ci.yml`
- `Makefile` (cible `check`)
- `docs/versions/v0.1-foundation.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.1 est la seule version dont tous les critères sont satisfaits sauf un :

```text
- [ ] Workflow CI exécuté sur GitHub.
```

Le workflow existe ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) et les contrôles
passent localement, mais aucune exécution GitHub n'est attachée. La traçabilité l'indique
explicitement : « nouveaux tests locaux ; exécution GitHub absente ».

C'est une preuve manquante, pas un développement. Le dépôt n'a qu'un seul commit (`ac0a57a`), ce
qui suggère que le remote n'a jamais reçu de push déclenchant le workflow.

## Travail à réaliser

1. Vérifier que le dépôt distant existe et que GitHub Actions y est activé.
2. Déclencher le workflow sur `main` ou sur une pull request.
3. Vérifier que les jobs couvrent bien : lint, typecheck, tests backend, tests pipelines, build
   frontend, et validation du contrat OpenAPI.
4. Si un job échoue pour une raison d'environnement CI et non de code, corriger le workflow — sans
   désactiver de contrôle pour faire passer la CI.
5. Attacher l'URL du run et son résultat dans les preuves de v0.1.

## Points de vigilance

- Un job vert obtenu en réduisant le périmètre des tests n'est pas une preuve. Comparer la liste
  des contrôles exécutés en CI à celle de `make check`.
- Les secrets nécessaires ne doivent pas apparaître en clair ; si la CI a besoin d'un service
  PostgreSQL/PostGIS, il doit être fourni par un service container, pas par un secret externe.
- Le workflow [`deploy-vps.yml`](../../.github/workflows/deploy-vps.yml) n'est pas concerné par ce
  ticket : son exécution réelle relève de [G6](./G6-exploitation-restauration.md).

## Critères d'acceptation

- au moins un run GitHub complet et vert sur `main` ou sur une PR mergée ;
- les contrôles exécutés en CI sont au moins ceux de `make check` ;
- l'URL du run figure dans les preuves de livraison de v0.1 ;
- la ligne « Parcours critiques en CI » de la traçabilité passe de partiel à validé.

## Preuves à produire

- lien du run dans [`docs/versions/v0.1-foundation.md`](../versions/v0.1-foundation.md) ;
- mise à jour de la ligne correspondante dans
  [`docs/data/mvp-dod-traceability.md`](../data/mvp-dod-traceability.md) ;
- passage de v0.1 à `Terminée` dans [`docs/versions/README.md`](../versions/README.md).
