# D7 — Population, logements, équipements et aires d'attraction : les variables qui séparent les marchés

**Version :** v0.5 · **Taille :** L · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/import_territorial_release.py, pipelines/scripts/territorial_variables_report.py, pipelines/src/immo_pipelines/market_data/territorial.py, pipelines/tests/test_territorial.py, pipelines/tests/test_import_traceability.py, backend/migrations/versions/, backend/tests/test_territorial_indicator_migration_contract.py, contracts/datasets/DS-14/, contracts/datasets/DS-15/, contracts/datasets/DS-16/, contracts/datasets/README.md, docs/data/territorial-variables-35.md, docs/data/README.md, docs/decisions/ADR-023-sources-territoriales.md, Makefile, SPEC.md, ARCHITECTURE.md
**Dépend de :** D1 · **Bloque :** E6
**Demandé par :** conversation du 14 septembre 2026, à la clôture de D1 ; lancé le 16 septembre 2026
(« La suite ? » — « Go »)
**DoD :** preuve dans `docs/data/territorial-variables-35.md`, recomptée

## Contexte à charger

- `SPEC.md` §6.4, §12, §13.1, §13.3, §13.6, §13.7, §13.8, §13.9 — ces sections seulement
- [ADR-023](../decisions/ADR-023-sources-territoriales.md)
- `pipelines/scripts/pin_georisques_release.py`, `pipelines/scripts/import_georisques_release.py`
  (modèle d'épinglage et d'import à granularité communale)
- `pipelines/src/immo_pipelines/cadastre/manifest.py`, `archive.py`, `catalog.py`

## Choix retenus — 16 septembre 2026

