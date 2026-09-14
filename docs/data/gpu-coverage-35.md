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
