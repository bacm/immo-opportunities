# DS-07 DPE — appariement et distributions sur le 35

**Généré le :** 2026-09-14 · **Release :** `DS-07@2026-09-14-extract`
· **Publiée par la source le :** 2026-09-09
· **Run d'import :** `dpe:2026-09-14-extract:35:1`
· **Verdict :** `display_only`

Ce fichier est **régénéré** par `make dpe-report`. Ne pas l'éditer à la main.

## Volumétrie

| Étape | Enregistrements |
|---|---|
| Lignes de l'extrait | 231 416 |
| Diagnostics éligibles | 231 416 |
| Rattachés à un bâtiment | 136 628 |
| Rattachés à la seule adresse | 71 458 |
| Non rattachés | 23 330 |

### Enregistrements écartés avant appariement

Aucun. Toutes les lignes de l'extrait sont des diagnostics exploitables.

Le jeu accessible est la vue virtuelle de l'ADEME, filtrée en amont sur `dpe_desactive = 0` : **un diagnostic annulé n'y apparaît jamais**. La règle qui l'écarterait existe et est testée, mais c'est le producteur qui garantit l'exclusion, pas notre code.

## Appariement

| Classe | Diagnostics | Part |
|---|---|---|
| Bâtiment, par `id_rnb` | 136 628 | 59,04 % |
| Adresse seule, par `identifiant_ban` | 71 458 | 30,88 % |
| Non rattaché | 23 330 | 10,08 % |

**Taux d'appariement au bâtiment : 59,04 %** sur 335 communes.

Parmi les diagnostics rattachés à la seule adresse, **47 284** partagent leur adresse avec un autre diagnostic sans rattachement bâtiment, sur **9 423** adresses. Le calcul les rendra `ambiguous_match` : la cardinalité est réelle — un immeuble a plusieurs DPE légitimes — et c'est la population que D6 doit revoir à la main.

### La source se contredit sur son propre géocodage

**17 135 diagnostics** portent un `identifiant_ban` qui se résout dans notre référentiel alors que `statut_geocodage` annonce « aucune correspondance trouvée ». L'adresse est conservée — la jointure d'identifiant, elle, est vérifiable — et c'est la **confiance** qui devient absente avec le motif `contradictory_geocoding_status`. Quarantaine par attribut de BUG-03 : l'enregistrement reste, l'attribut invérifiable s'en va motivé.

### Communes aux taux extrêmes

