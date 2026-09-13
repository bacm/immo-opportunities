# Regroupement des enregistrements en bâtiments physiques — département 35

**Date :** 13 septembre 2026 · **Ticket :** [BUG-12](../backlog/BUG-12-deduplication-batiments-physiques.md)
**Méthode :** contiguïté, `ST_ClusterDBSCAN`, ε = 1 cm, par commune · **Version :** `1`

## Pourquoi ce regroupement existe

Les contrats le demandaient depuis le début, et rien ne l'implémentait :

```text
LAND-009  count(distinct certain resolved physical buildings, after source deduplication)
LAND-002  area(intersection(unit geometry, union(deduplicated resolved building footprints)))
```

Le défaut a été rencontré en revue manuelle, au cas 39 : ce que le relecteur voyait comme une
maison était **trois enregistrements RNB contigus** — 7,3 m², 77 m² et 16 m² — et le cas ne portait
que sur le premier. Sa question, « on ne parle jamais du bâtiment en entier ? », désignait
exactement le trou.

## Volumétrie

| Source | Enregistrements | Bâtiments physiques | Surcomptage évité | Plus grand agrégat |
|---|---:|---:|---:|---:|
| RNB | 741 379 | **514 859** | 30,6 % | 213 |
| Cadastre | 865 335 | **517 615** | 40,2 % | 104 |

Compter des enregistrements RNB au lieu de bâtiments **surestime de 44 %**.

## Validation : deux levés indépendants convergent

Le critère de contiguïté n'est pas postulé, il est recoupé. RNB et cadastre sont deux levés
indépendants, qui diffèrent de **17 %** en nombre d'enregistrements. Après regroupement :

| | Bâtiments physiques |
|---|---:|
| RNB | 514 859 |
| Cadastre | 517 615 |
| **Écart** | **0,5 %** |

### La convergence tient aussi commune par commune

Un écart global de 0,5 % pourrait masquer des compensations locales. Sur les **332 communes** où
les deux sources sont présentes :

| | Communes | Part |
|---|---:|---:|
| Écart ≤ 5 % | 280 | **84,3 %** |
| Écart ≤ 10 % | 327 | **98,5 %** |
| Écart > 20 % | **0** | 0 % |

Écart médian **2,33 %**, maximum **17,4 %**. Aucune compensation locale ne se cache derrière le
chiffre départemental.

## Effet sur les features

### LAND-009 `building_count` — faux de 44 % sans regroupement

C'est la raison d'être du ticket. Une feature de la stratégie division / extension, donc la
première des deux du produit.

### LAND-002 `building_footprint_m2` — épargné, et c'est mesuré

L'intuition disait que des mitoyens partagent un mur sans se recouvrir, donc que l'union de leurs
emprises a la même aire que leur somme. Une intuition géométrique n'est pas une mesure, et le
ticket exigeait de la vérifier.

Sur **20 000 groupes multi-membres** RNB tirés au hasard :

| | Valeur |
|---|---:|
| Groupes dont l'aire est inchangée à 0,5 m² près | **19 866 — 99,33 %** |
| Aire totale perdue par l'union | **0,009 %** |
| Plus grand recouvrement sur un groupe | 294,1 m² |

**LAND-002 est donc insensible au regroupement**, à neuf millièmes de pour cent près. Les 0,67 %
de groupes qui perdent de l'aire recouvrent réellement — un recouvrement de 294 m² évoque un
doublon dans la source plutôt qu'une mitoyenneté, et mérite d'être regardé à part.

## Ce que ce regroupement ne fait pas

- **Il ne modifie aucune donnée source.** Les enregistrements RNB et cadastraux restent tels qu'ils
  ont été importés ; chaque identifiant reste atteignable par
  `reference.physical_building_member`. Un test échoue si le script écrit dans une table source.
- **Il ne réconcilie pas les deux sources entre elles.** Chaque source est regroupée séparément.
  Savoir quel bâtiment RNB correspond à quel bâtiment cadastral est un autre problème — c'est
  l'appariement d'identité, accepté par [B4](./spatial-matching-manual-review-35.md) sur la paire
  BD TOPO ↔ RNB.
- **Il ne rattache pas les groupes aux parcelles.** La règle de rang établie par
  [BUG-09](../backlog/BUG-09-recouvrement-batiment-parcelle.md) s'applique aujourd'hui
  enregistrement par enregistrement ; la porter au niveau du groupe relève du calcul des features,
  donc de [B5](../backlog/B5-features-morphologiques.md).

## Le seuil de 1 cm

C'est le seul paramètre. Deux enregistrements qui partagent un mur ne sont jamais séparés par plus
que le bruit de numérisation ; élargir souderait des bâtiments voisins réellement distincts.

Ce n'est pas un seuil territorial au sens de la règle non négociable : il ne dépend d'aucun profil
de commune, et sa validation n'est pas une distribution observée mais le recoupement de deux levés
indépendants.

## Contraste utile avec l'unité foncière

La même méthode appliquée au **parcellaire** échoue complètement —
[BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md) mesure des grappes moyennes de 37 parcelles
et jusqu'à 3 494, soit un quartier entier devenu une seule « unité ».

Ce n'est donc pas la contiguïté qui est bonne ou mauvaise en soi : **le bâti a des discontinuités
naturelles, le parcellaire n'en a pas.** Les deux mesures se répondent et méritent d'être lues
ensemble.

## Reproduire

```bash
make physical-buildings SOURCE=rnb DEPARTMENT=35
make physical-buildings SOURCE=cadastre DEPARTMENT=35
```

Idempotent : la version de regroupement entre dans l'identifiant du groupe et dans la clause de
purge, de sorte qu'un changement de méthode ne peut pas se confondre avec l'existant.
