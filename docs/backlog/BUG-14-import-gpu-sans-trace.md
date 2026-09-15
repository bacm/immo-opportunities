# BUG-14 — Deux imports métier ne laissent aucune trace, et le calcul URB ne vérifie aucun verdict

**Version :** v0.5 · **Taille :** M · **État :** Terminé
**Dépend de :** — · **Bloque :** E1
**Touche :** pipelines/scripts/import_gpu_release.py, pipelines/scripts/import_dvf_release.py, pipelines/scripts/compute_urban_features.py
**Découvert par :** [D5](./D5-rapports-qualite-metier.md), 15 septembre 2026

## Contexte à charger

- `pipelines/scripts/import_gpu_release.py`
- `pipelines/scripts/compute_urban_features.py` (les deux emplois de `source_not_accepted`)
- `pipelines/src/immo_pipelines/cadastre/catalog.py` (`set_acceptance`, `_require_successful_import`)

Ne rien charger d'autre sans nécessité démontrée.

## Quatre défauts, une seule cause

[D2](./D2-import-gpu-ds08.md) a importé 184 documents et 11 305 zones, et produit un rapport de
couverture sérieux. Mais son import **n'écrit aucune ligne dans `meta.import_run`**, là où DS-01,
DS-02, DS-03, DS-04, DS-05, DS-07 et DS-09 en écrivent une, avec clé d'idempotence portant la
version de transformation.

**`import_dvf_release.py` a le même défaut**, relevé par [D5](./D5-rapports-qualite-metier.md) en
comptant les runs par source : `DS-06@2026-09-13` porte `display_only` **sans qu'aucun run
d'import ne l'appuie**. Le verdict a donc été prononcé par un chemin qui contourne
`_require_successful_import`, et rien en base ne relie aujourd'hui les 133 066 transactions à un
import identifié, daté et rejouable.

Les conséquences s'enchaînent :

1. **`DS-08@2026-09-14` ne peut pas recevoir de verdict.** `set_acceptance` appelle
   `_require_successful_import`, qui refuse : « Release requires at least one successful import
   run ». La garde est correcte — une release sans import traçable ne doit pas être publiable.
   La release est donc restée `pending` depuis le 14 septembre.
2. **L'import n'est pas relançable de façon contrôlée.** Sans clé d'idempotence, rien ne dit si
   une relance rejouerait à vide ou dupliquerait, et un correctif de code n'a aucun moyen
   déclaré d'atteindre les données — c'est la leçon de [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md),
   non appliquée ici.
3. **`compute_urban_features` ne vérifie aucun verdict.** Il prend `--release` et calcule, quel
   que soit l'`acceptance_status`. **554 714 valeurs `URB-001` sont en base alors que leur source
   est `pending`**, ce que la règle du projet interdit : une source sans verdict `accepted`
   produit des features absentes avec le motif `source_not_accepted`.

## Et un motif d'absence qui en dit un autre

Dans le même script, `source_not_accepted` est employé pour signifier **« aucune zone opposable ne
couvre cette parcelle »** — le RNU, ou une commune sans document. Ce n'est pas la même chose que
« la source n'est pas acceptée », et les conséquences sur le scoring diffèrent :

| Situation | Motif correct | Ce que E1 doit en faire |
|---|---|---|
| Release non acceptée | `source_not_accepted` | ignorer la source entière |
| Parcelle hors de tout document | `source_value_missing` | mesurer la couverture réelle |

Aujourd'hui les deux sortent sous le même code. **776 499 absences `URB-001`** signifient « hors
document » et se lisent « DS-08 inutilisable ». [D5](./D5-rapports-qualite-metier.md) pose que
confondre les motifs d'absence rend E1 impossible à conduire correctement ; c'en est le cas
d'espèce.

## Travail à réaliser

1. `import_gpu_release.py` **et** `import_dvf_release.py` écrivent un `meta.import_run` :
   identifiant et clé d'idempotence portant la version de transformation, comptes source /
   normalisés / quarantaine, statut final.
2. Réimporter DS-08 et DS-06 sur le 35, puis prononcer ou reprononcer leur verdict.
3. `compute_urban_features.py` refuse de calculer sur une release sans verdict `accepted` ou
   `display_only`, et émet alors `source_not_accepted` sur toutes ses features — sans exception.
4. Séparer les deux motifs : « hors document » devient `source_value_missing`.
5. Recalculer les features URB.

## Tests obligatoires

- une release `pending` fait sortir toutes les features URB en `source_not_accepted` ;
- une parcelle hors de tout document sur une release acceptée sort en `source_value_missing` ;
- un réimport GPU ou DVF de la même version est stable et ne duplique pas ;
- aucun verdict ne peut être prononcé sur une release sans run d'import réussi ;
- la somme des valeurs présentes et des absences par motif égale le volume total.

## Critères d'acceptation

- `DS-08@2026-09-14` porte un verdict motivé ;
- aucune feature calculée ne s'appuie sur une release sans verdict ;
- les deux motifs d'absence sont distincts en base ;
- [D5](./D5-rapports-qualite-metier.md) peut publier une ventilation des motifs qui veut dire
  quelque chose.

## Clôture — 15 septembre 2026

**Le code est arrivé par le mauvais commit.** Les trois scripts déclarés dans `Touche` ont été
modifiés dans `6aa78b4`, intitulé « A1 — La CI a tourné… ». Le correctif est sur `main` depuis ce
commit ; seul le commit de clôture porte l'identifiant BUG-14. `make dod` ne voit donc que la
seconde moitié du diff — les tests, le rapport et ce fichier.

Ce que la réimportation a établi :

- DS-08 était **à moitié peuplée** : 11 305 zones en base pour 21 136 annoncées par le rapport
  de [D2](./D2-import-gpu-ds08.md) — le manifeste de la release ne porte aucun compte de zones,
  contrairement à ce qu'une première version du rapport affirmait. Après réimport tracé :
  21 136 zones, 300 communes, run `gpu:2026-09-14:35:1` réussi.
- DS-06 porte deux runs réussis, un par release, l'archive 2014-2020 de [D8](./D8-historique-dvf-2014.md)
  comprise.
- `URB-001` passe de 554 714 à 1 209 188 valeurs présentes ; les 776 499 « `source_not_accepted` »
  se répartissent en 122 026 `source_value_missing` réels et 2 113 `ambiguous_match`.
- `DS-08@2026-09-14` porte `display_only`, et le motif est écrit dans `notes` de la release, à la
  manière de DS-06. Aucun chemin de code n'écrit ce champ : c'est un manque à porter dans D6.

**Recompte indépendant** du rapport régénéré, depuis la base et sans lire le script : tous les
chiffres du tableau des verdicts, de DS-08, des ventilations URB et des communes les moins
calculables sont confirmés. Le recompte a relevé deux écarts, corrigés avant clôture : le rapport
avait été généré avant l'import de l'archive DVF, et la phrase de traçabilité attribuait au
manifeste un chiffre qu'il ne contient pas. Cette phrase est désormais dérivée du tableau et ne
porte plus de volumétrie en dur.

**Dépendances relues :** aucun ticket ne déclare dépendre de BUG-14 ; E1 dépend de D6, qui dépend
de D5. Rien à retirer.
