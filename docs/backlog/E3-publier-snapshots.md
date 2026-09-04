# E3 — Publier des `OpportunitySnapshot` immuables

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Dépend de :** E2 · **Bloque :** E4, F1, et toute la section NICE

> **Jalon central du projet.** C'est le premier moment où le produit existe pour un utilisateur :
> un classement réel d'actifs à approfondir sur le 35. Tout ce qui précède y mène, tout ce qui
> suit en dépend.

## Contexte à charger

- `pipelines/src/immo_pipelines/scoring/persistence.py`
- `backend/src/immo/scoring.py`
- `backend/src/immo/api/routes/scoring.py`
- migration `20260807_0012`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le mécanisme est livré et testé : snapshots immuables, composantes, preuves, digest des entrées,
publication atomique par déplacement de pointeur, rollback. Migration `20260807_0012`.

**Règles non négociables :**
- les snapshots sont **immuables** ;
- la publication **déplace un pointeur**, elle ne réécrit jamais l'historique ;
- un scénario financier privé ne modifie **jamais** un snapshot.

## Contenu de chaque snapshot

| Élément | Exigence |
|---|---|
| Éligibilité | avec sa raison si l'unité est inéligible |
| Score | rang synthétique, jamais présenté comme une probabilité |
| Confiance | calculée séparément du score |
| Composantes | contribution de chaque feature, positive ou négative |
| Preuves | source et date de chaque valeur ayant contribué (FR-006, FR-011) |
| Manquants | chaque valeur absente avec son motif (FR-007) |
| Scénario de référence | prudent / central / optimiste, distinct des scénarios privés (FR-008) |

## Travail à réaliser

1. Exécuter le calcul sur l'ensemble des unités du périmètre éligible défini en E2.
2. Publier le bundle et déplacer le pointeur de façon atomique.
3. Vérifier que le nombre d'unités éligibles est **suffisant pour être utile** : un top-N sur une
   poignée de candidats ne permet pas de conduire le pilote G8. Publier le volume obtenu, par
   commune et par segment.
4. Vérifier la performance : le scoring est calculé en amont, jamais à la requête.
5. Exercer un rollback réel et vérifier que l'historique est intact.

## Points de vigilance

- **Le volume est un résultat, pas un objectif.** S'il est faible, la cause est en amont
  (couverture des sources) et se corrige en amont — pas en assouplissant l'éligibilité.
- Une unité inéligible doit être visible avec sa raison, pas absente sans explication : c'est ce
  qui distingue « aucun candidat ici » de « données insuffisantes ici » (voir [C2](./C2-zone-non-couverte.md)).
- Les preuves doivent permettre à un professionnel de refaire le raisonnement à la main. C'est le
  critère de FR-006, et ce sera mesuré en G8 (hypothèse H3, compréhension).

## Tests obligatoires

- propriété d'immutabilité : un snapshot publié ne peut être modifié par aucun chemin ;
- un scénario privé ne modifie aucun snapshot ;
- publication et rollback atomiques, historique intact ;
- score identique à données et définition identiques ;
- feature `required` absente : unité inéligible avec raison, jamais score partiel ;
- feature `optional` absente : contribution neutre, confiance réduite ;
- bornes du score et de la confiance respectées ;
- aucun calcul de score à la requête.

## Critères d'acceptation

- au moins une définition publiée avec des snapshots réels sur le 35 ;
- volume publié par commune et par segment ;
- preuves et manquants présents sur chaque snapshot ;
- rollback exercé et documenté ;
- **le produit peut afficher un top-N réel** — v0.7 devient activable.

## Preuves à produire

- rapport `docs/data/first-published-scoring-35.md` : périmètre, volumes, distribution des scores
  et des confiances, exemples de snapshots complets ;
- mise à jour de [`scoring-v0.6-report.md`](../data/scoring-v0.6-report.md) et de
  [`mvp-dod-traceability.md`](../data/mvp-dod-traceability.md).
