# BUG-13 — Une feature de bâtiment ne peut se poser que sur un enregistrement, pas sur un bâtiment

**Version :** dette transverse · **Taille :** M · **État :** Terminé
**Dépend de :** — · **Bloque :** —
**Touche :** backend/migrations/versions/, pipelines/scripts/compute_morphology_features.py, pipelines/scripts/compute_urban_features.py, pipelines/scripts/compute_building_features.py, pipelines/scripts/dpe_matching_report.py, pipelines/scripts/market_data_quality_report.py, pipelines/scripts/exploratory_candidates.py, pipelines/tests/, Makefile, docs/data/building-features-35.md
**Nature :** implémentation
**DoD :** preuve dans `docs/data/building-features-35.md`, recomptée
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

## Choix retenus — 16 septembre 2026

Pris par l'agent sur délégation du porteur (« enchaîne en prenant les meilleures décisions »).

- **Sujet** : une troisième colonne, `physical_building_id`, vers `reference.physical_building`.
  L'exclusion reste stricte : `num_nonnulls(property_unit_id, building_id, physical_building_id)
  = 1`. Une contrainte interdit en plus d'écrire `BLD-*` ou `REN-*` sur un enregistrement
  (`building_id`). Porter les features sur `physical_building` sans passer par `feature_value`
  aurait dédoublé le stockage des features et leur provenance.
- **Regroupement** : les bâtiments physiques de source `rnb` (514 859, BUG-12) — ceux auxquels les
  DPE se rattachent par `id_rnb`. Les 517 615 regroupements cadastraux servent `LAND-009`.
- **Valeurs** : BDNB et BD TOPO (BLD, REN-001..003) et DPE (REN-004..008) sont `display_only`.
  `SPEC.md` §13.8 : une source `display_only` n'alimente pas un score. Les onze features sont
  écrites absentes, `source_not_accepted`, pour chaque bâtiment physique — comme `LAND-008` l'est
  déjà pour chaque unité foncière. Le motif n'est plus « schéma impossible ».
- **Écriture ensembliste** : une requête par feature, sans passer par le moteur Python, puisque
  aucune valeur n'est calculée. Le script **refuse de s'exécuter** si l'une de ces sources devient
  acceptée : le calcul réel demandera alors ses chargeurs, sous ticket.
- **Volume** : environ 5,7 millions de lignes, un peu plus de 2 Gio au rythme de la table.
- **Migration 0028**, `downgrade` réel : supprime les lignes portées par un bâtiment physique,
  puis la colonne, et rétablit la contrainte précédente.

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

## Résultat — 16 septembre 2026

- [ADR-024](../decisions/ADR-024-sujet-des-features-batiment.md) ; migration
  `20260917_0028` appliquée, puis `downgrade` et `upgrade` rejoués sur la base réelle : les
  19 999 905 features d'unité foncière restent en place à chaque sens.
- En base, dans une transaction annulée : une `BLD-001` sur un enregistrement RNB est refusée
  (`feature_value_building_family_subject`), une ligne à deux sujets aussi
  (`feature_value_subject`), une ligne sur un bâtiment physique est acceptée.
- `make building-features DEPARTMENT=35` : **5 663 449** lignes, soit 514 859 bâtiments physiques
  RNB × 11 features, toutes `source_not_accepted`, avec les releases lues (DS-03, DS-04, DS-05,
  DS-07). Une seconde exécution laisse le compte inchangé. La table passe à 10 Gio.
- Aucune ligne sur `building_id` ; aucune feature hors `BLD`/`REN` sur un bâtiment physique, et
  aucune `BLD`/`REN` sur une unité foncière. Seul le premier point est imposé par une contrainte ;
  les deux autres sont contrôlés par le rapport. Tous les enregistrements RNB du 35 (741 379 ;
  741 376 au compte de BUG-12) sont membres d'un regroupement.
  Rapport : [`building-features-35.md`](../data/building-features-35.md).
- Les écritures de `LAND-*` et `URB-*` visent la nouvelle identité (`ON CONFLICT` à trois
  colonnes de sujet), et un test l'impose.
- B5, D4, D5, D6b relus : leur constat « en attente du schéma » n'a plus d'objet, une note datée
  le dit. Les rapports `dpe-matching`, `dpe-neuf-matching` et `market-data-quality` le disent
  aussi, générateurs compris.
- Recompte `recompte-preuve` : tous les chiffres confirmés. Corrigés à sa suite : la portée de la
  contrainte, le compte d'enregistrements RNB, les dates. Signalé : la release DS-07 citée n'est
  pas active pour le 35 (`meta.active_dataset_release`), ce qui est cohérent avec son statut
  `display_only`, non accepté.
- **Reste à faire, hors de ce ticket.** Les valeurs : elles attendent l'acceptation de BDNB, BD
  TOPO, BAN ou DPE, puis leurs chargeurs. BDNB n'a toujours aucun rattachement au RNB : c'est un
  appariement géométrique (E8e), pas un schéma.
