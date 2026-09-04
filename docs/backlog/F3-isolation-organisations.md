# F3 — Isolation des organisations en conditions proches production

**Version :** v0.7 · **Taille :** M · **État :** À faire
**Dépend de :** F1 · **Bloque :** G8, clôture de v0.7

## Contexte à charger

- `backend/src/immo/auth.py`
- `backend/src/immo/database.py` (RLS)
- `scripts/check-database-permissions`
- `map/` (configuration Martin, rôle `tiles_ro`)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

La traçabilité indique : « Rôles et isolation organisations — RLS forcé, tests v0.7 — **local
validé, production absent** ».

L'enjeu est direct : le pilote [G8](./G8-pilote-trois-professionnels.md) met trois professionnels
concurrents sur la même instance. Une fuite de notes, de statuts ou de motifs de rejet entre
organisations serait une faute grave, pas un défaut mineur.

## Travail à réaliser

1. Rejouer les tests d'isolation dans un environnement de configuration production : RLS forcé,
   rôles PostgreSQL réels, pas de superutilisateur applicatif.
2. Vérifier l'isolation sur **tous** les chemins de lecture, pas seulement l'API principale :
   - API privée `/api/v1/*` ;
   - tuiles Martin — vérifier que le rôle `tiles_ro` ne peut atteindre aucune donnée privée ;
   - exports et endpoints d'administration ;
   - messages d'erreur, qui ne doivent pas révéler l'existence d'une ressource d'une autre organisation.
3. Vérifier qu'un identifiant d'entité connu d'une organisation A ne permet à B ni de lire, ni de
   modifier, ni de déduire l'existence de la ressource.
4. Tester le cas d'un utilisateur appartenant à plusieurs organisations, si le modèle l'autorise.
5. Vérifier que la publication d'un bundle de scores est visible par toutes les organisations,
   alors que notes, statuts et scénarios restent strictement privés.

## Points de vigilance

- **Martin est le chemin le plus exposé** : la règle est que les tuiles ne portent que des attributs
  de rendu. Notes, statuts et scénarios passent exclusivement par l'API privée sous RLS. Vérifier
  qu'aucune vue exposée à `tiles_ro` ne contient d'attribut privé, même indirectement.
- Une réponse 404 et une réponse 403 ne disent pas la même chose : renvoyer 403 sur une ressource
  d'une autre organisation révèle son existence.
- Le test doit être conduit avec des jetons OIDC réels, pas avec un contournement d'authentification.

## Tests obligatoires

- lecture croisée A → B refusée sur chaque chemin, y compris tuiles ;
- écriture croisée refusée ;
- aucune fuite par message d'erreur ou par différence de code de statut ;
- le rôle `tiles_ro` ne peut lire aucune table privée, vérifié au niveau PostgreSQL ;
- bundle de scores partagé, données privées cloisonnées.

## Critères d'acceptation

- isolation vérifiée en configuration proche production, pas seulement en local ;
- tous les chemins de lecture couverts ;
- la ligne « Rôles et isolation organisations » de la traçabilité passe à validé ;
- v0.7 peut être passée à `Terminée`.

## Preuve à produire

Rapport `docs/data/multi-tenant-isolation-35.md` : environnement, chemins testés, résultats, et
vérification PostgreSQL des droits effectifs du rôle `tiles_ro`.
