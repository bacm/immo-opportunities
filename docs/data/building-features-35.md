# Features de bâtiment — département 35

**Généré le** 2026-09-16 par `make building-features` — ticket [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md), [ADR-024](../decisions/ADR-024-sujet-des-features-batiment.md).

Les features `BLD-001..003` et `REN-001..008` portent sur le **bâtiment physique**, regroupement `rnb` de `reference.physical_building` (BUG-12). Leurs sources sont `display_only` : chacune est écrite absente, `source_not_accepted`, pour chaque bâtiment physique `rnb` du département.

## Regroupements

| Regroupement | Bâtiments physiques | Enregistrements regroupés |
|---|---:|---:|
| `cadastre` | 517 615 | 865 335 |
| `rnb` | 514 859 | 741 379 |

## Lignes écrites

| Feature | Motif d'absence | Releases citées | Bâtiments physiques |
|---|---|---|---:|
| BLD-001 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| BLD-002 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| BLD-003 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| REN-001 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| REN-002 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| REN-003 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-04@2026-06-15` | 514 859 |
| REN-004 | `source_not_accepted` | `DS-07@2026-09-14-extract` | 514 859 |
| REN-005 | `source_not_accepted` | `DS-07@2026-09-14-extract` | 514 859 |
| REN-006 | `source_not_accepted` | `DS-07@2026-09-14-extract` | 514 859 |
| REN-007 | `source_not_accepted` | `DS-07@2026-09-14-extract` | 514 859 |
| REN-008 | `source_not_accepted` | `DS-03@2026-02-a`, `DS-05@2026-06-17`, `DS-07@2026-09-14-extract` | 514 859 |

## Sujets de `feature.feature_value`, tout le territoire

| Sujet | Lignes |
|---|---:|
| unité foncière | 19 999 905 |
| enregistrement RNB (`building_id`) | 0 |
| bâtiment physique | 5 663 449 |
| bâtiment physique, feature hors `BLD`/`REN` | 0 |

La base refuse une feature `BLD-*` ou `REN-*` sur un enregistrement (`feature_value_building_family_subject`). Qu'aucune autre feature ne porte sur un bâtiment physique est un constat de ce rapport, pas une contrainte.