- **Identifiants.** `SPEC.md` §13.1 réserve DS-10 à DS-12 (Sitadel, MAJIC PM, BODACC/Sirene) :
  le ticket les réutilisait par erreur. Les sources prennent **DS-14** (recensement : populations
  de référence et logements), **DS-15** (base permanente des équipements) et **DS-16** (zonage en
  aires d'attraction des villes 2020) — [ADR-023](../decisions/ADR-023-sources-territoriales.md).
- **Stockage — décision du porteur.** Une table `observation.territorial_indicator`, une ligne
  par release × commune × indicateur, valeur ou motif d'absence ; ajoutée à la purge d'ADR-022.
- **Pôles — décision du porteur.** Le pôle d'une commune est la commune-centre de son aire
  d'attraction (INSEE, AAV 2020) ; aucun seuil de population choisi ici.
- **Équipements.** La BPE de l'INSEE, pas les points d'intérêt de la BD TOPO : source officielle,
  millésimée, dénombrée par commune et par type ; la BD TOPO n'a pas de nomenclature équivalente.
- **Fichiers.** Distribution Melodi de l'INSEE (CSV zippé) pour DS-14 et DS-15, fichier XLSX du
  zonage pour DS-16, lu avec la bibliothèque standard (aucune dépendance). Les URL Melodi ne sont
  pas datées : copie archivée nommée au manifeste, SHA-256 épinglé (SPEC §13.9). Extrait
  départemental trié, gzip, archivé, comme DS-09.
- **Géographie.** Les trois fichiers sont en géographie au 1er janvier 2025 et couvrent les 332
  communes du 35 : aucune table de passage.
- **Distance au pôle** : entre centroïdes Lambert-93 des communes de `reference.area`, calculée à
  l'import de DS-16 et tracée avec la release DS-01 lue.
- **Pas de script d'épinglage.** Les manifestes portent l'empreinte des fichiers nationaux amont
  et nomment leur archive ; `resolve_asset` télécharge, vérifie et archive au premier import.
- **Logements retenus** : total, résidences principales, résidences secondaires et occasionnelles,
  maisons, appartements (2023, autres dimensions agrégées). **Équipements** : total, 7 domaines,
  27 sous-domaines ; le détail par type n'est pas lu.

## Résultat — 16 septembre 2026

- **Trois releases** importées sur les 332 communes du 35, verdict `display_only` :
  `DS-14@rp-2023` (2 656 lignes), `DS-15@bpe-2025` (11 620), `DS-16@aav2020-geo2025` (1 660, dont
  92 absences motivées). Preuve : [`territorial-variables-35.md`](../data/territorial-variables-35.md),
  régénérée par `make territorial-report`.
- **Distance au pôle** : 284 communes mesurées, 44 hors attraction (`not_applicable`), 4 dont la
  commune-centre est hors du 35 — Guer (56075) pour trois, Pontorson (50410) pour une
  (`source_value_missing`).
- **Transport.** Le fichier logements (98 Mo) cale à ~34 Mo en téléchargement continu depuis
  Melodi ; il a été reconstitué par plages HTTP, vérifié par son SHA-256, et déposé à la clé
  d'archive du manifeste avant l'import (origine `manifest_archive` au run). Les trois autres
  fichiers viennent de l'amont (`upstream`).
- **Migration** `20260917_0027` : montée, descente, remontée exécutées sur la base locale.
- **Recompte** (`recompte-preuve`, sous-agent isolé du code, deux chemins : fichiers bruts et
  base) : tous les chiffres confirmés. Trois écarts de forme, corrigés : le run DS-16 ne comptait
  pas les 332 distances dans `normalized_row_count` (réimporté : 1 328 lues, 1 660 écrites) ;
  l'arrondi au demi pair n'était pas déclaré (désormais demi vers le haut, déclaré) ; la mention
  « en vigueur au 1er janvier 2026 » n'était pas établie par la source archivée (retirée).
- **Débloque E6**, qui attend encore E1. Constat reporté dans E6 : la classification littorale
  n'existe pas en base.

## Contexte

[D1](./D1-import-dvf-ds06.md) a renvoyé les **segments de marché** à
[E1](./E1-profiling-distributions.md), en laissant une mesure parlante : le prix au m² d'un
terrain va de **1 € à 181 € entre quartiles**, parce qu'il mêle terres agricoles et terrains à
bâtir. Un comparable tiré sans segment est un comparable faux.

`scoring.segment_definition` existe déjà, en `draft`, avec cinq segments — `rural`, `coastal`,
`periurban`, `medium_city`, `metropolitan` — et `thresholds: profiling_required`. Le mécanisme
attend ses variables.

La stratification de [B4](./B4-revue-manuelle-appariements.md) en a utilisé deux, faute de mieux :
la limite terre-mer de la BD TOPO pour le littoral, et les tercies du **nombre de parcelles par
commune** comme approximation de densité. La seconde est un proxy grossier : elle confond une
commune dense et une commune très découpée.

Ce ticket apporte les variables qui manquent.

## Ce que le produit possède déjà, et ce qu'il n'a pas

| Variable | État |
|---|---|
| Classification littorale | existe — limite terre-mer BD TOPO |
| Distance aux pôles urbains | **calculable** — géométries de communes en base |
| **Population communale** | **absente** — source à importer |
| **Équipements : commerces, écoles, santé** | **absentes** — source à importer |

## Travail à réaliser

1. **DS-10 — population et logements.** Recensement INSEE au niveau communal. Contrat, manifeste
   checksumé, import relançable, verdict d'acceptation motivé. Millésime figé, jamais un alias.
2. **DS-11 — équipements.** Base permanente des équipements de l'INSEE, ou les points d'intérêt
   de la BD TOPO si leur couverture est suffisante — à instruire, pas à présumer.
3. **Distance aux pôles** calculée depuis `reference.area`, sans nouvelle source.
4. Publier la distribution observée de chaque variable sur le 35, comme entrée de
   [E6](./E6-segmentation-observee.md).

## Points de vigilance

- **Ces variables décrivent une commune, pas une parcelle.** Les rattacher à une parcelle est une
  jointure administrative, pas une mesure : une commune n'est pas homogène, et une variable
  communale appliquée à une parcelle porte une incertitude qui doit rester visible.
- **Aucun seuil ici.** Ce ticket importe et mesure ; découper appartient à E6, sur distribution
  observée.
- **Une couverture partielle est un résultat.** Si la BPE ne couvre pas certaines communes, elles
  portent une variable absente avec motif, jamais une valeur imputée.

## Critères d'acceptation

- deux releases réelles, archivées, checksumées, importées et auditées sur le 35 ;
- verdict d'acceptation écrit pour chacune ;
- distributions publiées dans `docs/data/` ;
- aucune variable imputée, aucune moyenne de substitution.
