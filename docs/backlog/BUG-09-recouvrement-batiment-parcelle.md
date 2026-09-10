# BUG-09 — Un tiers des relations bâtiment ↔ parcelle sont des contacts marginaux déclarés certains

**Version :** v0.3 · **Taille :** M · **État :** À faire
**Dépend de :** — · **Bloque :** B5, et toute feature comptant des bâtiments par parcelle
**Découvert par :** revue manuelle B4, cas 47 puis cas 3, 10 septembre 2026

## Contexte à charger

- `pipelines/src/immo_pipelines/spatial/importer.py` (`RnbImporter._publish_stage`, bloc
  `rnb-plot-relation`)
- `docs/data/spatial-matching-distribution-35.md` (cardinalité)
- `contracts/features/morphology-v1.json` (LAND-002, LAND-009)

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Le relecteur de [B4](./B4-revue-manuelle-appariements.md), en regardant la carte du cas 47, a
signalé que « les bâtiments n'étaient pas indiqués sur la bonne parcelle ».

Le bâtiment `building:rnb:QWC7KJ2SBC4D`, 213 m², chevauche **quatre** parcelles :

| Parcelle | Part du bâtiment | Relation enregistrée |
|---|---:|---|
| `35285000ZH0409` | 49 % | `certain` |
| `35285000ZH0374` | 44 % | `certain` |
| `35285000ZH0372` | **3 %** | `certain` |
| `35285000ZH0401` | **3 %** | `certain` |

Les deux dernières sont des échardes de 7 m² : le cadastre et le RNB ne s'alignent pas au
centimètre, et le bâtiment déborde de quelques décimètres sur les parcelles voisines.

Le même relecteur l'a revu au cas 3, sur un exemple plus net encore — deux parcelles
seulement, des parts sans ambiguïté :

| Parcelle | Part du bâtiment | Surface parcelle | Décision | Confiance |
|---|---:|---:|---|---:|
| `350930000L0434` | 84,5 % | 308 m² | `certain` | **0,90** |
| `350930000L0435` | 11,1 % | 163 m² | `certain` | **0,90** |
| hors parcelle | 4,4 % | — | — | — |

Même décision et même confiance pour un rapport de 1 à 8 sur le recouvrement. Un bâtiment de
91 m² est déclaré posé avec la même assurance sur une parcelle qui en porte 77 m² et sur une
autre qui en porte 10.

Le cas 3 ne portait pas sur les parcelles — il demandait si un bâtiment BD TOPO et un bâtiment
RNB étaient le même bâtiment, ce qu'ils sont, au centimètre. Le défaut n'a été visible que
parce que le fond de carte affiche le parcellaire. C'est la deuxième fois qu'il est repéré par
accident, ce qui dit surtout qu'il **manque une strate de revue pour cette relation** : les
relations bâtiment ↔ parcelle ne sont pas échantillonnées en tant que telles par B4.

## Ampleur mesurée

Sur les **1 240 355** relations bâtiment ↔ parcelle du 35, toutes `certain` :

| Recouvrement | Relations | Part |
|---|---:|---:|
| 0,0 à 0,1 | **400 706** | **32,3 %** |
| 0,1 à 0,5 | 107 541 | 8,7 % |
| 0,5 à 0,9 | 102 920 | 8,3 % |
| 0,9 à 1,0 | 616 988 | 49,8 % |

273 123 relations — 22 % — sont sous **2 %** de recouvrement. 353 999 bâtiments sont rattachés
à plus d'une parcelle.

**La distribution est nettement bimodale** : un pic sous 0,1 et un pic au-dessus de 0,9, avec un
creux entre les deux. Deux phénomènes distincts se cachent donc sous une même décision — un
bâtiment réellement posé sur sa parcelle, et un contact géométrique entre deux référentiels qui
ne s'alignent pas.

### Le chevauchement vient du croisement de deux levés, pas du RNB seul

Un bâtiment cadastral et une parcelle cadastrale sont issus du **même levé** : leurs limites
sont dessinées ensemble et coïncident par construction. Un bâtiment RNB est un levé
indépendant. Comparer les deux mesure donc la part du chevauchement qui tient à la méthode
plutôt qu'au terrain.

Part des bâtiments qui enjambent une limite de parcelle, département 35 entier, selon la
surface minimale comptée sur la seconde parcelle :

| Source | Bâtiments | > 0 m² | > 0,5 m² | > 5 m² |
|---|---:|---:|---:|---:|
| RNB (`reference.building`) | 737 088 | **47,3 %** | 30,6 % | 18,1 % |
| Cadastre (`reference.active_cadastral_building`) | 864 703 | **7,2 %** | 4,5 % | 3,5 % |

Deux lectures, toutes deux vraies :

- **Le cadastre chevauche aussi.** 7,2 % de ses bâtiments enjambent une limite, et 3,5 % le
  font de plus de 5 m². Un bâtiment à cheval sur deux parcelles est une réalité foncière
  courante — mitoyenneté, dépendance sur la parcelle voisine, bâti antérieur au découpage. Il
  ne faut donc pas traiter tout chevauchement comme une erreur.
