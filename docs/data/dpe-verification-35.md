# Vérification manuelle des diagnostics DPE — département 35

**Date :** 15 septembre 2026 · **Ticket :** [D6b](../backlog/D6b-verification-diagnostics-parcelle.md)
**Instrument :** bloc « diagnostics DPE » de la fiche parcelle, Explorer
**Release vérifiée :** `DS-07@2026-09-14-extract`, `display_only`

## Ce que l'instrument est, et n'est pas

Un bloc replié dans la fiche parcelle, symétrique de celui des mutations de
[D6a](./dvf-verification-35.md), qui liste les diagnostics atteignant la parcelle par un de ses
bâtiments RNB. **Ce n'est pas un consultatif DPE** : pas d'entrée de menu, pas de filtre par
étiquette, pas d'export, et aucune couleur de A à G — ni dans le bloc, ni sur la carte. Une
classe F rendue en rouge deviendrait un signal de dégradation, et une observation de diagnostic
n'est pas une preuve d'état du bâti.

Aucune agrégation n'est calculée à l'affichage : pas d'étiquette « dominante » de la parcelle,
qui fabriquerait une valeur n'existant nulle part.

## Ce qui n'était visible nulle part avant

208 086 diagnostics sont en base depuis [D4](../backlog/D4-import-dpe-ds07.md). L'unique lecture
qui les exposait, `GET /property-units/{id}/market-context`, joint `meta.active_dataset_release`
— **qui ne contient aucune ligne pour DS-07**, la release n'étant pas publiée. Elle renvoyait
donc systématiquement `energy_assessment: null`. La donnée était importée, contrôlée, rapportée,
et invisible.

## Le chemin de rattachement

```text
energy_assessment.building_id  →  reference.building (RNB)
                               →  reference.building_parcel  →  reference.parcel
```

| Mesure | Valeur |
|---|---:|
| Diagnostics rattachés à un bâtiment RNB | 136 628 |
| … atteignant une parcelle | 136 294 |
| Parcelles portant au moins un diagnostic certain | 46 695 |
| Relations `certain` par diagnostic | exactement 1, sans exception |
| Parcelles touchées en comptant les relations `ambiguous` | 2,24 en moyenne |

Les **71 458** diagnostics rattachés à la seule adresse restent hors de l'écran. Les poser sur une
parcelle demanderait la relation adresse ↔ parcelle, que [B4](./spatial-matching-manual-review-35.md)
a établie non vérifiable par aucune règle géométrique, avec environ 24 % d'erreur irréductible.
Le bloc énonce cette limite à l'écran, pas seulement ici.

## Ce que la vérification a trouvé

### 1. Le rattachement tient, et on peut désormais le dire avec un chiffre

Confronter la surface habitable déclarée au diagnostic à l'emprise au sol du bâtiment RNB auquel
il est rattaché donne une mesure de plausibilité que rien ne produisait jusqu'ici.

| Type déclaré | Diagnostics | Surface DPE médiane | Emprise médiane du bâtiment |
|---|---:|---:|---:|
| appartement | 88 797 | 57,0 m² | 443,1 m² |
| maison | 44 115 | 96,0 m² | 105,0 m² |
| immeuble | 20 | 180,5 m² | 100,7 m² |

Une maison de 96 m² habitables sur une emprise de 105 m², un appartement de 57 m² dans un
bâtiment de 443 m² d'emprise : le rattachement place les diagnostics sur un bâti de la bonne
taille. **154 diagnostics sur 132 932** — 0,12 % — déclarent plus de quatre fois l'emprise du
bâtiment qui les porte.

### 2. Un identifiant saisi par logiciel est 5,8 fois plus souvent incohérent

C'est le résultat principal, et il porte sur l'hypothèse que cet écran existait pour mettre à
l'épreuve : `match_confidence` vaut 1,0 pour **tout** diagnostic rattaché par `id_rnb`, parce que
l'identifiant est déclaré par le producteur et repris tel quel. Une confiance héritée n'est pas
une confiance vérifiée.

| Provenance de l'`id_rnb` | Diagnostics | Surface > 4× l'emprise | Taux |
|---|---:|---:|---:|
| Reprise RNB | 116 754 | 85 | **0,073 %** |
| Logiciel | 16 178 | 69 | **0,427 %** |

