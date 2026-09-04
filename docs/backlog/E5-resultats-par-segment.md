# E5 — Résultats par segment urbain / périurbain / littoral / rural

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Dépend de :** E4 · **Bloque :** clôture de v0.6

## Contexte à charger

- `pipelines/src/immo_pipelines/scoring/engine.py` (segmentation)
- `docs/data/scoring-v0.6-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DoD de v0.6 ouverte : « Résultats par segment documentés ». Critère d'acceptation associé :
« aucun segment critique ne masque une dégradation régionale ».

Un score globalement correct peut être inutilisable sur le rural, qui représente l'essentiel du
volume de parcelles en Bretagne. Une moyenne départementale masquerait exactement ce que le pilote
révélerait ensuite douloureusement.

## Segments

Les cinq segments du protocole existant, appliqués au 35 :

| Segment | Enjeu propre |
|---|---|
| Urbain (Rennes et communes denses) | volume de comparables élevé, contraintes PLU fortes |
| Périurbain | dynamique de division / extension la plus forte |
| Littoral | prix atypiques, risques de submersion et de recul du trait de côte |
| Rural | faible densité de transactions, support statistique limité |
| Cas frontières | communes à cheval sur deux dynamiques |

## Travail à réaliser

1. Rejouer les métriques de [E4](./E4-backtest-baseline.md) segment par segment : précision top
   10 / 20 / 50 contre baseline, ablations.
2. Publier, pour chaque segment, le volume d'unités éligibles et la couverture des features.
3. Identifier les segments où le score n'apporte rien ou dégrade par rapport à la baseline.
4. Décider, pour chaque segment défaillant : restreindre le périmètre de publication, ou publier
   avec un avertissement explicite. Documenter la décision.
5. Vérifier que la segmentation elle-même repose sur la donnée observée et non sur un découpage
   administratif choisi — cohérence avec les segments de marché définis en [D1](./D1-import-dvf-ds06.md).

## Points de vigilance

- Un segment à faible volume produit des métriques instables : publier les volumes et ne pas
  conclure sur un segment trop petit.
- Le rural est le test le plus sévère : peu de transactions, donc peu de comparables, donc beaucoup
  d'absences. Si le score n'y fonctionne pas, c'est une limite produit majeure à connaître avant G8.
- La restriction du périmètre de publication est une réponse acceptable ; l'ajustement de seuils
  par segment pour faire remonter une métrique ne l'est pas, sauf si le profiling par segment le
  justifie explicitement (décision prise en [E1](./E1-profiling-distributions.md)).

## Critères d'acceptation

- métriques publiées pour chacun des cinq segments, y compris défavorables ;
- volumes publiés à côté des taux ;
- décision documentée pour chaque segment défaillant ;
- v0.6 peut être passée à `Terminée` et v0.7 à `En cours`.

## Preuve à produire

Section par segment dans `docs/data/scoring-backtest-35.md`, et mise à jour de
[`mvp-dod-traceability.md`](../data/mvp-dod-traceability.md) sur la ligne « Performance par segment ».
