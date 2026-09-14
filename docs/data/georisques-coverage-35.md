# DS-09 Géorisques — couverture par famille sur le 35

**Généré le :** 2026-09-14

Ce fichier est **régénéré** par `make georisques-report`. Ne pas l'éditer à la main.

L'inventaire de la source, écrit avant le premier lot, est dans [`georisques-source-inventory-35.md`](./georisques-source-inventory-35.md).

## Une release par famille

Elles n'ont ni la même granularité, ni la même fraîcheur, ni le même producteur. Une release unique « Géorisques » aurait masqué ces différences et rendu impossible un verdict famille par famille.

| Famille | Accès | Granularité | Observations | dont fines | Communes | Verdict |
|---|---|---|---:|---:|---:|---|
| Cavités souterraines | `department` | `point` | 179 | 179 | 32 | `pending` |
| Exposition au retrait-gonflement des argiles | `download` | `zone` | 1 428 | 1 428 | 332 | `pending` |
| Atlas des zones inondables | `commune` | `commune` | 273 | 0 | 225 | `pending` |
| Risques recensés GASPAR | `commune` | `commune` | 1 730 | 0 | 332 | `pending` |
| Installations classées | `department` | `point` | 3 588 | 3 588 | 321 | `pending` |
| Mouvements de terrain | `department` | `point` | 372 | 372 | 49 | `pending` |
| Arrêtés de catastrophe naturelle | `commune` | `commune` | 1 485 | 0 | 331 | `pending` |
| Potentiel radon | `commune` | `commune` | 332 | 0 | 332 | `pending` |
| Sites et sols pollués | `department` | `zone` | 189 | 170 | 133 | `pending` |
| Servitudes d'utilité publique | `download` | `zone` | 1 248 | 1 248 | 256 | `pending` |

**10 824 observations**, dont **6 985** à granularité fine — point ou zone. Les autres sont communales et le restent.

## Couverture : interrogée, et ce qu'on y a trouvé

Une commune interrogée sans observation est une **couverture connue à zéro**. Une commune absente de la table n'a pas été interrogée. Le contrat DS-09 appelle cette distinction `coverage_absence`, et c'est elle qui empêche de lire une absence d'information comme une absence de risque.

| Famille | Communes interrogées | dont sans observation | Observation la plus fraîche |
|---|---:|---:|---|
| Cavités souterraines | 332 | 302 | — |
| Exposition au retrait-gonflement des argiles | 332 | 0 | — |
| Atlas des zones inondables | 332 | 107 | 1995-01-01 |
| Risques recensés GASPAR | 332 | 0 | — |
| Installations classées | 332 | 11 | 2026-09-12 |
| Mouvements de terrain | 332 | 283 | 2018-06-10 |
| Arrêtés de catastrophe naturelle | 332 | 1 | 2026-05-08 |
| Potentiel radon | 332 | 0 | — |
| Sites et sols pollués | 332 | 204 | 2025-03-10 |
| Servitudes d'utilité publique | 332 | 76 | — |

## Types de risque observés, et à quelle granularité

Le type vient de la source. Les libellés français sont ceux que GASPAR publie et que nous n'avons pas rattachés à un type canonique : les recoder au jugé serait inventer une interprétation.

