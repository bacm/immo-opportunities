# Unités foncières du 35 — ce que chaque signal regrouperait

**Généré le** 2026-09-16 par `make property-unit-report`
(`property-unit-signals-v1`) — ticket [BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md).
**Recompté le 2026-09-16** par `recompte-preuve`, en isolement du code : aucune divergence. Une régénération efface cette mention.

Une unité foncière, ce sont des parcelles contiguës d'un même propriétaire ;
le propriétaire est hors d'atteinte. Ce rapport mesure les signaux qui restent.
**Il n'en choisit aucun** : le choix est une décision.

## Sources et filtres

- Parcelles du 35 : **1 333 327**,
  une unité `single_parcel` chacune aujourd'hui.
- Mutations DVF du 2014-01-02 au 2025-12-31 : 312 639 actes,
  332 394 parcelles distinctes rattachées au cadastre courant.
- 11 828 actes portent moins de parcelles distinctes
  rattachées que la source n'en déclare : une parcelle renumérotée ou divisée
  depuis la vente perd son rattachement.
  3 395 actes à plusieurs parcelles n'en
  gardent qu'une ou aucune, et échappent à tout regroupement par acte.
- Releases lues :
  - `DS-01@2026-06-01` (DS-01, `accepted`)
  - `DS-02@2026-09-05` (DS-02, `accepted`)
  - `DS-05@2026-06-17` (DS-05, `display_only`)
  - `DS-06@2019-04-archive` (DS-06, `pending`), 179 573 actes
  - `DS-06@2026-09-13` (DS-06, `display_only`), 133 066 actes
- Une release `pending` n'est pas acceptée : les actes qui en viennent comptent ici
  comme observation, pas comme donnée validée.
- Adresse : appariements adresse → parcelle `certain` seulement.
- Bâti : `reference.building_parcel`, part de l'emprise du bâtiment sur la parcelle,
  relations `certain` et `ambiguous` confondues. Depuis BUG-09, un bâtiment n'a qu'une
  relation `certain`, celle de la parcelle qui en porte le plus : **le signal repose
  donc entièrement sur les relations secondaires**, dont BUG-09 renvoie le seuil à E1.
- Contact : deux parcelles à moins de 1 cm.
- **Chaîné** : deux groupes qui partagent une parcelle fusionnent. C'est ce qui
  produit une partition — et ce qui peut faire d'un quartier une seule unité.

## Actes DVF portant plusieurs parcelles

- **76 461** actes,
  **226 117** parcelles distinctes.
- 64 836 actes ont au moins deux parcelles qui se
  touchent ; 53 893 sont d'un seul tenant, soit
  70,5 % des 76 461 actes à plusieurs parcelles.
- Un acte qui n'est pas d'un seul tenant vend ensemble des parcelles éloignées :
  même vendeur, mais pas une unité foncière au sens de la contiguïté.

## Ce que chaque signal regrouperait

| Signal | Unités de plus d'une parcelle | Parcelles regroupées | Part du 35 | Trois plus grandes | Cas 90 réuni | Cas 55 réuni |
|---|---:|---:|---:|---|:---:|:---:|
| DVF, même acte, chaîné | 58 802 | 226 117 | 17,0 % | 1 590, 198, 171 | non | non |
| DVF, même acte, parcelles contiguës, chaîné | 58 388 | 195 337 | 14,7 % | 171, 170, 144 | non | non |
| Adresse BAN commune, chaîné | 18 012 | 41 305 | 3,1 % | 41, 35, 26 | non | non |
| Bâti partagé, au moins 5 % de l'emprise sur chaque parcelle | 82 633 | 232 446 | 17,4 % | 48, 45, 44 | non | oui |
| Bâti partagé, au moins 10 % de l'emprise sur chaque parcelle | 64 761 | 160 584 | 12,0 % | 48, 24, 24 | non | oui |
| Bâti partagé, au moins 25 % de l'emprise sur chaque parcelle | 27 506 | 58 581 | 4,4 % | 43, 10, 9 | non | oui |
| Bâti partagé, au moins 40 % de l'emprise sur chaque parcelle | 8 966 | 18 206 | 1,4 % | 6, 5, 4 | non | non |

### Taille des unités

| Signal | 2 | 3 à 5 | 6 à 10 | 11 à 50 | 51 à 500 | plus de 500 |
|---|---:|---:|---:|---:|---:|---:|
| DVF, même acte, chaîné | 29 042 | 21 972 | 5 558 | 2 130 | 99 | 1 |
| DVF, même acte, parcelles contiguës, chaîné | 31 532 | 21 075 | 4 515 | 1 219 | 47 | 0 |
| Adresse BAN commune, chaîné | 14 542 | 3 315 | 126 | 29 | 0 | 0 |
| Bâti partagé, au moins 5 % de l'emprise sur chaque parcelle | 52 419 | 25 699 | 3 857 | 658 | 0 | 0 |
| Bâti partagé, au moins 10 % de l'emprise sur chaque parcelle | 46 970 | 16 331 | 1 340 | 120 | 0 | 0 |
| Bâti partagé, au moins 25 % de l'emprise sur chaque parcelle | 24 687 | 2 769 | 49 | 1 | 0 | 0 |
| Bâti partagé, au moins 40 % de l'emprise sur chaque parcelle | 8 712 | 253 | 1 | 0 | 0 | 0 |

## Corroboration par les ventes

Unité : la paire distincte de parcelles prise **dans un même groupe** — même acte,
même adresse, même bâtiment —, sans chaînage. Parmi ces paires, celles dont les deux
parcelles ont été vendues, et la part vendue dans un même acte. Une paire dont une
parcelle n'a jamais été vendue est exclue du dénominateur. Le signal DVF vaut 100 %
par construction : sa ligne ne donne que ses effectifs. La ligne de base ne compte que
les paires internes à la commune.

| Signal | Paires | Deux parcelles vendues | Vendues ensemble | Taux |
|---|---:|---:|---:|---:|
| DVF, même acte | 866 436 | 866 436 | 866 436 | 100,0 % |
| Adresse BAN commune | 29 575 | 8 625 | 8 005 | 92,8 % |
| Bâti partagé, au moins 5 % de l'emprise sur chaque parcelle | 173 010 | 34 940 | 22 402 | 64,1 % |
| Bâti partagé, au moins 10 % de l'emprise sur chaque parcelle | 104 840 | 22 483 | 15 553 | 69,2 % |
| Bâti partagé, au moins 25 % de l'emprise sur chaque parcelle | 31 625 | 7 642 | 6 008 | 78,6 % |
| Bâti partagé, au moins 40 % de l'emprise sur chaque parcelle | 9 241 | 2 440 | 1 916 | 78,5 % |
| Ligne de base : parcelles contiguës, commune 35093 | 26 314 | 3 651 | 1 227 | 33,6 % |
| Ligne de base : parcelles contiguës, commune 35238 | 82 967 | 13 368 | 3 507 | 26,2 % |
| Ligne de base : parcelles contiguës, commune 35288 | 71 357 | 9 910 | 3 750 | 37,8 % |

Vendues ensemble ne veut pas dire « même propriétaire » : c'est l'indice le plus
proche que les données autorisées donnent. Un signal au niveau de la ligne de base
n'apporte rien de plus que la contiguïté, déjà disqualifiée.

## Cas de référence

| Parcelle | Actes DVF | Vendue avec |
|---|---:|---|
| `35033000ZS0089` | 0 | — |
| `35033000ZS0091` | 0 | — |
| `35288000DA0321` | 1 | `35288000DA0323` |
| `35288000DA0322` | 0 | — |
