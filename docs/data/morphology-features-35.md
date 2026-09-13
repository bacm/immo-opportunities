# Features morphologiques — département 35

**Date :** 13 septembre 2026 · **Ticket :** [B5](../backlog/B5-features-morphologiques.md)
**Unités calculées :** 1 333 327 · **Transformation :** `morphology@1` · **Version :** 1

## Une seule release est acceptée, et c'est ce qui gouverne tout

| Source | Statut | Effet |
|---|---|---|
| **Cadastre Etalab** `2026-06-01` | **`accepted`** | seule base de calcul |
| RNB `2026-09-05` | `pending` | jamais accepté |
| BD TOPO `2026-06-15` | `display_only` | `LAND-008` absente |
| BDNB `2026-02-a` | `display_only` | `BLD-001..003` indisponibles |
| BAN `2026-06-17` | `display_only` | sans effet ici |

Le RNB n'a **jamais** été accepté. [B4](./spatial-matching-manual-review-35.md) a accepté
l'appariement d'identité BD TOPO ↔ RNB, mais c'est une acceptation de *relation*, pas de
*release* : deux portes distinctes, et la seconde n'a pas été franchie.

Cela ne gêne pas : le contrat `morphology-v1` liste `datasets: [DS-01, DS-03, DS-04]`, **sans
DS-02**. Le bâti utilisé est donc le bâti cadastral, ce que le contrat demandait depuis le début —
et il est levé avec le parcellaire, donc cohérent avec lui par construction.

Les bâtiments sont comptés **dédupliqués**, par `reference.physical_building`
([BUG-12](../backlog/BUG-12-deduplication-batiments-physiques.md)) : compter les enregistrements
surestimerait `LAND-009` de 44 %.

## Distributions observées

| Feature | Calculées | Absentes | Min | Q1 | Médiane | Q3 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `LAND-001` surface parcellaire (m²) | 1 333 327 | 0 | 0,01 | 280 | **813** | 4 132 | 59 385 | 1 729 173 |
| `LAND-002` emprise bâtie (m²) | 1 333 327 | 0 | 0 | 0 | **0** | 92 | 1 078 | 392 115 |
| `LAND-003` taux d'emprise | 1 333 327 | 0 | 0 | 0 | **0** | 0,17 | 1,00 | 1,00 |
| `LAND-004` surface non bâtie (m²) | 1 333 327 | 0 | 0 | 219 | **718** | 4 039 | 59 174 | 1 729 173 |
| `LAND-005` compacité | 1 333 327 | 0 | 0 | 0,42 | **0,60** | 0,71 | 0,81 | 1,00 |
| `LAND-006` largeur approchée (m) | 1 333 327 | 0 | 0,01 | 11,6 | **23,1** | 50,7 | 246 | 1 758 |
| `LAND-007` distance bâti ↔ limite (m) | 638 306 | **695 021** | 0 | 0 | **0** | 0 | 9,0 | 142 |
| `LAND-008` accès à la voirie | **0** | **1 333 327** | — | — | — | — | — | — |
| `LAND-009` nombre de bâtiments | 1 333 327 | 0 | 0 | 0 | **0** | 1 | 4 | 101 |
| `LAND-010` part de bâti léger | **0** | **1 333 327** | — | — | — | — | — | — |

**Aucune valeur imputée.** Aucun zéro de substitution : les zéros de `LAND-002`, `LAND-003` et
`LAND-009` sont des parcelles réellement non bâties, ce que confirme la médiane de `LAND-009`
à 0 — plus de la moitié des parcelles du 35 ne portent aucun bâtiment.

## Les absences, et leurs trois motifs distincts

| Feature | Motif | Pourquoi |
|---|---|---|
| `LAND-007` | `not_applicable` (695 021) | la parcelle ne porte aucun bâtiment : il n'y a pas de distance à mesurer, ce n'est pas une donnée manquante |
| `LAND-008` | `source_not_accepted` (1 333 327) | la voirie vient de la BD TOPO, `display_only` |
| `LAND-010` | `source_value_missing` (1 333 327) | voir ci-dessous |