| Type | Granularité | Observations | Communes |
|---|---|---:|---:|
| `industrial_installation` | `point` | 3 588 | 321 |
| `natural_disaster` | `commune` | 1 485 | 331 |
| `clay` | `zone` | 1 428 | 332 |
| `sup_AC1` | `zone` | 964 | 208 |
| `flood` | `commune` | 395 | 254 |
| `landslide` | `point` | 372 | 49 |
| `Phénomène lié à l'atmosphère` | `commune` | 332 | 332 |
| `earthquake` | `commune` | 332 | 332 |
| `Tempête et grains (vent)` | `commune` | 332 | 332 |
| `radon` | `commune` | 332 | 332 |
| `Transport de marchandises dangereuses` | `commune` | 225 | 225 |
| `cavity` | `point` | 179 | 32 |
| `soil_pollution` | `zone` | 170 | 130 |
| `sup_PM1` | `zone` | 147 | 130 |
| `sup_T1` | `zone` | 100 | 100 |
| `Par une crue à débordement lent de cours d'eau` | `commune` | 96 | 96 |
| `landslide` | `commune` | 85 | 85 |
| `Tassements différentiels` | `commune` | 76 | 76 |
| `Feu de forêt` | `commune` | 47 | 47 |
| `sup_AC4` | `zone` | 32 | 30 |
| `Rupture de barrage` | `commune` | 26 | 26 |
| `Par submersion marine` | `commune` | 25 | 25 |
| `soil_pollution` | `commune` | 19 | 12 |
| `Risque industriel` | `commune` | 6 | 6 |
| `Affaissements et effondrements d'origine anthropique (anciennes carrières souterraines, hors mines)` | `commune` | 6 | 6 |
| `Effet thermique` | `commune` | 6 | 6 |
| `sup_PM3` | `zone` | 5 | 5 |
| `Eboulement ou chutes de pierres et de blocs` | `commune` | 4 | 4 |
| `Effet de surpression` | `commune` | 4 | 4 |
| `Effet toxique` | `commune` | 3 | 3 |
| `Glissement de terrain` | `commune` | 1 | 1 |
| `Recul du trait de côte et de falaises` | `commune` | 1 | 1 |
| `Par une crue torrentielle ou à montée rapide de cours d'eau` | `commune` | 1 | 1 |

## Ce que ces données permettent, et ce qu'elles ne permettent pas

| Feature | Fondée sur | État |
|---|---|---|
| `RISK-001` exposition argiles | `clay`, zones | **calculable** |
| `RISK-003` sites pollués | `soil-pollution`, zones | **calculable** |
| `RISK-004` cavités | `cavity`, points | **calculable** |
| `RISK-101` contraintes applicables | toutes | **calculable** |
| `RISK-002` zones inondables | — | **absente avec motif** |

### `RISK-002` reste absente, et ce n'est pas un défaut d'import

Aucune source disponible sur le 35 ne donne une zone inondable **typée**. GASPAR et l'atlas des zones inondables disent qu'une commune est concernée — c'est communal, et « la commune est concernée par un PPRI » n'est pas « la parcelle est en zone inondable ».

La servitude `PM1` donne bien des géométries de zone, et c'est le seul zonage opposable du département. Mais elle porte les **risques naturels prévisibles** sans dire lequel : son assiette est une « enveloppe des zonages réglementaires ». En déduire « inondation » serait la faute que D2 a commise sur le champ `ETAT` du CNIG — interpréter de mémoire un code que le contrat ne documente pas.

Rattacher chaque assiette `PM1` à son aléa demande la table de correspondance du producteur. Tant qu'elle n'est pas sourcée, `RISK-002` sort `source_value_missing` et les périmètres restent visibles dans `RISK-101` sous `sup_PM1`.

### Quatre servitudes que le producteur refuse

Le Géoportail de l'urbanisme répond `403 Forbidden` au téléchargement de quatre des neuf servitudes du 35, et le refait aux trois tentatives. Ce n'est donc pas un échec passager — un cinquième document, `T1`, a échoué une fois puis répondu, ce qui rend la distinction mesurable et non supposée.

| Document | Catégorie | Ce qui manque |
|---|---|---|
| `120068051_SUP_35_I1` | I1 | assiettes non téléchargeables |
| `120064019_SUP_35_T5` | T5 | assiettes non téléchargeables |
| `120064019_SUP_35_PT1` | PT1 | assiettes non téléchargeables |
| `120064019_SUP_35_PT2` | PT2 | assiettes non téléchargeables |

La couverture des servitudes est donc **partielle et le manifeste le dit**. Les catégories manquantes — canalisations, aéronautique, télécoms — ne pèsent pas sur les features RISK, qui ne les consultent pas.

