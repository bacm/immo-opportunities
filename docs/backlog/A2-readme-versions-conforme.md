# A2 — Une seule version « En cours » dans le suivi

**Version :** transverse · **Taille :** S · **État :** Terminé

## Contexte à charger

- `docs/versions/README.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme constaté

La règle de suivi « une seule version peut être `En cours` » était violée : **trois** versions
l'étaient simultanément (v0.3, v0.5, v0.8), et deux états hors nomenclature étaient utilisés
(`Implémenté`, `En cours — socle technique livré`).

La cause est un glissement de sens : le code livré en avance sur ses données était compté comme
avancement. Une version dont les critères dépendent d'une donnée absente n'est pas active, elle
est bloquée.

## Correction appliquée

| Version | Avant | Après |
|---|---|---|
| v0.3 Référentiel spatial | En cours | **En cours** (seule version active) |
| v0.5 Données métier | En cours | Bloquée (v0.3) |
| v0.7 MVP connecté | Implémenté | Bloquée (publication v0.6) |
| v0.8 Pilote Bretagne | En cours | Bloquée (données 35 et terrain) |

Fichiers modifiés : [`docs/versions/README.md`](../versions/README.md),
[`v0.5-market-data.md`](../versions/v0.5-market-data.md),
[`v0.7-connected-mvp.md`](../versions/v0.7-connected-mvp.md),
[`v0.8-brittany-pilot.md`](../versions/v0.8-brittany-pilot.md).

Une règle explicite a été ajoutée au README pour empêcher la récidive :

> Le code livré en avance sur une dépendance ne vaut pas avancement : une version dont les critères
> dépendent d'une donnée absente reste `Bloquée` avec son motif, jamais `En cours`.

## Reste à faire

- Aucun développement. À revérifier à chaque changement d'état de version : le passage d'une
  version à `Terminée` doit s'accompagner du passage d'**exactement une** suivante à `En cours`.