**Les plus faibles** (communes d'au moins 100 diagnostics)

| Commune | Diagnostics | Rattachés bâtiment | Taux |
|---|---|---|---|
| SAINT-JUST (35285) | 122 | 18 | 14,75 % |
| LUITRE-DOMPIERRE (35163) | 238 | 66 | 27,73 % |
| PLESDER (35225) | 102 | 29 | 28,43 % |
| MESNIL ROC'H (35308) | 609 | 185 | 30,38 % |
| SAINT-SULPICE-DES-LANDES (35316) | 138 | 45 | 32,61 % |
| LA BAUSSAINE (35017) | 107 | 35 | 32,71 % |
| LA BAZOUGE DU DESERT (35018) | 113 | 38 | 33,63 % |
| CHANTELOUP (35054) | 153 | 53 | 34,64 % |
| SAINT-SENOUX (35312) | 179 | 65 | 36,31 % |
| SAINT-BROLADRE (35259) | 154 | 56 | 36,36 % |

**Les plus élevées** (communes d'au moins 100 diagnostics)

| Commune | Diagnostics | Rattachés bâtiment | Taux |
|---|---|---|---|
| BRECE (35039) | 353 | 283 | 80,17 % |
| ST JACQUES DE LA LANDE (35281) | 3 642 | 2 791 | 76,63 % |
| SAINT-GREGOIRE (35278) | 1 668 | 1 241 | 74,40 % |
| CINTRE (35080) | 275 | 203 | 73,82 % |
| ACIGNE (35001) | 1 148 | 846 | 73,69 % |
| L'HERMITAGE (35131) | 931 | 684 | 73,47 % |
| THORIGNE FOUILLARD (35334) | 1 150 | 839 | 72,96 % |
| BOURGBARRE (35032) | 648 | 471 | 72,69 % |
| ORGERES (35208) | 1 000 | 722 | 72,20 % |
| CHANTEPIE (35055) | 2 778 | 2 004 | 72,14 % |

## Distributions pour E1

Sur les **208 086 diagnostics conservés** — les 23 330 sans sujet ne sont dans aucune table ci-dessous, seulement en quarantaine avec leur motif.

### `REN-004` — étiquette énergétique observée

| Classe | Diagnostics | Part |
|---|---|---|
| A | 3 154 | 1,52 % |
| B | 10 562 | 5,08 % |
| C | 96 684 | 46,46 % |
| D | 59 881 | 28,78 % |
| E | 23 850 | 11,46 % |
| F | 9 408 | 4,52 % |
| G | 4 547 | 2,19 % |

### `REN-005` — consommation en énergie primaire, kWh/m²/an

| Mesure | Valeur |
|---|---|
| Observations | 208 079 |
| Q1 | 118,3 |
| Médiane | 166,4 |
| Q3 | 226,1 |

### `REN-006` — fraîcheur des diagnostics

Du 2021-07-01 au 2026-09-07, médiane au 2024-05-02. Un diagnostic ancien reste un diagnostic valide : sa fraîcheur alimente la confiance, elle n'invalide pas la valeur.

### `REN-007` — caractéristiques déclarées présentes

| Caractéristique | Diagnostics | Part |
|---|---|---|
| `ceiling_height_m` | 208 086 | 100,00 % |
| `envelope` | 208 086 | 100,00 % |
| `ubat_w_per_m2_k` | 208 086 | 100,00 % |
| `windows` | 208 086 | 100,00 % |
| `walls` | 208 037 | 99,98 % |
| `inertia` | 206 825 | 99,39 % |
| `lower_floor` | 204 052 | 98,06 % |
| `ventilation` | 196 590 | 94,48 % |
| `roof_lost_attic` | 112 588 | 54,11 % |
| `roof_converted_attic` | 37 419 | 17,98 % |
| `roof_terrace` | 31 367 | 15,07 % |

### `REN-008` — confiance d'appariement

| Provenance de la confiance | Diagnostics |
|---|---|
| identifiant officiel (1,0) | 136 628 |
| score de géocodage 0,5 à 0,8 | 38 778 |
| absente avec motif | 17 135 |
| score de géocodage < 0,5 | 10 815 |
| score de géocodage ≥ 0,8 | 4 730 |

La valeur 1,0 n'est pas un seuil choisi : c'est la convention que `meta.entity_match` porte déjà pour `rnb-ban-identifier`, un identifiant officiel déclaré par le producteur. Les autres valeurs sont le `score_ban` de la source, repris tel quel.

### `REN-001` — période de construction déclarée au diagnostic

| Période | Diagnostics |
|---|---|
| 1948-1974 | 51 645 |
| 1975-1977 | 5 914 |
| 1978-1982 | 9 856 |
| 1983-1988 | 10 864 |
| 1989-2000 | 27 915 |
| 2001-2005 | 9 413 |
| 2006-2012 | 24 211 |
| 2013-2021 | 17 894 |
| après 2021 | 6 126 |
| avant 1948 | 44 248 |

## Contrôles du contrat DS-07

| Contrôle | Résultat | Bloque la publication |
|---|---|---|
| `building_match_rate` | passed | non |
| `deposited_only` | passed | oui |
| `label_consumption_consistency` | passed | non |
| `multiple_dpe_resolution` | passed | oui |

`label_consumption_consistency` ne compare pas l'étiquette à une table de seuils : le DPE 2021 classe sur un **double seuil** énergie et GES, et reconstituer cette table ici serait inventer une interprétation que le contrat ne porte pas. Le contrôle vérifie ce qui se mesure sans seuil — que la consommation médiane croît de A vers G.

## Ce que ce rapport ne dit pas

- **`REN-001..008` ne sont pas matérialisées.** `feature.feature_value.building_id` réfère `reference.building`, donc les enregistrements RNB, alors que BUG-12 a établi que le sujet est le bâtiment physique. Les écrire aujourd'hui graverait le sujet que BUG-12 vient d'invalider — B5 a refusé la même chose pour `BLD-001..003`. Les distributions ci-dessus sont ce dont E1 a besoin ; la matérialisation attend le changement de schéma.
- **Aucune estimation d'état du bâti.** Une classe F ou G est l'observation d'un diagnostic, pas une preuve de dégradation.
- **Aucun signal tiré d'une absence.** Un bâtiment sans diagnostic n'est pas suspect : il est sans diagnostic. L'absence ne pèse sur aucune composante de score, elle ne réduit que la confiance — vérifié par test.

