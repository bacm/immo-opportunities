# E8d — Supprimer le plancher de surface et exposer les seuils, à commencer par la largeur du lot

**Version :** v0.6 · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/tests/test_exploratory_candidates.py, docs/data/exploratory-candidates/, Makefile
**Dépend de :** E8c · **Bloque :** E9
**Demandé par :** arbitrage du 15 septembre 2026

## Contexte à charger

- `docs/backlog/E8c-divisibilite-geometrique.md`
- `docs/data/exploratory-candidates-35051.md`

Ne rien charger d'autre sans nécessité démontrée.

## Le plancher de surface faisait doublon, et coûtait cher

`min_parcel_area_m2 = 800` était un **proxy grossier** de la divisibilité, posé quand rien ne la
mesurait. Depuis [E8c](./E8c-divisibilite-geometrique.md), le rayon inscriptible dans la partie
libre la mesure directement. Deux critères pour une même question, dont l'un ne vérifie rien.

Mesuré sur le 35051, parmi les unités qui satisfont **tous** les autres critères :

| Tranche | Éligibles | Lot inscriptible ≥ 6 m | Taux | Rayon max |
|---|---:|---:|---:|---:|
| 400–600 m² | 549 | 86 | 15,7 % | 8,6 m |
| 600–800 m² | 528 | 262 | 49,6 % | 10,4 m |

**348 parcelles divisibles étaient écartées** par le plancher, pour un vivier retenu de 357. Il
coupait donc près de la moitié du gisement sans rien vérifier.

## Ce que l'arbitrage a tranché

- **Le plancher est supprimé.** Un seul critère décide désormais : le lot est-il inscriptible ?
- **La largeur du lot reste à 12 m**, et devient **un paramètre exposé** — c'est le seul seuil qui
  porte un sens métier, et il n'appartient pas au code de le fixer en dur.
- Le plafond de surface est conservé et exposé lui aussi. Il écarte encore 16 unités sur 1 484,
  dont un bâtiment résidentiel sur 133 012 m².

## La remarque métier qui accompagne l'arbitrage, et où elle mène

> « En dessous de 12 m ça devient compliqué, sauf s'il est possible de construire en limite de
> propriété — et c'est là où ça devient complexe. »

Le retrait par rapport aux limites séparatives est une **règle du règlement du PLU**, pas une
propriété du terrain. La lire suppose les profils de règles de
[D2b](./D2b-profils-de-regles.md), non livrés — et `SPEC.md` interdit d'interpréter un règlement
sans eux. La largeur de 12 m est donc une hypothèse de travail qui vaut **tant qu'on suppose un
retrait obligatoire**, et le rapport doit le dire plutôt que la présenter comme une contrainte
physique.

C'est aussi un argument concret pour D2b, jusqu'ici motivé de façon abstraite.

## Travail à réaliser

1. Supprimer le plancher de surface et son étape d'entonnoir.
2. Remplacer `min_free_radius_m` par `min_lot_width_m`, de sens métier, le rayon exigé en étant la
   moitié.
3. Exposer les paramètres en options de ligne de commande, et la largeur du lot dans la cible
   `make`.
4. Publier dans le rapport la répartition du vivier par tranche de surface — ce que la suppression
   du plancher fait entrer doit être visible.
5. Écrire dans le rapport que 12 m suppose un retrait obligatoire, et renvoyer à D2b.

## Tests obligatoires

- aucune étape d'entonnoir ne porte sur un plancher de surface ;
- `--lot-width 15` exige bien un rayon de 7,5 m ;
- un paramètre non fourni conserve la valeur par défaut déclarée ;
- la répartition par tranche de surface couvre tout le vivier, sans trou ni recouvrement.

## Critères d'acceptation

- le plancher est supprimé, l'effet sur le vivier du 35051 est publié ;
- la largeur du lot est paramétrable depuis `make` et vaut 12 m par défaut ;
- l'hypothèse de retrait obligatoire est écrite, avec le renvoi à D2b ;
- aucun autre seuil de E8 n'est modifié à cette occasion.

## Preuve à produire

`docs/data/exploratory-candidates-35051.md`, régénéré : entonnoir sans plancher, paramètres
effectifs, répartition par tranche de surface, hypothèse de retrait.
