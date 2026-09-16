# Immo Opportunities

Intelligence de marché immobilier sur l'Ille-et-Vilaine, à partir de données publiques : un
baromètre du marché par EPCI, puis un radar hebdomadaire de mise en vente
([ADR-016](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md)). La plateforme
cartographique antérieure est gelée. **Répondre et documenter en français.**

## Où trouver l'information

Ne charger que ce que la tâche demande. `SPEC.md` et `ARCHITECTURE.md` font ~600 lignes : une
section à la fois, jamais en entier. L'audit `docs/audit-critique-2026-09-15.md` est de
l'historique : on y va pour une preuve. Sources de vérité, dans l'ordre : `SPEC.md` →
`ARCHITECTURE.md` → `docs/decisions/` → `contracts/` → `docs/data/`.

| Besoin | Charger |
|---|---|
| Implémenter un ticket | `docs/backlog/<ID>-*.md`, son bloc « Contexte à charger ». Rien d'autre. |
| Savoir quoi faire ensuite, état du projet, chemin critique | `docs/backlog/README.md` |
| Pourquoi le produit a changé, ce qui est gelé et à quelles conditions | ADR-016 ; `SPEC.md` §6.2, §11 |
| Périmètre et hors périmètre | `SPEC.md` §6, en particulier §6.4 |
| Ce que les données ont déjà établi sur le 35, à ne pas redécouvrir | `SPEC.md` §10, puis le rapport `docs/data/` cité |
| Mesures du baromètre `BAR-*`, radar | `SPEC.md` §7, §8 |
| Règles de données, valeurs manquantes, imports, interdits de données | `SPEC.md` §13 |
| Ce qui existe, ce qui est défectueux | `ARCHITECTURE.md`, la section concernée |
| Un chiffre et son filtre | le rapport `docs/data/` qui le porte, jamais un résumé |
| Outillage du dépôt (CI, `make`, scripts de contrôle) | `Makefile`, `make help`, `scripts/`, `.github/workflows/` |
| Reconstituer la base | `docs/operations/referentiel-local-35.md` |
| Boucle de développement et verrous | [ADR-015](docs/decisions/ADR-015-boucle-autonome.md) |

## Garde-fous, quel que soit le ticket

- **Plateforme gelée** : aucune ligne dans `apps/web/`, `backend/src/immo/api/`, le moteur de
  score, `infra/`, `config/`, les fichiers Compose, sans ADR de dégel (SPEC §11). L'API locale
  reste locale.
- **Données** : valeur manquante reste manquante avec un motif, jamais zéro ; jamais un taux sans
  son effectif ni un effectif sans son filtre ; aucun seuil territorial inventé, un seuil de
  support est un paramètre déclaré ; aucune combinaison de signaux en score sans profiling écrit ;
  aucune donnée nominative dans le baromètre, aucune liste par adresse avant l'avis juridique H4 ;
  réforme DPE du 1er janvier 2026 à distinguer ou déclarer ; jamais de données simulées présentées
  comme réelles ; import reproductible (SHA-256, pas d'alias `latest`, version de transformation
  dans la clé d'idempotence). Détail : SPEC §13.
- **Technique** : pas de ML en production, de Kubernetes, de Celery, de scoring à la requête, de
  secrets en clair, de nouvelle table pour le baromètre. Aucune bibliothèque sans ADR.
- **Chiffres** : tout chiffre publié dans `docs/data/` passe par la compétence `recompte-preuve`
  avant clôture du ticket.

## Toute modification passe par un ticket

Toute demande touchant le code, un schéma, l'infrastructure, l'outillage ou le comportement de
l'application s'ouvre en ticket **avant la première ligne modifiée**, même en cours de
conversation, en `En cours`, avec la demande et **les choix retenus**. Seul `docs/` en est
dispensé ; `SPEC.md`, `ARCHITECTURE.md` et `CLAUDE.md` demandent un ticket. Le critère porte
sur les **chemins touchés**, jamais sur l'importance du changement. Combler un écart déjà tranché
n'ouvre pas de ticket : le commit porte l'identifiant du ticket honoré ; sinon c'est une décision,
et elle s'écrit. `make ticket-check` : sujet du commit avec identifiant (`H1 — …`, `A7, H6 — …`)
ou `ticket-ok: <raison>` dans le corps.

## Definition of Done

Terminé **seulement si** : 1) test automatisé ajouté ou étendu ; 2) preuve dans `docs/data/` ou
`contracts/`, recomptée si elle porte un chiffre ; 3) `make openapi` régénéré si l'API change ;
4) `make check` vert ; 5) aucune donnée simulée présentée comme réelle ; 6) état du ticket mis à
jour **dans son propre fichier**, puis `make backlog` ; 7) dépendances des tickets débloqués
**relues**. `make dod ID=<ticket>` vérifie le mécanisable. Sans test ou preuve légitime, l'en-tête
le déclare : `**DoD :** test sans objet — <raison>` ou `preuve sans objet — <raison>`.

## Boucle et arrêt

Trois contrôles, non interchangeables : déterministe (`make check`, `make backlog-check`,
`make dod`, à chaque étape), adversarial (`recompte-preuve`, dès qu'un chiffre entre dans
`docs/data/`, sans lire le code), humain (tickets de `**Nature :**` humaine). `make invariants`
contrôle les interdits sur les lignes ajoutées ; ligne légitime signalée : `invariant-ok:
<raison>` sur place.

**La boucle s'arrête**, explicitement, sur : un ticket de nature humaine (annoncé **verrou
humain**, jamais « prêt ») ; deux échecs consécutifs du même gate sur le même ticket ; une
décision que `SPEC.md` ne tranche pas ; une source externe indisponible ou un quota atteint
(temporiser, jamais une fixture) ; une contradiction entre deux sources de vérité.

## Backlog et sous-agents

L'état d'un ticket vit à **un seul endroit**, la ligne `**État :**` de son fichier : `À faire`,
`En cours`, `Terminé`, `Abandonné`. `**Nature :**` vaut `implémentation` (défaut), `revue humaine`
ou `décision humaine` ; ces deux dernières sont des **verrous** déclarés, avec `**Preuve :**` le
fichier attendu. « Disponibilité » est dérivée du graphe par `make backlog` ; une nouvelle série
demande un ticket (modèle : A7). **Passer un ticket à `En cours` en le commençant** ; à la
clôture, réexaminer ce qu'il débloque.

Sous-agents : oui pour la recherche en fan-out (garder la conclusion) et pour les tickets d'un
même lot menable de front (champ `**Touche :**` ; sans `Touche`, ticket isolé) ; non sur le
chemin critique. Un sous-agent reçoit l'ID du ticket et son bloc « Contexte à charger ».

## Commandes de la boucle

```bash
make check                # lint, typecheck, tests sans base, OpenAPI, Compose, invariants, budget doc
make backlog              # régénère le tableau ; make backlog-check le vérifie (hors make check)
make dod ID=<ticket>      # ce qui est mécanisable de la DoD
make ticket-check         # tout commit hors docs/ porte un identifiant de ticket
make help                 # tout le reste : dev, rebuild, imports, features, baromètre
```

`make rebuild` recrée PostgreSQL et coupe tout lot en cours ; les conteneurs embarquent le code
figé au build, un changement de pipeline ou de contrat demande `make rebuild`.
