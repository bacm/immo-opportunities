# ADR-022 — Une release remplacée se retire sur décision explicite, tracée

**Date :** 16 septembre 2026

**Contexte.** Les contrats déclarent `observations: append-only by release` : une nouvelle release
s'ajoute, la précédente reste. Rien ne permet de la retirer, sauf
`meta.rollback_unpublished_dataset_release`, qui ne purge que les tables du cadastre (DS-01) et
refuse toute release ayant été publiée. Au 16 septembre 2026, aucune release remplacée n'encombre
la base (29 Gio) ; mais le radar prévoit une release DS-07 par semaine, soit environ 208 000
diagnostics et 40 000 écarts d'import par extrait, une dizaine de millions de lignes par an.

**Alternatives écartées.**

- *Tout garder.* Aucun geste, mais un volume qui croît sans que personne l'ait décidé.
- *Garder les N derniers millésimes.* Borne le volume par une profondeur que rien ne fonde.

**Décision.**

1. **Le retrait est un geste explicite**, comme l'acceptation et la publication :
   `meta.retire_replaced_dataset_release(release, remplaçante, acteur, motif)`. Le motif est
   obligatoire ; acteur, motif, remplaçante et date s'écrivent dans les notes de la release, qui
   passe en `retired`. La ligne de release n'est jamais supprimée.
2. **Garde-fous.** La remplaçante est de la même source, distincte, non retirée, importée avec
   succès sur chaque territoire importé par la release retirée. La release retirée n'est ni active
   ni membre d'un bundle régional. Une release **publiée** peut être retirée une fois remplacée :
   c'est le cas normal d'un changement de millésime ; son historique de publication reste.
3. **La purge couvre toutes les données portées par la release** : observations spatiales (et
   leurs liens), ventes, diagnostics, urbanisme, risques, routes, quarantaines, métriques de
   couverture et d'appariement, contrôles, runs d'import, tables du cadastre. La purge du
   `rollback` des releases non publiées est étendue de la même façon.
4. **Ce qui reste.** Les fichiers bruts archivés et leur ligne `meta.raw_asset` (la source reste
   reproductible), les identifiants de source (`entity_source_identifier`, qui disent la
   continuité d'une identité d'une release à l'autre), les décisions d'appariement
   (`entity_match`, que la revue B4 référence) et l'historique de publication.
5. **Le jugement reste humain.** Deux releases d'une même source ne se remplacent pas toujours :
   les deux releases DVF couvrent des millésimes différents. La fonction vérifie la forme ; le
   motif écrit porte le jugement.

**Conséquences.**

- `make release-volume` montre le volume par release ; `make release-retire` exécute le geste.
- Réimporter une release retirée reste possible depuis son archive.
- Les décisions d'appariement d'une release retirée restent en base : leur sort, s'il faut un jour
  le trancher, demandera sa propre décision.
- **Les valeurs dérivées gardent leur provenance, pas leurs données.** `feature.feature_value`,
  `market.market_metric`, `meta.entity_match` et `scoring.*` citent des releases par tableau
  d'identifiants. La ligne de release restant en base (`retired`, avec sa note), ces références ne
  sont pas pendantes ; mais les observations qu'elles citent ont disparu. Une valeur dérivée d'une
  release retirée n'est plus recalculable sans réimport depuis l'archive : retirer une release
  dont dérivent des valeurs encore lues suppose de les recalculer d'abord sur la remplaçante.
