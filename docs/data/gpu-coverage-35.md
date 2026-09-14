# Couverture des documents d'urbanisme — département 35

**Date :** 14 septembre 2026 · **Ticket :** [D2](../backlog/D2-import-gpu-ds08.md)
**Release :** `DS-08@2026-09-14` · **Source :** Géoportail de l'urbanisme, exports CNIG

## Ce qui est épinglé

| | |
|---|---:|
| Documents | **184** — 164 PLU, 14 cartes communales, 6 PLUi |
| Couches structurées | 1 257 |
| **Volume épinglé** | **707,6 Mo** |
| Archives correspondantes | **34,2 Go** |
| Documents illisibles | **0** |

Le rapport dit l'essentiel de la méthode : **707 Mo d'empreintes pour 34 Go d'archives**, soit
2 %, et sans qu'aucune archive ait été téléchargée intégralement. Le répertoire central d'un ZIP
étant à sa fin, on lit la queue du fichier puis les seuls membres voulus.

## Couverture communale

| | Communes | Part |
|---|---:|---:|
| Déclarées par un document | 300 | — |
| **Présentes dans notre référentiel** | **290** | **87,3 %** |
| Sans document — RNU | **42** | 12,7 % |

### Les PLUi sont invisibles d'une requête départementale

Un PLUi porte le **SIREN de l'EPCI** comme code de territoire, jamais un code départemental.
`territory=35` ne les retourne pas, et `territory=<code commune>` ne retourne rien : le filtre
porte sur le territoire du document, pas sur les communes couvertes.

Six PLUi couvrent le 35, et il faut les chercher parmi les 565 de France, puis lire leur
`DOC_URBA_COM` :

| PLUi | Communes du 35 |
|---|---:|
| Rennes Métropole | 43 |
| Bretagne Romantique | 25 |
| Bretagne Porte de Loire Communauté | 20 |
| Val d'Ille-Aubigné | 19 |
| Couesnon Marches de Bretagne | 8 |
| Brocéliande | 8 |

**Le PLUi de Rennes Métropole représente à lui seul 43 communes.** Une requête départementale
naïve l'aurait perdu, et avec lui la métropole entière.

### Dix communes déclarées que notre référentiel ne connaît pas

`35011`, `35100`, `35112`, `35113`, `35269`, `35293`, `35301`, `35303`, `35341`, `35348`.

Chacune est déclarée par un document communal à son propre nom — `DU_35100` déclare `35100` — sauf
`35011`, portée par le PLUi de Couesnon. Ce sont des **communes fusionnées** : le GPU publie encore
leur document sous l'ancien code, qui a disparu du cadastre.

C'est le même phénomène que le décalage temporel mesuré sur DVF, où le taux de rattachement monte
de 96,3 % en 2021 à 99,3 % en 2025. Les documents d'urbanisme survivent à la fusion des communes
qu'ils régissaient, et le référentiel cadastral non.

**Aucun rattrapage n'est tenté ici.** Retrouver la commune absorbante demanderait une table de
correspondance des fusions, qui est une source à part entière — contrat, manifeste, verdict. Ces
dix documents restent épinglés avec leur code d'origine ; leurs zones se rattacheront par la
géométrie, qui ignore les fusions.

## Un document réparé par une provenance dégradée

**Dinard, `DU_35093`.** Ses deux fichiers `DOC_URBA.dbf` et `DOC_URBA_COM.dbf` commencent par
`0x50` et contiennent `[Content_Types].xml` : ce sont des **archives Office déposées sous une
extension `.dbf`** par le producteur. Les cinq autres couches — dont les 57 zones — sont de vrais
DBF, parfaitement lisibles.

Le document ne peut donc pas déclarer les communes qu'il couvre. Mais le catalogue les déclare
ailleurs : `grid = {name: "35093", title: "DINARD", type: "municipality"}`.

