# Volume par release

**Généré le** 2026-09-16 par `make release-volume` — ticket [BUG-08](../backlog/BUG-08-cycle-de-vie-des-releases-remplacees.md), [ADR-022](../decisions/ADR-022-retrait-des-releases-remplacees.md).

Base entière : **29 GB** (unités binaires). Les lignes comptées sont
celles des tables que le retrait purge directement ; les enfants en cascade (liens
d'observation, lots de vente, zones et prescriptions d'urbanisme) partent avec elles
et ne sont pas comptés. « Publiée » : au moins un événement de publication, même si la
release n'est plus active. « Retirable » ne veut pas dire « remplacée » : deux releases
d'une source peuvent se compléter, comme les deux releases DVF ; le motif écrit du
retrait porte ce jugement. Les valeurs dérivées d'une release retirée gardent sa
référence mais plus ses données (ADR-022).

| Source | Release | Cycle | Acceptation | Publiée | Lignes | Statut |
|---|---|---|---|:---:|---:|---|
| DS-01 | `DS-01@2026-06-01` | validated | accepted | oui | 2 200 008 | active — non retirable |
| DS-02 | `DS-02@2026-08-01` | discovered | pending | non | 0 | retirable si remplacée |
| DS-02 | `DS-02@2026-09-05` | discovered | accepted | non | 742 049 | retirable si remplacée |
| DS-03 | `DS-03@2026-02-a` | validated | display_only | oui | 546 969 | active — non retirable |
| DS-04 | `DS-04@2026-06-15` | validated | display_only | oui | 1 366 056 | active — non retirable |
| DS-05 | `DS-05@2026-06-17` | validated | display_only | oui | 438 768 | active — non retirable |
| DS-06 | `DS-06@2019-04-archive` | discovered | pending | non | 179 575 | retirable si remplacée |
| DS-06 | `DS-06@2026-09-13` | discovered | display_only | non | 133 068 | retirable si remplacée |
| DS-07 | `DS-07@2026-09-14-extract` | validated | display_only | non | 248 893 | retirable si remplacée |
| DS-08 | `DS-08@2026-09-14` | validated | display_only | non | 185 | retirable si remplacée |
| DS-09 | `DS-09@cavity--2026-09-14` | validated | display_only | non | 512 | retirable si remplacée |
| DS-09 | `DS-09@clay--2026-09-14` | validated | display_only | non | 1 761 | retirable si remplacée |
| DS-09 | `DS-09@flood-atlas--2026-09-14` | validated | display_only | non | 606 | retirable si remplacée |
| DS-09 | `DS-09@gaspar-risks--2026-09-14` | validated | display_only | non | 2 063 | retirable si remplacée |
| DS-09 | `DS-09@industrial-installation--2026-09-14` | validated | display_only | non | 3 921 | retirable si remplacée |
| DS-09 | `DS-09@landslide--2026-09-14` | validated | display_only | non | 705 | retirable si remplacée |
| DS-09 | `DS-09@natural-disaster--2026-09-14` | validated | display_only | non | 1 818 | retirable si remplacée |
| DS-09 | `DS-09@radon--2026-09-14` | validated | display_only | non | 665 | retirable si remplacée |
| DS-09 | `DS-09@soil-pollution--2026-09-14` | validated | display_only | non | 522 | retirable si remplacée |
| DS-09 | `DS-09@sup--2026-09-14` | validated | display_only | non | 1 581 | retirable si remplacée |
| DS-13 | `DS-13@2026-09-16-extract` | validated | display_only | non | 44 735 | retirable si remplacée |

## Détail par table

