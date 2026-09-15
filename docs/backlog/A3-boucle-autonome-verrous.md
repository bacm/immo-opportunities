# A3 — Verrous humains et invariants de la boucle de développement

**Version :** transverse · **Taille :** M · **État :** Terminé
**Touche :** .github/workflows/ci.yml, scripts/backlog-status, scripts/check-diff-invariants, scripts/check-ticket-dod, scripts/tests/, Makefile, CLAUDE.md, .claude/skills/, docs/backlog/B4-revue-manuelle-appariements.md, docs/backlog/D6-revue-manuelle-metier.md, docs/backlog/E7-decision-valorisation.md, docs/backlog/G8-pilote-trois-professionnels.md, docs/backlog/G9-decision-finale.md
**Dépend de :** — · **Bloque :** —
**DoD :** preuve sans objet — outillage : la preuve est la suite `scripts/tests/`
**Demandé par :** conversation du 15 septembre 2026

## Contexte à charger

- `scripts/backlog-status`
- `docs/backlog/B4-revue-manuelle-appariements.md` (verrou de référence)
- `CLAUDE.md` §Definition of Done d'une tâche

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Les tickets sont de plus en plus souvent menés par un agent, en boucle. La question posée est
celle de la fiabilité de cette boucle : jusqu'où peut-elle avancer seule, et à quoi s'arrête-t-elle.

La réponse retenue n'est **pas** un agent validateur après chaque étape. Un relecteur qui dispose
du même contexte que le producteur valide surtout la cohérence interne — ce que `make check` fait
déjà, en reproductible et pour rien. Les trois défauts structurels de v0.3 (BUG-09, BUG-10,
BUG-12) n'ont été trouvés ni par les tests ni par une relecture de code, mais par **B4**, une revue
menée contre les sources.

D'où trois natures de contrôle, distinctes et non interchangeables :

| Nature | Qui | Quand |
|---|---|---|
| Déterministe | `make check`, `make backlog-check`, invariants de diff | à chaque étape |
| Adversarial | un agent qui **recalcule** depuis les sources, sans voir le code | quand l'étape écrit un chiffre dans `docs/data/` ou `contracts/` |
| Humain | B4, D6, E7, G8, G9 | quand le verdict porte sur l'exactitude dans le monde réel, ou sur un arbitrage produit |

## Le point dur : le verrou ne peut pas être un jugement du modèle

Demander à un agent « as-tu besoin d'un humain ici ? » revient à lui demander de s'interrompre
alors qu'il est sous pression d'achèvement. Il répondra non.

Le verrou doit donc être **topologique**, comme l'est déjà la disponibilité : dérivé de la donnée
du backlog, pas décidé en cours de route. B4 et D6 sont déjà dans le graphe de dépendances — B5
dépend de B4, E1 dépend de D6. Il manquait seulement de quoi les distinguer d'un ticket
implémentable.

## Périmètre

1. Champ d'en-tête `**Nature :**` — `implémentation` (défaut), `revue humaine`, `décision
   humaine`. Un ticket de nature humaine prêt n'est jamais annoncé « prêt » : il est annoncé
   **verrou humain**, et sort de fait des lots menables de front.
2. Champ d'en-tête `**Preuve :**` — obligatoire pour un ticket de nature humaine, et le fichier
   doit exister pour que l'état `Terminé` soit accepté. Les tickets concernés déclarent déjà ce
   chemin dans leur section « Preuve à produire » ; le champ le remonte là où l'outillage le lit.
3. `scripts/check-diff-invariants` — les interdits de `CLAUDE.md` vérifiés sur les lignes ajoutées
   du diff. Le mode d'échec d'une boucle autonome n'est pas l'erreur, c'est l'arrangement :
   assouplir un test au lieu de corriger, convertir une valeur manquante en zéro, figer un alias
   `latest`. Échappatoire explicite `invariant-ok: <raison>` — un contrôle sans échappatoire finit
   désactivé.
4. `scripts/check-ticket-dod` — les sept points de la DoD vérifiés mécaniquement sur le diff du
   ticket, celui-ci étant reconstitué depuis les commits dont le sujet porte son identifiant.
5. Compétence `recompte-preuve` — le contrôle adversarial, décrit comme un recalcul depuis les
   sources et non comme une relecture de diff.

## Critères d'acceptation

- un ticket de nature humaine n'apparaît jamais comme « prêt » ni dans un lot menable de front ;
- un ticket de nature humaine passé à `Terminé` sans sa preuve sur disque fait échouer
  `make backlog-check` ;
- les invariants de diff attrapent les cinq familles d'arrangement et sont calibrés : zéro
  signalement sur les dix derniers commits du dépôt ;
- `make dod ID=<ticket>` rend un verdict point par point, et dit lesquels il ne peut pas vérifier
  plutôt que de les déclarer verts ;
- les scripts sont couverts par des tests exécutés par `make check`.

## Ce qui n'est pas dans le périmètre

- **A1 reste ouvert.** Sans exécution CI sur GitHub, la boucle n'a que son propre témoignage. Ce
  ticket n'y change rien : il ajoute des contrôles, il ne les fait pas observer par un tiers.
- Le point 7 de la DoD — relire les dépendances des tickets débloqués — n'est pas mécanisable. Le
  script les affiche, il ne peut pas les juger.