Le rattrapage est fait, et **marqué `catalog_fallback`** dans le manifeste pour rester visible.
Ce n'est pas une convention inventée — prendre le producteur au mot sur un canal distinct n'est
pas deviner `35093` depuis le nom de fichier `DU_35093`.

**La frontière est codée et testée :** seul un document dont `grid.type = municipality` est
rattrapable. Un PLUi ne l'est jamais, son `grid` portant le SIREN de l'EPCI sans rien dire des
communes couvertes — Rennes Métropole en couvre 43, qu'aucun champ du catalogue n'énumère.
Deviner y serait faux, pas dégradé.

## Ce que cette couverture ne dit pas

- **Elle ne dit pas que le zonage est importé.** Ce rapport porte sur l'épinglage ; l'import des
  zones et des prescriptions reste à faire.
- **Elle ne dit rien des règles d'urbanisme.** `URB-002` et `URB-004` demandent qu'un humain lise
  chaque règlement, ce qui relève de [D2b](../backlog/D2b-profils-de-regles.md) et représente
  près de quatre années-personne à l'échelle nationale. `URB-005` publiera cette incomplétude.
- **Elle ne vaut que pour le 35.** La France compte 12 795 documents d'urbanisme en production.

## Reproduire

```bash
cd pipelines && uv run python scripts/pin_gpu_release.py --department 35 --release 2026-09-14
```

Reprise sur manifeste existant, écriture au fil de l'eau. Un échec passager n'est pas consigné
comme définitif et le script sort en code 3 pour dire que le manifeste est incomplet.


## Features URB matérialisées — 14 septembre 2026

**1 333 327 unités**, 332 communes, 16 minutes, aucun échec.

| Feature | Calculées | Absentes | Motifs |
|---|---:|---:|---|
| `URB-001` code de zone | **554 714** | 778 613 | `source_not_accepted`, `ambiguous_match` |
| `URB-003` contraintes | **380 679** | 952 648 | `source_not_accepted` |
| `URB-005` complétude | 1 333 327 | 0 | — |
| `URB-002`, `URB-004` | 0 | 1 333 327 | `source_value_missing` |

**257 communes sur 332 portent un zonage**, contre 300 couvertes par le manifeste : l'écart est
celui des 32 documents non importés, le lot ayant été arrêté volontairement.

### La distribution des types de zone est celle d'un département rural

| `typezone` | Unités | Part |
|---|---:|---:|
| **A** agricole | 271 074 | **48,9 %** |
| **U** urbaine | 158 488 | 28,6 % |
| **N** naturelle | 111 844 | 20,2 % |
| `AUc` à urbaniser | 9 964 | 1,8 % |
| `Ah`, `AUs`, autres | 2 860 | 0,5 % |

Près d'une parcelle zonée sur deux est agricole, et à peine 2 % sont ouvertes à l'urbanisation.
C'est cohérent avec ce que le cadastre disait déjà — plus de la moitié des parcelles du 35 ne
portent aucun bâtiment — et c'est directement pertinent pour la stratégie division / extension :
**le gisement est étroit**, et le scoring devra en tenir compte plutôt que de traiter le
département comme un ensemble homogène.

### 2 114 unités en `ambiguous_match`

Ce sont les ex æquo parfaits : deux zones couvrent exactement la même part de la parcelle, et le
rang ne départage pas. Choisir serait arbitraire, donc la feature est absente avec ce motif — la
quatrième classe de la résolution d'entités existe pour cela.

Soit **0,4 % des unités zonées**. Le rang tranche donc dans 99,6 % des cas sans qu'aucun seuil
n'ait été inventé.

### `URB-005` vaut zéro partout, et c'est le résultat

Aucun profil de règles n'est validé, puisque [D2b](../backlog/D2b-profils-de-regles.md) n'a pas
commencé — c'est un travail humain de près de quatre années-personne à l'échelle nationale. La
feature existe précisément pour publier cette incomplétude plutôt que de la taire.
