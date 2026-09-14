# BUG-13 — Une feature de bâtiment ne peut se poser que sur un enregistrement, pas sur un bâtiment

**Version :** dette transverse · **Taille :** M · **État :** À faire
**Dépend de :** — · **Bloque :** —
**Touche :** backend/migrations/versions/, pipelines/scripts/compute_morphology_features.py, pipelines/scripts/compute_renovation_features.py
**Découvert par :** [B5](./B5-features-morphologiques.md), reconstaté par [D4](./D4-import-dpe-ds07.md) le 14 septembre 2026

## Contexte à charger

- `backend/migrations/versions/20260806_0011_market_data.py` (`feature.feature_value`)
- `docs/backlog/BUG-12-deduplication-batiments-physiques.md`
- `docs/backlog/B5-features-morphologiques.md` §« Deux constats qui appellent une suite »

Ne rien charger d'autre sans nécessité démontrée.

## Le défaut

`feature.feature_value.building_id` référence `reference.building`, c'est-à-dire les
**enregistrements RNB**. [BUG-12](./BUG-12-deduplication-batiments-physiques.md) a établi que le
sujet du contrat est le **bâtiment physique** : 741 376 enregistrements RNB regroupent 514 859
bâtiments, et compter les premiers surestime de 44 %.

Une feature écrite sur un enregistrement est donc écrite sur un sujet que le produit sait faux.
Le stockage ne peut pas exprimer le bon.

## Ce que ça a déjà coûté

Deux tickets ont buté dessus et ont, chacun, choisi de ne pas matérialiser plutôt que de graver
le mauvais sujet :

| Ticket | Features non matérialisées | Conséquence |
|---|---|---|
| [B5](./B5-features-morphologiques.md) | `BLD-001..003` | absentes avec motif, v0.3 close quand même |
| [D4](./D4-import-dpe-ds07.md) | `REN-001..008` | distributions publiées au rapport, rien en base |

Les deux ont eu raison. Mais la dette se paie une troisième fois à chaque ticket qui touche une
feature de bâtiment, et [E1](./E1-profiling-distributions.md) profilera des distributions qu'elle
devra recalculer faute de les trouver en base.

## Travail à réaliser

1. Trancher le sujet : `reference.physical_building` porte-t-il les features de bâtiment, ou
   `feature_value` gagne-t-il une troisième colonne de sujet ? La contrainte
   `feature_value_subject` (`num_nonnulls(property_unit_id, building_id) = 1`) doit rester une
   exclusion stricte.
2. Migration, avec `downgrade` réel.
3. Matérialiser `BLD-001..003` et `REN-001..008` sur le sujet corrigé.
4. Vérifier qu'aucune feature déjà écrite — `LAND-*`, `URB-*`, qui portent sur l'unité foncière
   et non sur le bâtiment — n'est déplacée par erreur.

## Tests obligatoires

- une feature de bâtiment ne peut pas être écrite sur un enregistrement source ;
- le regroupement de BUG-12 est celui qui porte la feature, et le compte le prouve ;
- `downgrade` restitue le schéma précédent sans perte de feature d'unité foncière.

## Critères d'acceptation

- `BLD-001..003` et `REN-001..008` matérialisées, ou absentes avec un motif qui n'est plus celui-ci ;
- B5 et D4 relus : leur constat « en attente d'un changement de schéma » n'a plus d'objet.
