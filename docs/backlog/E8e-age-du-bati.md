# E8e — L'âge du bâti pèse plus que son implantation, et il manquait au classement

**Version :** v0.6 · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/tests/test_exploratory_candidates.py, docs/data/exploratory-candidates/
**Dépend de :** E8d · **Bloque :** E9
**Demandé par :** relecture du 15 septembre 2026

## Contexte à charger

- `docs/backlog/E8d-seuils-parametrables.md`
- `docs/data/exploratory-candidates-35051.md`
- `docs/backlog/BUG-13-sujet-des-features-batiment.md`

Ne rien charger d'autre sans nécessité démontrée.

## Le constat

> « Une maison construite dans les années 50, même placée en plein milieu du terrain, peut
> intéresser plus les marchands qu'une maison bien excentrée sur le terrain mais construite il y a
> dix ans. »

Le classement de [E8c](./E8c-divisibilite-geometrique.md) ne connaît que la morphologie : rayon
inscriptible, emprise, largeur, recul. Il traite donc un pavillon de 2015 et une longère de 1950
comme équivalents à géométrie égale — alors que l'un ne se vendra pas et n'a aucun potentiel de
reprise, et que l'autre est précisément la cible.

C'est un **signal de classement manquant**, pas un critère d'élimination : un bien récent n'est pas
disqualifié, il est moins bien placé.

## La source, sa couverture et sa limite

| Source | Champ | Renseigné | Rattachable aujourd'hui |
|---|---|---:|---|
| DS-04 BD TOPO | `date_d_apparition` | 434 235 / 974 172 — **44,6 %** | oui, par `identifiants_rnb` |
| DS-03 BDNB | `ffo_bat_annee_construction` | 376 206 / 546 301 — **68,9 %** | **non**, aucun identifiant RNB |

BD TOPO est moins couvert mais **joignable sans appariement géométrique**, ce qui est la même
raison qui a fait le choix de E8b. Sa valeur est **approximative pour l'ancien** — les années se
concentrent sur 1800, 1850, 1870, 1880, 1900, signature d'une datation historique arrondie. Le
rapport doit le dire : c'est une période, pas une date d'acte.

BDNB, mieux couvert et mieux distribué — 79 937 avant 1900, 37 830 sur 1900-1949, 51 711 sur
1950-1974, 96 057 sur 1975-1999, 110 671 après 2000 — reste hors de portée tant que son
rattachement n'est pas résolu. C'est une entrée de plus pour
[BUG-13](./BUG-13-sujet-des-features-batiment.md).

## Travail à réaliser

1. Remonter l'année la plus ancienne des bâtiments de la parcelle depuis BD TOPO.
2. L'ajouter aux signaux de classement, en ordre croissant — le plus ancien devant.
3. L'afficher comme preuve par candidat.
4. Écrire dans le rapport la couverture de 44,6 %, le caractère approximatif de la datation
   ancienne, et ce que BDNB apporterait s'il était rattaché.

## Ce que ce ticket ne fait pas

- **Éliminer sur l'âge.** Un bien récent reste candidat, moins bien classé.
- **Pondérer.** Les signaux restent à poids égal, par rang moyen. Décider qu'un âge vaut deux fois
  une géométrie demanderait un profiling — c'est [E1](./E1-profiling-distributions.md), et cela ne
  se décrète pas sur une phrase.
- **Rattacher BDNB.** Cela demande un appariement géométrique bâtiment ↔ bâtiment ; c'est BUG-13.

## Tests obligatoires

- à géométrie égale, le bâti le plus ancien est mieux classé ;
- une année absente laisse l'unité classée sur les autres signaux, sans valoir zéro ni l'éliminer ;
- l'année remontée est la plus ancienne de la parcelle, pas la plus récente.

## Critères d'acceptation

- l'âge est un signal de classement, jamais un filtre ;
- la couverture et le caractère approximatif sont publiés ;
- l'apport de BDNB est chiffré et renvoyé à BUG-13 ;
- aucun seuil existant n'est modifié.

## Preuve à produire

`docs/data/exploratory-candidates-35051.md`, régénéré : année par candidat, couverture, limite de
datation.

**Relu le 16 septembre 2026 ([BUG-13](./BUG-13-sujet-des-features-batiment.md)).** BUG-13 a
donné aux features de bâtiment leur sujet, le bâtiment physique RNB. Il n'a pas rattaché BDNB au
RNB : cet appariement géométrique reste à ouvrir sous son propre ticket.
