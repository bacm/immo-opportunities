# Vérification manuelle des mutations DVF — département 35

**Date :** 14 septembre 2026 · **Ticket :** [D6a](../backlog/D6a-verification-mutations-parcelle.md)
**Instrument :** bloc « mutations DVF » de la fiche parcelle, Explorer

## Ce que l'instrument est, et n'est pas

Un bloc dans la fiche parcelle, replié par défaut, qui liste les mutations rattachées à la
parcelle sélectionnée. **Ce n'est pas une fonctionnalité de consultation DVF** : pas d'entrée de
menu, pas de recherche par prix, pas d'export. L'accès se fait depuis une parcelle déjà
sélectionnée, comme l'écran de revue de [B4](./spatial-matching-manual-review-35.md).

Aucun prix au m² n'est calculé à l'affichage : il n'existe pas en base, et le dériver en
fabriquerait un. Le motif de non-allocation est montré à la place — **65,5 % des mutations n'ont
aucun prix allouable**, et ce motif est l'information.

## Quatre défauts trouvés, tous en regardant la donnée

Aucun n'aurait été détecté par un contrôle automatique : tous produisaient des chiffres cohérents.

### 1. Une surface bâtie empruntée au terrain — 30 816 lots

La première parcelle ouverte affichait trois lots « Dépendance » de **382 m²**, nature de culture
« sols ». Une dépendance de 382 m² n'existe pas : la surface venait du terrain.

La règle prenait `surface_reelle_bati` puis retombait sur `surface_terrain`, confondant deux
grandeurs sans rapport. **30 816 lots bâtis** étaient concernés — 17,2 % — dont **367 portaient un
prix alloué**, donc un prix au m² faux d'un ordre de grandeur.

Corrigé en version 3 : un lot bâti sans surface bâtie garde une surface **absente**. La catégorie
« Dépendance » perd ses 295 prix, intégralement fictifs ; maisons, appartements et terrains sont
inchangés à l'unité près.

### 2. Deux versions de transformation coexistantes — 133 066 doublons

L'écran montrait quatre lignes pour deux mutations. Les versions 2 et 3 cohabitaient : j'avais
gardé la précédente « pour comparer », et la comparaison une fois faite, le doublon restait.

L'import purge désormais les versions antérieures de la même release.

### 3. Un bien décrit plusieurs fois compté comme plusieurs lots — 4 666 mutations

Deux mutations affichaient chacune « 2 lots », tous deux « Maison · 75 m² ». Vérifié dans la
source : `geo-dvf` publie **une ligne par couple bien / nature de culture du terrain**. Une maison
vendue avec un terrain en « terres » et un en « sols » apparaît deux fois, identique à
l'identique.

Sans déduplication, cette maison comptait pour deux lots chiffrables et la mutation devenait
complexe : son prix était écarté alors qu'il est parfaitement allouable.

| | v3 | v4 |
|---|---:|---:|
| Prix alloués | 45 580 | **49 820** |
| Écartées `multiple_priced_lots` | 38 920 | **34 430** |

**4 666 mutations sur 49 838** à plusieurs lignes bâties, soit 9,4 %, sont un seul bien répété.

La clé de déduplication est volontairement stricte — type, surface bâtie, nombre de pièces,
numéro de lot, parcelle. Deux appartements identiques du même immeuble ne s'y distinguent pas,
mais l'ambiguïté est alors **réelle** et non fabriquée : la source ne permet pas de trancher.

### 4. Une fiche gardant les mutations de la parcelle précédente

Signalé en revue : `35024000AP0206` affichait les deux ventes de sa voisine `AP0207` alors qu'elle
n'en porte qu'une. La base et l'API étaient justes.

La fiche est rendue à la même place d'une parcelle à l'autre : React réutilise l'instance et son
état survit au changement. Un garde « ne pas recharger si on a déjà les données » empêchait toute
nouvelle requête.

**Un écran de vérification qui attribue une vente à la mauvaise parcelle est pire qu'un écran
absent** : il fait douter d'une donnée juste, ou pire, il fait croire à une donnée fausse. Un test
de navigation le verrouille désormais.

## État après correction

| | |
|---|---:|
| Mutations | 133 066 |
| Lots | 337 019 |
| **Prix alloués** | **49 820 — 37,4 %** |
| Rattachement au cadastre | 97,49 % |

## Ce que cette vérification ne prouve pas

- **Elle ne valide pas la sélection de comparables.** Les comparables retenus sont-ils pertinents,
  les exclus l'ont-ils été à juste titre : c'est [D6](../backlog/D6-revue-manuelle-metier.md), qui
  suppose des segments de marché renvoyés à [E1](../backlog/E1-profiling-distributions.md).
- **Elle n'est pas stratifiée.** Contrairement à B4, aucun échantillon n'a été tiré ni de taille
  justifiée avant examen : les parcelles ont été ouvertes au fil de la vérification. Le résultat
  se lit comme « quatre défauts trouvés », jamais comme « un taux d'erreur mesuré ».
- **Elle ne dit rien des 2,5 % de lots non rattachés**, dont la cause — dérive de numérotation
  parcellaire — est établie dans [`dvf-quality-35.md`](./dvf-quality-35.md).

## Ce qu'elle confirme sur la méthode

Le ticket annonçait que l'erreur d'allocation avait été trouvée « en relisant des distributions,
tard », et qu'un écran montrant les mutations d'une parcelle l'aurait rendue évidente au premier
regard.

L'écran a trouvé son premier défaut **avant d'avoir une interface**, sur la première requête de
l'API. Les trois autres ont suivi en quelques minutes d'usage.

C'est le même constat que B4, où trois défauts structurels ont été trouvés parce qu'un humain
regardait une carte : **un contrôle automatique ne détecte pas une absence cohérente.**