### `LAND-010` : le champ existe, sa signification n'est pas au contrat

Le cadastre distingue bien deux types de bâti, et **27,1 %** des enregistrements portent le
code `02`. Mais `contracts/datasets/DS-01/v1.json` déclare `type` comme `string|null`, **sans
table de valeurs**. Décider ici que `02` signifie « léger » serait inventer une interprétation,
au moment précis où le produit s'interdit d'inventer.

La feature reste donc absente jusqu'à ce que la table de valeurs soit sourcée et écrite au
contrat. C'est un travail court, et il débloque une feature entière.

### `BLD-001..003` : indisponibles, et le sujet ne correspond pas

Leurs sources, BDNB et BD TOPO, sont `display_only` : les trois sortiraient en
`source_not_accepted`.

Mais l'obstacle est plus profond. `feature.feature_value.building_id` réfère
`reference.building`, c'est-à-dire les **enregistrements RNB**. Or BUG-12 a établi que le sujet
du contrat est le **bâtiment physique**, et que compter des enregistrements surestime de 44 %.
Matérialiser ces lignes graverait dans le stockage le sujet que BUG-12 vient d'invalider — et sur
une source qui n'est même pas acceptée.

C'est un changement de schéma, hors du périmètre de B5, et il doit précéder toute matérialisation
des features bâtiment.

## Anomalies relevées, aucune écrêtée

### Cinq taux d'emprise supérieurs à 1

`LAND-003` est borné à 1 au contrat, avec `out_of_range: flag`. Cinq unités le dépassent :

| Unité | Taux | Surface parcelle | Emprise |
|---|---:|---:|---:|
| `35238000AI0623` | 1,000000000171 | 0,248129311083 | 0,248129311126 |
| `35055000AP0164` | 1,000000000005 | 369,263480466158 | 369,263480467863 |
| `352920110B0822` | 1,000000000004 | 116,076669596502 | 116,076669596957 |
| `35238000BW0557` | 1,0000000000005 | 124,342552308270 | 124,342552308332 |
| `35145000ZI0061` | 1,0000000000005 | 47,550092529095 | 47,550092529119 |

Ce sont des **parcelles entièrement bâties**, dont l'aire de l'intersection égale l'aire de la
parcelle à la précision de la virgule flottante près. L'écart est de l'ordre de 10⁻¹³ à 10⁻¹⁰.

Elles sont **signalées et non corrigées**. Écrêter à 1 donnerait un résultat visuellement propre
et masquerait le fait que le calcul travaille au bord de la précision machine — exactement
l'écrêtage silencieux que le ticket interdit.

### 1 981 parcelles de moins de 1 m²

Dans la plage contractuelle — `LAND-001` n'a pas de minimum autre que 0 — mais absurdes au
regard du sens. La plus petite mesure **0,01 m²**, soit un carré d'un centimètre de côté.

Ce sont probablement des résidus de découpage cadastral. Elles ne sont pas écartées : elles
entreront dans le profiling de [E1](../backlog/E1-profiling-distributions.md), qui décidera si
une surface minimale a du sens — **sur distribution observée, jamais sur seuil choisi d'avance.**

## Features désactivées, par commune

`LAND-008` et `LAND-010` sont désactivées sur les **332 communes** du 35, sans exception :
vérifié, `LAND-008` n'a de valeur dans aucune commune. La désactivation est uniforme parce que la
cause l'est — une release `display_only` et une table de valeurs absente valent pour tout le
département.

## Provenance

Chaque valeur porte sa release source, sa formule et sa version de transformation. La provenance
permet de remonter à la release exacte, ce qui rendra le score explicable en
[E3](../backlog/E3-publier-snapshots.md) et reproductible après changement de millésime.

## Reproduire

```bash
make physical-buildings SOURCE=cadastre DEPARTMENT=35   # prérequis, BUG-12
make morphology-features DEPARTMENT=35
```

## Ce que ces distributions sont

La **première moitié** de l'entrée de [E1](../backlog/E1-profiling-distributions.md). Les seuils
du scoring viendront de là et des distributions métier de D5 — jamais d'une valeur choisie a
priori.
