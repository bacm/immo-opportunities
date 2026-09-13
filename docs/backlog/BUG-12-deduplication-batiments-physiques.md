# BUG-12 — Compter des enregistrements n'est pas compter des bâtiments

**Version :** v0.3 · **Taille :** M · **État :** À faire
**Dépend de :** — · **Bloque :** B5
**Découvert par :** revue manuelle B4, cas 39, 13 septembre 2026

## Contexte à charger

- `contracts/features/morphology-v1.json` (LAND-002, LAND-009)
- `pipelines/src/immo_pipelines/spatial/importer.py` (`RnbImporter._publish_stage`)
- `docs/backlog/BUG-09-recouvrement-batiment-parcelle.md`
- `docs/backlog/BUG-11-unite-fonciere-degeneree.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Les deux contrats concernés demandent explicitement des bâtiments **physiques**, **dédupliqués** :

```text
LAND-009  building_count
  count(distinct certain resolved physical buildings, after source deduplication)
LAND-002  building_footprint_m2
  area(intersection(unit geometry, union(deduplicated resolved building footprints)))
```

**Rien n'implémente cette déduplication.** Les tables portent des enregistrements source, et un
bâtiment découpé en plusieurs enregistrements compte pour plusieurs.

Le relecteur de [B4](./B4-revue-manuelle-appariements.md) l'a rencontré au cas 39 sans connaître
le modèle : ce qu'il voyait comme une maison était **trois enregistrements RNB** qui se touchent —
7,3 m², 77 m² et 16 m² — et le cas ne portait que sur le premier. Sa question, « on ne parle jamais
du bâtiment en entier ? », a exactement désigné le trou.

## Ampleur mesurée

Regroupement par contiguïté, `ST_ClusterDBSCAN` à 1 cm, département 35 entier :

| Source | Enregistrements | Bâtiments physiques | Surcomptage | Plus grand agrégat |
|---|---:|---:|---:|---:|
| **RNB** (`reference.building`) | 741 379 | **514 859** | **30,6 %** | 213 |
| **Cadastre** (`reference.active_cadastral_building`) | 865 335 | **517 615** | **40,2 %** | 104 |

Compter des enregistrements RNB au lieu de bâtiments surestime le nombre de **44 %**
— 741 379 contre 514 859.

### Les deux sources convergent, et c'est l'information importante

Deux levés indépendants, deux volumétries d'enregistrements très différentes — 741 379 et
865 335, soit 17 % d'écart — et pourtant **514 859 contre 517 615 bâtiments physiques après
regroupement : 0,5 % d'écart.**

Trois conséquences :

1. **Le fractionnement est une convention d'enregistrement, pas une réalité.** Les deux sources
   découpent, chacune à sa façon, un même bâti.
2. **Choisir le cadastre plutôt que le RNB ne règle rien** — le cadastre fractionne davantage,
   40,2 % contre 30,6 %.
3. **La contiguïté est ici un critère valable**, ce qui n'allait pas de soi : appliquée aux
   parcelles dans [BUG-11](./BUG-11-unite-fonciere-degeneree.md) elle produisait des grappes de
   3 494 parcelles et un non-sens. Appliquée aux bâtiments, elle fait converger deux sources
   indépendantes à un demi-point. C'est une validation croisée, pas une hypothèse.

## Conséquences

- **LAND-009 `building_count` est faux d'environ 44 %** s'il est calculé sur les enregistrements.
  C'est une feature de la stratégie division / extension, donc la première des deux du produit.
- **LAND-002 `building_footprint_m2` est probablement épargné** : des enregistrements mitoyens
  partagent un mur sans se recouvrir, donc l'union de leurs emprises a la même aire que leur
  somme. **À vérifier avant de conclure** — c'est une intuition géométrique, pas une mesure.
- **BLD-001..003**, définies sur un bâtiment, n'ont pas de sujet tant que « un bâtiment » n'est pas
  défini.

## Ce que ce ticket ne doit pas faire

- **Modifier les contrats.** Ils sont justes : ils demandent des bâtiments physiques depuis le
  début. C'est l'implémentation qui manque.
- **Fusionner les géométries source.** Les enregistrements restent tels quels, avec leurs
  identifiants ; la déduplication produit un regroupement, elle n'écrase pas la donnée d'origine.
- **Réutiliser le résultat pour l'unité foncière.** La contiguïté marche sur le bâti et échoue sur
  le parcellaire, c'est mesuré dans les deux sens. BUG-11 reste ouvert et distinct.

## Travail à réaliser

1. Matérialiser le regroupement par contiguïté en entité de référence, avec ses membres — le
   modèle `PropertyUnitMember` fournit le motif à imiter.
2. Vérifier la convergence commune par commune, et non seulement en volumétrie départementale :
   un écart global de 0,5 % peut masquer des compensations locales.
3. Mesurer l'effet réel sur LAND-002, au lieu de le supposer épargné.
4. Rattacher le regroupement à la parcelle par la règle de rang établie dans
   [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md), et non enregistrement par enregistrement.

## Tests obligatoires

- trois enregistrements mitoyens comptent pour un bâtiment ;
- le cas 39 — `building:rnb:P7EGXX2HZYB2` et ses deux voisins — sert de cas de référence ;
- un enregistrement isolé reste un bâtiment, et son identifiant source reste atteignable ;
- la volumétrie RNB et la volumétrie cadastrale du 35 restent à moins de 1 % l'une de l'autre.

## Critères d'acceptation

- LAND-009 compte des bâtiments physiques, et le rapport publie l'écart avec le comptage naïf ;
- l'effet sur LAND-002 est mesuré et documenté, qu'il soit nul ou non ;
- aucun identifiant source n'est perdu par le regroupement.
