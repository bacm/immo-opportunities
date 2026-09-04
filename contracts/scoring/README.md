# Contrats de scoring

Les définitions sont immuables après création. Leur activation utilise un pointeur de publication
séparé ; elle ne modifie ni les poids ni les snapshots historiques.

- [`feature-registry-v1`](./feature-registry-v1.json) fige les features financières et les
  politiques de nécessité ;
- [`division-extension-v1`](./division-extension-v1.json) reprend les poids initiaux de la spec ;
- [`renovation-resale-v1`](./renovation-resale-v1.json) reprend les poids initiaux de la spec.

Les deux définitions restent `draft` et `publication_eligible: false` jusqu'au profiling stratifié
des distributions bretonnes. Les percentiles et scores discrets sont des entrées versionnées du
moteur : aucun seuil territorial arbitraire n'est inscrit dans ces contrats.