Les identifiants saisis par le logiciel du diagnostiqueur sont incohérents **5,8 fois plus
souvent** que ceux repris du RNB. Les deux taux restent faibles, et aucun ne justifie d'écarter
une population : le constat est que la fragilité existe, qu'elle est localisée, et qu'elle est
désormais mesurée. C'est pourquoi le bloc affiche la provenance diagnostic par diagnostic plutôt
qu'une confiance qui vaudrait 1,0 partout.

### 3. Le filtre « rattaché bâtiment » peut retenir l'ancien et écarter le nouveau

Deux diagnostics présents en base sont explicitement remplacés par un autre diagnostic également
présent. Dans les deux cas, **le remplaçant n'a pas d'`id_rnb` et le remplacé en a un** :

| Remplaçant | Date | Remplacé | Date | Visible sur la fiche parcelle |
|---|---|---|---|---|
| `2635E0230360O` | 2026-01-26 | `2235E1476415P` | 2022-06-29 | le remplacé seulement |
| `2535E3339507C` | 2025-10-22 | `2435E1744762S` | 2024-05-17 | le remplacé seulement |

L'écran montre donc un diagnostic périmé et cache celui qui le remplace. **Ampleur : 2 cas sur
208 086.** Le mécanisme, lui, n'est pas anecdotique : le filtre de rattachement n'est pas neutre
vis-à-vis de la fraîcheur, et rien ne garantit qu'un diagnostic plus récent soit mieux rattaché.
À reprendre dans [D6](../backlog/D6-revue-manuelle-metier.md), qui revoit la règle de sélection.

### 4. Le cas extrême est plausible, et ce n'était pas acquis

La parcelle `35238000AZ0487` porte **526 diagnostics**, le maximum du département. Regardée de
près, elle est cohérente :

| Mesure | Valeur |
|---|---:|
| Bâtiments RNB | 2 |
| Adresses distinctes | 22 |
| Emprise bâtie | 2 792 m² |
| Surface de la parcelle | 21 240 m² |
| Surface habitable cumulée | 24 720 m² |
| Surface moyenne par diagnostic | 47,4 m² |

24 720 m² habitables sur 2 792 m² d'emprise donnent environ neuf niveaux, pour des logements de
47 m² en moyenne, sur deux bâtiments et 22 entrées déclarés construits entre 1948 et 1984. C'est
une résidence collective, pas un défaut de rattachement. **La cardinalité forte était le candidat
le plus probable à un défaut d'appariement : elle n'en est pas un.**

### 5. Aucun défaut là où DVF en avait

Trois contrôles repris de [D6a](./dvf-verification-35.md), qui y avaient trouvé des défauts :

| Contrôle | Résultat |
|---|---|
| Versions de transformation coexistantes | une seule, `v1` — l'origine de 133 066 doublons DVF |
| Bâtiments non actifs porteurs d'un diagnostic | aucun, les 136 628 sont `active` |
| Fiche gardant les diagnostics de la parcelle précédente | prévenu, et couvert par un test e2e |

Le troisième n'est pas une constatation mais une précaution : le défaut d'état résiduel de D6a
vient de ce que React réutilise l'instance du composant d'une parcelle à l'autre. Le bloc DPE est
rendu au même endroit et aurait reproduit le défaut à l'identique.

## Un écart de comptage qui n'en est pas un

`dpe-matching-35.md` annonce SAINT-JUST à **14,75 %** (18 rattachés sur 122). La table
`observation.energy_assessment` n'y contient que **39** diagnostics, ce qui donnerait 46,15 %.

Les deux sont justes et ne comptent pas la même chose : les **83** diagnostics manquants sont en
quarantaine `unresolved_source_identifier`, aucun identifiant déclaré ne s'y résolvant. Le
rapport d'appariement compte sur l'extrait complet, la table ne contient que les conservés.
Vérifié : 39 + 83 = 122.

## Ce que cette vérification ne dit pas

- **Rien sur la justesse d'un diagnostic.** Elle vérifie qu'il est posé au bon endroit, pas que
  sa classe est la bonne.
- **Rien sur les 71 458 rattachés à la seule adresse.** Ils restent hors de portée de tout
  instrument géométrique, et c'est un résultat de B4, pas une limite de cet écran.
- **Rien sur la sélection.** Quel diagnostic retenir quand une parcelle en porte 526 est la
  question de [D6](../backlog/D6-revue-manuelle-metier.md), pas celle-ci.
