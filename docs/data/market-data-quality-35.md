# Qualité des données métier — département 35

**Généré le :** 2026-09-15 · **Ticket :** [D5](../backlog/D5-rapports-qualite-metier.md)

Ce fichier est **régénéré** par `make market-data-quality`. Ne pas l'éditer à la main.

Les rapports par source restent la référence de détail : [DVF](./dvf-quality-35.md), [GPU](./gpu-coverage-35.md), [DPE](./dpe-matching-35.md), [Géorisques](./georisques-coverage-35.md).

## Verdicts et traçabilité

| Source | Releases | acceptées | `display_only` | `pending` | Runs d'import |
|---|---:|---:|---:|---:|---:|
| DS-06 DVF+ open-data | 2 | 0 | 1 | 1 | 2 |
| DS-07 DPE Logements existants depuis juillet 2021 | 1 | 0 | 1 | 0 | 1 |
| DS-08 Géoportail de l urbanisme exports CNIG | 1 | 0 | 1 | 0 | 1 |
| DS-09 Géorisques API et téléchargements | 10 | 0 | 10 | 0 | 10 |

**Aucune source métier n'est `accepted`.** Les quatre attendent la revue manuelle stratifiée de [D6](../backlog/D6-revue-manuelle-metier.md).

**Chaque release porte au moins un run d'import réussi.** Ce n'était pas le cas avant [BUG-14](../backlog/BUG-14-import-gpu-sans-trace.md) : DS-06 et DS-08 n'écrivaient aucun run, et le second ne pouvait donc recevoir aucun verdict. Le ticket relate ce que la réimportation a révélé ; ce rapport ne porte que l'état courant.

## Volumétrie et fraîcheur par source

| Source | Unité | Enregistrements | Communes | Donnée la plus récente |
|---|---|---:|---:|---|
| DS-06 | transactions | 312 639 | 353 | 2025-12-31 |
| DS-07 | diagnostics | 208 086 | 334 | 2026-09-07 |
| DS-08 | zones | 21 136 | 300 | 2026-06-25 |
| DS-09 | observations | 10 824 | 339 | 2026-09-12 |

## Complétude par feature, ventilée par motif d'absence

C'est le cœur du rapport. Quatre motifs différents n'appellent pas la même décision : une source non acceptée s'ignore en bloc, une valeur absente se mesure, un appariement ambigu se revoit à la main, une feature non applicable ne se compte pas comme un manque.

| Feature | Total | Présentes | `source_not_accepted` | `source_value_missing` | `not_applicable` | `ambiguous_match` | Somme vérifiée |
|---|---:|---:|---:|---:|---:|---:|---|
| `LAND-001` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-002` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-003` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-004` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-005` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-006` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-007` | 1 333 327 | 638 306 | 0 | 0 | 695 021 | 0 | oui |
| `LAND-008` | 1 333 327 | 0 | 1 333 327 | 0 | 0 | 0 | oui |
| `LAND-009` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |
| `LAND-010` | 1 333 327 | 0 | 0 | 1 333 327 | 0 | 0 | oui |
| `URB-001` | 1 333 327 | 1 209 188 | 0 | 122 026 | 0 | 2 113 | oui |
| `URB-002` | 1 333 327 | 0 | 0 | 1 333 327 | 0 | 0 | oui |
| `URB-003` | 1 333 327 | 947 155 | 0 | 386 172 | 0 | 0 | oui |
| `URB-004` | 1 333 327 | 0 | 0 | 1 333 327 | 0 | 0 | oui |
| `URB-005` | 1 333 327 | 1 333 327 | 0 | 0 | 0 | 0 | oui |

La dernière colonne vérifie l'invariant que D5 impose : présentes + absences par motif = volume total, par feature. Un `NON` serait un motif d'absence non prévu.

## Distributions observées

| Feature | Observations | Min | Q1 | Médiane | Q3 | Max |
|---|---:|---:|---:|---:|---:|---:|
| `LAND-001` | 1 333 327 | 0 | 280,2 | 812,7 | 4 132,5 | 1 729 172 |
| `LAND-002` | 1 333 327 | 0 | 0 | 0 | 92,3 | 392 115 |
| `LAND-003` | 1 333 327 | 0 | 0 | 0 | 0,2 | 1 |
| `LAND-004` | 1 333 327 | 0 | 218,5 | 717,6 | 4 039,0 | 1 729 172 |
| `LAND-005` | 1 333 327 | 0 | 0,4 | 0,6 | 0,7 | 0 |
| `LAND-006` | 1 333 327 | 0 | 11,6 | 23,1 | 50,7 | 1 757 |
| `LAND-007` | 638 306 | 0 | 0 | 0 | 0 | 142 |
| `LAND-009` | 1 333 327 | 0 | 0 | 0 | 1 | 101 |
| `URB-005` | 1 333 327 | 0 | 0 | 0 | 0 | 0 |

