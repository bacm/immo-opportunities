# F2 — Vérifier FR-001 à FR-012 sur candidats réels

**Version :** v0.7 · **Taille :** M · **État :** À faire
**Dépend de :** F1 · **Bloque :** G1, clôture de v0.7

## Contexte à charger

- `docs/data/connected-mvp-v0.7-report.md`
- `SPEC.md` (§FR-001 à FR-012 uniquement)
- `apps/web/src/App.tsx`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Les douze exigences `Must` sont codées et tracées dans le rapport v0.7, mais sur un parcours
technique. Ce ticket les re-vérifie une par une sur des candidats publiés, et remplace « technique
validée » par une preuve réelle dans la traçabilité.

## Grille de vérification

| FR | Exigence | Preuve attendue sur données réelles |
|---|---|---|
| FR-001 | Recherche adresse / commune / parcelle | trois recherches réelles réussies, URL partageable |
| FR-002 | Carte des candidats | candidats publiés affichés, tuiles Martin, aucun GeoJSON régional |
| FR-003 | Synchronisation carte ↔ liste | état identique après filtre, tri, navigation |
| FR-004 | Filtres, tri et URL | état complet restitué au rechargement |
| FR-005 | Fiche complète | toutes les sections renseignées ou explicitement absentes |
| FR-006 | Preuves de score sourcées | chaque contribution remonte à une release et une date |
| FR-007 | Inconnu ≠ zéro ≠ N/A | les trois états distincts visibles sur un cas réel |
| FR-008 | Scénarios sans mutation des sources | snapshot inchangé après scénario |
| FR-009 | Statut, note, motif de rejet, historique | historique append-only sur un cas réel |
| FR-010 | Comparables DVF explicables | inclus et exclus avec motifs, sur un cas réel |
| FR-011 | Fraîcheur et provenance | date et source visibles au niveau de la valeur |
| FR-012 | Admin imports et qualité | import-runs et métriques réels visibles |

## Points de vigilance

- FR-007 est le plus révélateur et le plus souvent mal servi : il faut trouver un cas réel
  présentant simultanément une valeur inconnue, une valeur non applicable et une valeur nulle
  légitime, et vérifier qu'un utilisateur les distingue sans explication.
- FR-006 sera mesuré au pilote (hypothèse H3). Une preuve techniquement présente mais
  incompréhensible pour un professionnel ne satisfait pas l'exigence.
- FR-012 doit montrer de vrais import-runs, pas une interface vide.

## Critères d'acceptation

- les douze exigences vérifiées sur des candidats publiés, avec preuve individuelle ;
- les cas défaillants sont listés et corrigés ou documentés comme limites ;
- la traçabilité passe de « technique validée » à validé pour les lignes concernées ;
- v0.7 peut être passée à `Terminée` une fois F3 également livré.

## Preuve à produire

Grille complétée dans [`connected-mvp-v0.7-report.md`](../data/connected-mvp-v0.7-report.md) et
mise à jour de [`mvp-dod-traceability.md`](../data/mvp-dod-traceability.md).