| Release | Table | Lignes |
|---|---|---:|
| `DS-01@2026-06-01` | `meta.data_quality_check` | 1 011 |
| `DS-01@2026-06-01` | `meta.import_run` | 3 |
| `DS-01@2026-06-01` | `reference.administrative_area` | 332 |
| `DS-01@2026-06-01` | `reference.cadastral_building` | 865 335 |
| `DS-01@2026-06-01` | `reference.cadastral_parcel` | 1 333 327 |
| `DS-02@2026-09-05` | `meta.data_quality_check` | 336 |
| `DS-02@2026-09-05` | `meta.entity_match_metric` | 332 |
| `DS-02@2026-09-05` | `meta.entity_source_observation` | 741 379 |
| `DS-02@2026-09-05` | `meta.import_run` | 2 |
| `DS-03@2026-02-a` | `meta.data_quality_check` | 335 |
| `DS-03@2026-02-a` | `meta.entity_match_metric` | 332 |
| `DS-03@2026-02-a` | `meta.entity_source_observation` | 546 301 |
| `DS-03@2026-02-a` | `meta.import_run` | 1 |
| `DS-04@2026-06-15` | `meta.data_quality_check` | 334 |
| `DS-04@2026-06-15` | `meta.entity_match_metric` | 332 |
| `DS-04@2026-06-15` | `meta.entity_source_observation` | 974 172 |
| `DS-04@2026-06-15` | `meta.import_run` | 1 |
| `DS-04@2026-06-15` | `observation.road_segment` | 391 217 |
| `DS-05@2026-06-17` | `meta.attribute_quarantine` | 427 |
| `DS-05@2026-06-17` | `meta.data_quality_check` | 5 |
| `DS-05@2026-06-17` | `meta.entity_match_metric` | 664 |
| `DS-05@2026-06-17` | `meta.entity_source_observation` | 437 671 |
| `DS-05@2026-06-17` | `meta.import_run` | 1 |
| `DS-06@2019-04-archive` | `meta.import_run` | 2 |
| `DS-06@2019-04-archive` | `observation.transaction` | 179 573 |
| `DS-06@2026-09-13` | `meta.import_run` | 2 |
| `DS-06@2026-09-13` | `observation.transaction` | 133 066 |
| `DS-07@2026-09-14-extract` | `meta.attribute_quarantine` | 40 465 |
| `DS-07@2026-09-14-extract` | `meta.data_quality_check` | 6 |
| `DS-07@2026-09-14-extract` | `meta.dataset_coverage_metric` | 335 |
| `DS-07@2026-09-14-extract` | `meta.import_run` | 1 |
| `DS-07@2026-09-14-extract` | `observation.energy_assessment` | 208 086 |
| `DS-08@2026-09-14` | `meta.import_run` | 1 |
| `DS-08@2026-09-14` | `observation.urban_document` | 184 |
| `DS-09@cavity--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@cavity--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@cavity--2026-09-14` | `observation.risk_observation` | 179 |
| `DS-09@clay--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@clay--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@clay--2026-09-14` | `observation.risk_observation` | 1 428 |
| `DS-09@flood-atlas--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@flood-atlas--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@flood-atlas--2026-09-14` | `observation.risk_observation` | 273 |
| `DS-09@gaspar-risks--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@gaspar-risks--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@gaspar-risks--2026-09-14` | `observation.risk_observation` | 1 730 |
| `DS-09@industrial-installation--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@industrial-installation--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@industrial-installation--2026-09-14` | `observation.risk_observation` | 3 588 |
| `DS-09@landslide--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@landslide--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@landslide--2026-09-14` | `observation.risk_observation` | 372 |
| `DS-09@natural-disaster--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@natural-disaster--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@natural-disaster--2026-09-14` | `observation.risk_observation` | 1 485 |
| `DS-09@radon--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@radon--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@radon--2026-09-14` | `observation.risk_observation` | 332 |
| `DS-09@soil-pollution--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@soil-pollution--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@soil-pollution--2026-09-14` | `observation.risk_observation` | 189 |
| `DS-09@sup--2026-09-14` | `meta.dataset_coverage_metric` | 332 |
| `DS-09@sup--2026-09-14` | `meta.import_run` | 1 |
| `DS-09@sup--2026-09-14` | `observation.risk_observation` | 1 248 |
| `DS-13@2026-09-16-extract` | `meta.attribute_quarantine` | 25 740 |
| `DS-13@2026-09-16-extract` | `meta.data_quality_check` | 6 |
| `DS-13@2026-09-16-extract` | `meta.dataset_coverage_metric` | 317 |
| `DS-13@2026-09-16-extract` | `meta.import_run` | 1 |
| `DS-13@2026-09-16-extract` | `observation.energy_assessment` | 18 671 |