## Les communes où le moins de choses sont calculables

Un cas défavorable est une information pour le pilote, pas une gêne à masquer.

| Commune | Unités | Valeurs présentes | Lignes de feature | Part présente |
|---|---:|---:|---:|---:|
| NOYAL-SOUS-BAZOUGES (35205) | 3 352 | 27 679 | 50 280 | 55,05 % |
| BROUALAN (35044) | 2 833 | 23 416 | 42 495 | 55,10 % |
| PRINCE (35232) | 2 223 | 18 447 | 33 345 | 55,32 % |
| MONTAUTOUR (35185) | 1 411 | 11 721 | 21 165 | 55,38 % |
| SAINT ONEN LA CHAPELLE (35302) | 3 762 | 31 269 | 56 430 | 55,41 % |
| COMBLESSAC (35084) | 2 594 | 21 594 | 38 910 | 55,50 % |
| MOUTIERS (35200) | 3 368 | 28 072 | 50 520 | 55,57 % |
| VIEUX-VIEL (35354) | 2 310 | 19 262 | 34 650 | 55,59 % |
| LA SELLE-GUERCHAISE (35325) | 551 | 4 595 | 8 265 | 55,60 % |
| AVAILLES-SUR-SEICHE (35008) | 2 149 | 17 922 | 32 235 | 55,60 % |

## Un écart de vocabulaire entre sources, mesuré et non arbitré

Le BRGM cartographie l'exposition au retrait-gonflement des argiles sur **332 communes** du département, en zones. GASPAR recense commune par commune les risques faisant l'objet d'une procédure — et, sur le 35, **n'écrit jamais « Retrait-gonflement des argiles »**. Voici ce qu'il écrit :

| Libellé GASPAR, ou type canonique quand il est sourcé | Communes |
|---|---:|
| `earthquake` | 332 |
| `Tempête et grains (vent)` | 332 |
| `Phénomène lié à l'atmosphère` | 332 |
| `Transport de marchandises dangereuses` | 225 |
| `flood` | 122 |
| `Par une crue à débordement lent de cours d'eau` | 96 |
| `landslide` | 85 |
| `Tassements différentiels` | 76 |
| `Feu de forêt` | 47 |
| `Rupture de barrage` | 26 |
| `Par submersion marine` | 25 |
| `Affaissements et effondrements d'origine anthropique (anciennes carrières souterraines, hors mines)` | 6 |
| `Risque industriel` | 6 |
| `Effet thermique` | 6 |
| `Effet de surpression` | 4 |
| `Eboulement ou chutes de pierres et de blocs` | 4 |
| `Effet toxique` | 3 |
| `Recul du trait de côte et de falaises` | 1 |
| `Par une crue torrentielle ou à montée rapide de cours d'eau` | 1 |
| `Glissement de terrain` | 1 |

Les libellés restés en français sont ceux que notre table de correspondance ne couvre pas. Décréter ici que « Tassements différentiels » désigne le même aléa que la couche du BRGM serait une interprétation que le contrat DS-09 ne porte pas — la même faute que celle commise sur le champ `ETAT` du CNIG pendant D2.

L'écart est donc publié tel quel. Le combler demande la table de correspondance du producteur, pas une décision de notre part, et c'est une entrée pour [E1](../backlog/E1-profiling-distributions.md).

## Ce qui n'est pas encore profilable, et pourquoi

| Famille | État | Obstacle |
|---|---|---|
| `MKT-001..005`, `MKT-101..105` | non matérialisées | calculées au moment du score, à partir des comparables ; les segments de marché relèvent de [E1](../backlog/E1-profiling-distributions.md) |
| `REN-001..008` | non matérialisées | sujet invalidé — [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md). Distributions d'observations dans [`dpe-matching-35.md`](./dpe-matching-35.md) |
| `RISK-001..004`, `RISK-101` | non matérialisées | même sujet, et DS-09 `display_only`. Distributions dans [`georisques-coverage-35.md`](./georisques-coverage-35.md) |
| `BLD-001..003` | non matérialisées | [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md) |

Les distributions d'observations existent pour toutes ces familles, dans les rapports par source. Ce qui manque est leur matérialisation par unité, et deux obstacles la tiennent : le sujet des features de bâtiment, et le verdict de DS-08.

