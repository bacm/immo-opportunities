# DS-13 DPE logements neufs — appariement et distributions sur le 35

**Généré le :** 2026-09-16 · **Release :** `DS-13@2026-09-16-extract`
· **Publiée par la source le :** 2026-09-09
· **Run d'import :** `dpe-ds-13:2026-09-16-extract:35:1`
· **Verdict :** `display_only`

Ce fichier est **régénéré** par `make dpe-report SOURCE=DS-13`. Ne pas l'éditer à la main.

Diagnostics établis à la réception d'une construction. Affichés dans l'outil de vérification, **exclus de toute mesure** du baromètre et du radar : un DPE neuf accompagne une livraison, il n'annonce pas une vente (ADR-021).

## Volumétrie

| Étape | Enregistrements |
|---|---|
| Lignes de l'extrait | 39 072 |
| Diagnostics éligibles | 39 072 |
| Rattachés à un bâtiment | 9 310 |
| Rattachés à la seule adresse | 9 361 |
| Non rattachés | 20 401 |

### Enregistrements écartés avant appariement

Aucun. Toutes les lignes de l'extrait sont des diagnostics exploitables.

Le jeu accessible est la vue virtuelle de l'ADEME, filtrée en amont sur `dpe_desactive = 0` : **un diagnostic annulé n'y apparaît jamais**. La règle qui l'écarterait existe et est testée, mais c'est le producteur qui garantit l'exclusion, pas notre code.

## Appariement

| Classe | Diagnostics | Part |
|---|---|---|
| Bâtiment, par `id_rnb` | 9 310 | 23,83 % |
| Adresse seule, par `identifiant_ban` | 9 361 | 23,96 % |
| Non rattaché | 20 401 | 52,21 % |

**Taux d'appariement au bâtiment : 23,83 %** des diagnostics éligibles, répartis sur 317 communes déclarées par la source.

Parmi les diagnostics rattachés à la seule adresse, **7 328** partagent leur adresse avec un autre diagnostic sans rattachement bâtiment, sur **359** adresses. La cardinalité est réelle — un programme neuf dépose un DPE par logement — et aucune feature ne lit ces diagnostics (ADR-021).

### La source se contredit sur son propre géocodage

Parmi les diagnostics rattachés à la seule adresse, **5 339** portent un `identifiant_ban` qui se résout dans notre référentiel alors que `statut_geocodage` annonce « aucune correspondance trouvée ». L'adresse est conservée — la jointure d'identifiant, elle, est vérifiable — et c'est la **confiance** qui devient absente avec le motif `contradictory_geocoding_status`. Quarantaine par attribut de BUG-03 : l'enregistrement reste, l'attribut invérifiable s'en va motivé. Un diagnostic rattaché au bâtiment peut porter le même statut : sa confiance vient alors de l'identifiant RNB, pas du géocodage, et il n'est pas compté ici.

### Communes aux taux extrêmes

**Les plus faibles** (communes d'au moins 100 diagnostics)

| Commune | Diagnostics | Rattachés bâtiment | Taux |
|---|---|---|---|
| DOL DE BRETAGNE (35095) | 304 | 9 | 2,96 % |
| SAINT-COULOMB (35263) | 120 | 5 | 4,17 % |
| DOMLOUP (35099) | 137 | 6 | 4,38 % |
| SAINT-AUBIN-DU-CORMIER (35253) | 229 | 11 | 4,80 % |
| SAINT-AUBIN-D AUBIGNE (35251) | 192 | 10 | 5,21 % |
| CANCALE (35049) | 418 | 24 | 5,74 % |
| BREAL-SOUS-MONTFORT (35037) | 235 | 14 | 5,96 % |
| L'HERMITAGE (35131) | 124 | 8 | 6,45 % |
| LA MEZIERE (35177) | 102 | 7 | 6,86 % |
| ARGENTRE-DU-PLESSIS (35006) | 129 | 10 | 7,75 % |

**Les plus élevées** (communes d'au moins 100 diagnostics)

| Commune | Diagnostics | Rattachés bâtiment | Taux |
|---|---|---|---|
| NOYAL-CHATILLON-SUR-SEICHE (35206) | 540 | 366 | 67,78 % |
| VERN-SUR-SEICHE (35352) | 374 | 249 | 66,58 % |
| PONT PEAN (35363) | 179 | 99 | 55,31 % |
| CHANTEPIE (35055) | 546 | 290 | 53,11 % |
| ORGERES (35208) | 256 | 134 | 52,34 % |
| ACIGNE (35001) | 321 | 155 | 48,29 % |
| VITRE (35360) | 779 | 346 | 44,42 % |
| THORIGNE FOUILLARD (35334) | 346 | 150 | 43,35 % |
| MELESSE (35173) | 253 | 109 | 43,08 % |
| BETTON (35024) | 506 | 189 | 37,35 % |

## Distributions descriptives

Sur les **18 671 diagnostics conservés** — les 20 401 sans sujet ne sont dans aucune table ci-dessous, seulement en quarantaine avec leur motif.

### `REN-004` — étiquette énergétique observée

| Classe | Diagnostics | Part |
|---|---|---|
| A | 4 889 | 26,18 % |
| B | 5 169 | 27,68 % |
| C | 8 608 | 46,10 % |
| D | 5 | 0,03 % |

### `REN-005` — consommation en énergie primaire, kWh/m²/an

| Mesure | Valeur |
|---|---|
| Observations | 18 671 |
| Q1 | 49,1 |
| Médiane | 61,8 |
| Q3 | 76,0 |

### `REN-006` — fraîcheur des diagnostics

Date d'établissement du diagnostic : du 2021-07-02 au 2026-09-07, médiane au 2024-03-27. Un diagnostic ancien reste un diagnostic valide : sa fraîcheur alimente la confiance, elle n'invalide pas la valeur.

### `REN-007` — caractéristiques déclarées présentes

| Caractéristique | Diagnostics | Part |
|---|---|---|
| `walls` | 18 671 | 100,00 % |
| `envelope` | 18 671 | 100,00 % |
| `ceiling_height_m` | 18 671 | 100,00 % |
| `ubat_w_per_m2_k` | 18 671 | 100,00 % |
| `windows` | 18 671 | 100,00 % |
| `lower_floor` | 18 667 | 99,98 % |
| `roof_converted_attic` | 1 485 | 7,95 % |
| `inertia` | 1 035 | 5,54 % |
| `ventilation` | 1 024 | 5,48 % |

### `REN-008` — confiance d'appariement

| Provenance de la confiance | Diagnostics |
|---|---|
| identifiant officiel (1,0) | 9 310 |
| absente avec motif | 5 339 |
| score de géocodage 0,5 à 0,8 | 2 210 |
| score de géocodage ≥ 0,8 | 1 315 |
| score de géocodage < 0,5 | 497 |

La valeur 1,0 n'est pas un seuil choisi : c'est la convention que `meta.entity_match` porte déjà pour `rnb-ban-identifier`, un identifiant officiel déclaré par le producteur. Les autres valeurs sont le `score_ban` de la source, repris tel quel.

### `REN-001` — période de construction déclarée au diagnostic

| Période | Diagnostics |
|---|---|
| 2006-2012 | 42 |
| 2013-2021 | 3 948 |
| après 2021 | 14 681 |

## Contrôles du contrat DS-13

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

