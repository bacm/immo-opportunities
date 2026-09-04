# F1 — Parcours complet sans fixture sur candidats publiés

**Version :** v0.7 · **Taille :** M · **État :** À faire
**Dépend de :** E3 · **Bloque :** F2, F3

## Contexte à charger

- `backend/src/immo/connected_mvp.py`
- `backend/src/immo/api/routes/connected_mvp.py`
- `apps/web/src/App.tsx`
- `apps/web/tests/e2e/real-map.spec.ts`
- `docs/data/connected-mvp-v0.7-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.7 est entièrement codée. Le rapport existe, les tests Playwright passent, la DoD technique est
cochée. Une seule chose manque : des candidats réels à afficher.

> « validé sur parcours technique », « technique validée, cas réel absent »

Ce ticket ne développe rien. Il **exécute** le parcours de bout en bout sur les snapshots publiés
en E3, dans un environnement sans aucune fixture, et en consigne la preuve.

## Parcours à exécuter

```text
login OIDC
  → recherche (adresse, commune ou parcelle réelle)
  → filtres et tri, état restitué par l'URL
  → fiche : score, composantes, preuves, sources, dates, comparables DVF
  → scénario financier prudent / central / optimiste
  → changement de statut, note, motif de rejet
  → vérification de l'historique
```

## Vérifications spécifiques

| Point | Attendu |
|---|---|
| Origine des données | aucune fixture dans aucun écran ; chaque valeur remonte à une release |
| Synchronisation carte ↔ liste | identique après filtre, tri et navigation (FR-003) |
| Preuves de score | source et date pour chaque valeur contributive (FR-006, FR-011) |
| Inconnus | visibles, distincts de zéro et de « non applicable » (FR-007) |
| Scénario privé | ne modifie **jamais** le snapshot publié (FR-008) |
| Historique | append-only, un statut passé n'est pas réécrit (FR-009) |
| Comparables | inclus et exclus, avec motif (FR-010) |

## Points de vigilance

- Le point le plus facile à rater : un scénario financier privé qui, par un effet de bord, altère
  une valeur affichée du snapshot. À vérifier explicitement, snapshot rechargé après scénario.
- Un environnement « presque sans fixture » ne compte pas. Vérifier qu'aucun jeu de démonstration
  n'est chargé, y compris pour les organisations et les utilisateurs.
- Si le volume de candidats publiés est faible, le parcours reste valable mais la limite doit être
  notée : elle conditionne la faisabilité de [G8](./G8-pilote-trois-professionnels.md).

## Tests obligatoires

- parcours Playwright complet sur données réelles, sans fixture ;
- rechargement du snapshot après création d'un scénario : identique au bit près ;
- historique de statut append-only vérifié par test ;
- aucune requête ne déclenche un calcul de score.

## Critères d'acceptation

- parcours exécuté de bout en bout sur candidats réels ;
- aucune fixture présente dans l'environnement ;
- immutabilité du snapshot vérifiée après action utilisateur ;
- captures et journal d'exécution archivés.

## Preuve à produire

Mise à jour de [`connected-mvp-v0.7-report.md`](../data/connected-mvp-v0.7-report.md) avec la
section « parcours sur données réelles », captures datées et releases citées.