- **Mais le RNB chevauche 6,6 fois plus.** L'écart entre 47,3 % et 7,2 % ne décrit aucune
  réalité foncière : il décrit l'imprécision entre deux levés. À la louche, sur les 47,3 %,
  environ 7 points sont du bâti réellement à cheval et 40 points sont du désalignement.

L'écart se resserre quand on relève le seuil — de 6,6 à 5,2 entre « toute intersection » et
« plus de 5 m² » — ce qui confirme que le gros du surplus RNB est fait de contacts marginaux.

## Cause

Dans `RnbImporter._publish_stage` :

```sql
greatest(0.9, least(1, coalesce((plot->>'bdg_cover_ratio')::numeric, 0.9))),
'certain', true, false,
```

Le `greatest(0.9, …)` **plancherise la confiance à 0,9 quel que soit le recouvrement**, et
`'certain'` est écrit en dur. Un contact à 3 % ressort donc avec la même confiance qu'un
bâtiment entièrement sur sa parcelle, et avec la même décision.

Le taux de recouvrement est pourtant conservé dans
`reference.building_parcel.building_overlap_ratio` : l'information existe, elle n'est simplement
pas utilisée pour décider.

## Conséquences

- **`LAND-002 building_footprint_m2` et `LAND-009 building_count`** compteraient des bâtiments
  qui ne sont pas sur la parcelle. Une parcelle hériterait de l'emprise de ses voisins, et le
  score de division / extension s'en trouverait faussé — c'est la première des deux stratégies
  du produit.
- **La cardinalité rapportée par [B3](./B3-rapport-appariements.md)** — maximum 37 parcelles pour
  un bâtiment, moyenne 1,682 — ne décrit pas la réalité foncière mais l'imprécision entre deux
  sources. Le rapport devra le dire.
- **La quatrième classe est vide pour cette relation** : 0 ambigu, 0 rejeté sur 1,24 M. Une
  distribution sans aucun cas incertain aurait dû alerter plus tôt.

## La question de fond : quelle géométrie fait foi pour compter par parcelle

Le plancher de confiance est le défaut de code, et il se corrige en une ligne. Mais il masque
une décision d'architecture qui n'a jamais été prise explicitement : **avec quelle géométrie de
bâtiment calcule-t-on une métrique rapportée à la parcelle ?**

- La géométrie **cadastrale** est cohérente avec le parcellaire par construction. C'est la
  seule qui permette de dire « ce bâtiment est sur cette parcelle » sans arbitrer un
  recouvrement. Elle n'a pas d'identifiant national stable.
- La géométrie **RNB** porte l'identifiant national et sert de pivot d'appariement entre
  sources. Elle n'est pas cohérente avec le parcellaire, et ne peut pas le devenir.

La conclusion qui se dégage, à confirmer par [E1](./E1-profiling-distributions.md) : le RNB
reste le pivot d'identité, et **LAND-002 / LAND-009 se calculent sur la géométrie cadastrale**.
Ce n'est pas une préférence de source, c'est la seule combinaison qui ne demande pas de seuil
inventé.

## Ce que ce ticket ne doit pas faire

**Choisir un seuil.** Aucun seuil observé ne dit à partir de quel recouvrement un bâtiment est
« sur » une parcelle, et en inventer un est explicitement interdit. La bimodalité de la
distribution suggère qu'un seuil existe et qu'il est mesurable — c'est à
[E1](./E1-profiling-distributions.md) de le trancher, pas à ce ticket.

## Travail à réaliser

1. Cesser de plancheriser la confiance à 0,9 : reporter le recouvrement observé tel quel.
2. Cesser d'écrire `certain` en dur. En attendant un seuil calibré, la décision juste est
   `ambiguous` avec le recouvrement en preuve — c'est le traitement déjà appliqué à DS-04 pour
   la même raison, et il est cohérent.
3. Publier la distribution des recouvrements comme entrée du profiling de E1.
4. Corriger la lecture de la cardinalité dans le rapport B3.
5. Trancher, avec E1, la géométrie de référence de LAND-002 et LAND-009, et l'écrire dans
   `contracts/features/morphology-v1.json`.
6. Ouvrir une strate de revue pour la relation bâtiment ↔ parcelle : elle n'est pas
   échantillonnée par B4 et n'a été vue que par accident, deux fois.

## Tests obligatoires

- une relation à faible recouvrement n'est pas `certain` sans seuil calibré ;
- le recouvrement observé est reporté sans plancher ;
- la distribution en quatre classes de cette relation cesse d'être dégénérée.

## Critères d'acceptation

- aucune relation bâtiment ↔ parcelle n'est déclarée certaine sur la seule foi d'un contact ;
- la distribution des recouvrements est publiée et disponible pour E1 ;
- les conséquences sur LAND-002 et LAND-009 sont documentées.

## Ce que la revue manuelle a prouvé au passage

Ce défaut était invisible depuis les contrôles automatiques : ils vérifient que les quatre
classes somment au total, que les motifs sont présents, que les métriques se recalculent. Une
relation fausse mais cohérente les traverse sans bruit.

Il a fallu qu'un humain regarde une carte pour le voir. C'est exactement ce que
[B4](./B4-revue-manuelle-appariements.md) existe pour produire — et il l'a produit au
quarante-septième cas, sur une question qui ne portait même pas sur les parcelles.
