# G5 — Administration : import-runs, qualité, publication et rollback régional

**Version :** v0.8 · **Taille :** M · **État :** À faire
**Dépend de :** G2 · **Bloque :** clôture de v0.8

## Contexte à charger

- `backend/src/immo/api/routes/meta.py`
- `pipelines/src/immo_pipelines/scoring/persistence.py`
- `pipelines/src/immo_pipelines/pilot/brittany.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Les fonctions existent — « release importée / validée / publiée / annulée : technique validée,
région réelle absente ». Ce ticket les exerce à l'échelle régionale et satisfait FR-012 sur des
données réelles.

## Travail à réaliser

1. **Import-runs** : vue administrateur listant les exécutions réelles par dataset, release et
   département, avec état, durée, volumes, quarantaines et motifs.
2. **Qualité des données** : contrôles exécutés, résultats, sévérité, caractère bloquant, avec
   accès au détail des quarantaines.
3. **Publication régionale** : publier un bundle couvrant plusieurs départements de façon atomique.
4. **Retrait et rollback** : retirer une publication et revenir à la précédente, sans réécrire
   l'historique — le pointeur se déplace, les snapshots restent.
5. Exercer réellement le cycle complet publication → retrait → rollback sur données régionales et
   en consigner le chronométrage.

## Points de vigilance

- **L'atomicité régionale est le point délicat** : une publication partielle laisserait certains
  départements sur une version et d'autres sur une autre, rendant tout classement incohérent. Le
  test doit inclure un échec en cours de publication.
- Le rollback doit être exercé pour de vrai, pas seulement testé unitairement : c'est le filet de
  sécurité du pilote, il sera utilisé si un problème apparaît devant un professionnel.
- Les quarantaines doivent rester consultables après coup : c'est ce qui permet d'expliquer une
  absence à un utilisateur.

## Tests obligatoires

- publication régionale atomique ; un échec partiel ne laisse aucun état intermédiaire ;
- rollback restaure l'état précédent sans modifier aucun snapshot ;
- l'historique des publications est append-only ;
- les import-runs et les contrôles qualité réels sont visibles par un administrateur ;
- aucune donnée d'une organisation n'est visible depuis l'administration d'une autre.

## Critères d'acceptation

- FR-012 démontré sur des import-runs réels ;
- cycle publication / retrait / rollback exercé et chronométré sur données régionales ;
- atomicité vérifiée y compris en cas d'échec ;
- quarantaines consultables et motivées.

## Preuve à produire

Rapport `docs/data/regional-publication-drill.md` : déroulé, chronométrage, captures.
