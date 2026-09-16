# H1 — Baromètre du marché du 35 : les mesures, reproductibles et recomptées

**Version :** V5 · baromètre · **Taille :** L · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/market_barometer.py, pipelines/tests/test_market_barometer.py, Makefile, docs/data/barometre-marche-35.md, docs/data/barometre-marche-35/
**Dépend de :** A7 · **Bloque :** H2
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)

## Contexte à charger

- `docs/data/pistes-analyse-marche-35.md` (sections 2, 5.1, 5.2 et les SQL de `pistes-analyse-marche-35/`)
- `docs/data/dpe-signal-vente-35.md` (limites, et l'écart de comptage 14 532 / 9 754)
- `docs/data/dvf-quality-35.md` (prix non allouable, doublons de versions de transformation)
- `pipelines/scripts/market_listing_candidates.py` (comment E8f nomme sa cohorte et son filtre)
- `.claude/skills/recompte-preuve/SKILL.md`

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket produit

Un script `make market-barometer DEPARTMENT=35` qui régénère `docs/data/barometre-marche-35.md`
et un répertoire de tableaux CSV, à partir des seules tables `observation.transaction`,
`observation.energy_assessment` et du référentiel spatial. **Aucune source nouvelle, aucun
score, aucune parcelle nommée** : toutes les mesures sont agrégées par commune, EPCI ou
département, avec leur support.

## Les mesures

Toutes existent déjà sous forme de sondages « non recomptés » dans `pistes-analyse-marche-35.md`
§5. Ce ticket les rend reproductibles, les nomme, et les recompte.

| Mesure | Granularité | Ce qu'elle dit au professionnel |
|---|---|---|
| Volumes et prix médians au m², maisons et appartements | EPCI × année, commune × année si support | le marché tel qu'il est |
| Plus-value nette de marché par prix d'entrée (ventes répétées) | département, EPCI si support | où est la marge d'un marchand |
| Décote ou surcote par étiquette DPE, contrôle commune × année | département, EPCI si support | ce que vaut réellement une passoire |
| Délai dépôt DPE → acte, quartiles | commune (support ≥ 200), EPCI | délai de vente observé |
| Taux de mutation à 12 mois après premier DPE, par cohorte annuelle | commune (support ≥ 200), EPCI, département | la température du marché |
| Courbe de conversion mensuelle, cohorte la plus récente couverte | département, EPCI | quand un bien mis en vente part |
| Effet de l'extension de surface bâtie sur le prix total et au m² | département | ce que rapporte un agrandissement |
| Part des mutations sans prix allouable, part des DPE non rattachés | commune | ce que le baromètre ne voit pas |

## Règles

- **Le filtre de chaque cohorte est écrit dans la sortie**, en clair : relations bâtiment ↔ parcelle
  retenues, premier DPE par parcelle ou par bâtiment, types de bâtiment exclus. C'est la leçon de
  l'écart 14 532 / 9 754 : un effectif sans son filtre n'est pas reproductible.
- **Un taux ne paraît jamais sans son effectif**, et un seuil de support n'est pas un seuil
  inventé : il est déclaré comme paramètre du script et affiché.
- **Les DPE d'appartement générés depuis un DPE d'immeuble sont exclus** des mesures de conversion
  (0,6 %, mesuré), et l'exclusion est comptée.
- **La réforme DPE du 1er janvier 2026** (coefficient électricité) est une rupture de série : les
  mesures par étiquette distinguent avant et après, ou portent la réserve en toutes lettres.
- **DVF s'arrête au 31 décembre 2025** : aucune cohorte dont les douze mois ne sont pas couverts
  n'entre dans un taux à douze mois.
- Aucune valeur manquante n'est convertie en zéro ; une commune sans support apparaît « sans
  support » avec son effectif.

## Ce que ce ticket ne fait pas

- Il ne publie aucune parcelle ni aucune adresse. Le radar nominatif est H5, derrière H4.
- Il n'estime la valeur d'aucun bien non vendu (E7 reste suspendu).
- Il n'introduit ni modèle hédonique ni pondération : contrôle commune × année seulement, comme
  dans les sondages.

## Ce qui a été produit

`make market-barometer DEPARTMENT=35` écrit `docs/data/barometre-marche-35.md` et huit tableaux
CSV dans `docs/data/barometre-marche-35/`, plus `epci-communes.csv`. Le calcul est en Python sur
des lignes lues par cinq requêtes : les mesures se testent sans base, et trente tests couvrent
chaque mesure, le cas « support insuffisant » et le cas « cohorte non couverte par DVF ».

Deux décisions prises ici, faute d'être tranchées ailleurs :

- **Le découpage EPCI vient de DS-03 BDNB**, seule source du dépôt qui porte `code_epci_insee` —
  332 communes, chacune rattachée à un et un seul EPCI, 18 EPCI. Il sert de clé géographique,
  jamais d'attribut classant d'un bien. `SPEC.md` §13.3 ne range pas DS-03 parmi les sources du
  baromètre parce qu'il raisonne en attributs de bien ; le rattachement territorial n'en est pas
  un. La provenance est écrite dans le rapport, et le référentiel tient dans un CSV : en changer
  coûte un fichier.
- **La médiane de référence commune × année exige le même support que BAR-001**, quinze ventes.
  Les sondages de `pistes-analyse-marche-35.md` §5.2 utilisaient quinze pour la marge et vingt
  pour l'étiquette, sans le dire ; un seul paramètre déclaré vaut mieux que deux implicites. Les
  valeurs par étiquette s'en écartent donc légèrement.

L'écart **14 532 / 9 754** est tranché dans le rapport : sous le filtre écrit, la cohorte 2024
compte 9 754 parcelles avant l'exclusion des DPE d'immeuble et 9 653 après. Le 14 532 n'est pas
reproductible et cesse d'être cité ; le taux, lui, se retrouve à 35,5 % contre 35,65 %.

## Ce que le recompte a attrapé

Première passe de `recompte-preuve`, en isolement du code. Vingt-neuf chiffres éprouvés, vingt-deux
confirmés du premier coup — dont les 96 valeurs de BAR-001/002 à l'unité. Sept divergences, toutes
corrigées avant de fermer le ticket. C'est ce que `make check` ne pouvait pas voir.

| # | Ce que le recompte a trouvé | Correction |
|---|---|---|
| D1 | L'événement « vendue sous douze mois » comptait la VEFA et le terrain à bâtir, que le tableau des filtres déclarait écartés | Le filtre de l'événement est écrit à part, et le rapport publie sa sensibilité : 35,5 % toute mutation, 34,7 % en exigeant un lot de logement |
| D2 | La somme des EPCI ne bouclait pas avec le département sur BAR-005 à BAR-007, et les CSV portaient 334 communes pour 332 annoncées | **Défaut de fond** : la commune d'une parcelle de cohorte venait du `commune_code` du DPE, que 78 diagnostics déclarent hors du cadastre. Elle vient désormais de la parcelle. Les trois mesures bouclent |
| D3 | Le funnel DPE perdait 334 unités sans motif entre « rattaché à un bâtiment » et « rattaché à une parcelle » | Ligne ajoutée au tableau des cohortes, avec son motif |
| D4 | Quatre filtres appliqués mais non écrits, dont un qui renversait une conclusion : le « ratio au m² de 1,00 » de BAR-008 ne tenait qu'à une fenêtre de trois ans jamais déclarée | Les quatre sont écrits. BAR-008 publie **les deux fenêtres** : 205 paires à 1,00 sous trois ans, 743 paires à 1,17 toutes durées |
| D5 | « paires de ventes répétées » se lisait comme toutes les combinaisons — 10 100 — alors que le chiffre publié comptait les paires consécutives | Formulation corrigée, et l'entonnoir 7 024 → 1 505 est publié avec ses trois motifs d'écartement |
| D6 | DS-02 absent de la table des sources lues, alors que tout lien DPE ↔ parcelle passe par une identité RNB | Ajouté |
| D7 | Deux taux à douze mois publiés à quatre lignes d'écart, 35,5 % et 35,1 %, sans rapprochement | Expliqué : mois conventionnels de 30 jours, soit 360 jours contre 365 |

D2 et D4 sont les deux qui comptent : le premier était un défaut de calcul qu'aucun test ne
pouvait attraper, le second un résultat publiable dont la conclusion dépendait d'un choix tu.

Deuxième passe sur le rapport corrigé : **quarante-quatre chiffres éprouvés, quarante-deux
confirmés, aucune divergence de valeur**. Les 1 280 lignes communales de BAR-006 et les 4 929
cellules de BAR-001/002 sont identiques à l'unité à un recompte indépendant, les sommes EPCI
bouclent avec le département sur les trois mesures de cohorte, et les sept corrections tiennent.
Trois réserves de forme et un chiffre hérité, traités à leur tour :

| Réserve | Traitement |
|---|---|
| R1 — 105 couples (parcelle, date) portent plusieurs ventes le même jour ; la règle de départage décidait des bandes de BAR-003 sans être écrite | La règle — prix croissant, puis surface croissante — est écrite dans le rapport et tenue par un test |
| R2 — BAR-008 ne publiait aucun filtre, et « toutes durées » signifiait en fait « au-delà de 180 jours » | Filtre écrit, fenêtre renommée pour ce qu'elle est |
| R3 — BAR-004 publie une étiquette à effectif nul, BAR-001/002 omet une cellule vide | Les deux traitements sont délibérés et désormais expliqués : l'absence d'une étiquette est une information, une cellule année × type sans vente n'existe pas |
| Le **0,6 %** de `SPEC.md` §7.3, hérité de `pistes-analyse-marche-35.md` §1.4, ne se reproduit sous aucun filtre | Mesuré ici : 277 parcelles, 1 mutation, **0,4 %**. Même ordre de grandeur, pas le même chiffre. L'exclusion garde sa justification ; le chiffre à citer est celui-ci. **`SPEC.md` porte un chiffre non reproductible — à corriger par [H6](./H6-reecrire-spec.md)** |

## Après la clôture — BR-007 honoré

`SPEC.md` §9.1 exige, par BR-007, une « mention datée en tête du rapport » attestant le passage de
`recompte-preuve`. Le rapport clos ne la portait pas. Elle y est, et elle ne peut pas mentir : le
script calcule une **empreinte SHA-256 des huit CSV de mesures**, et la mention « Recompté le … »
n'apparaît que si `barometre-marche-35/recompte.csv` porte une attestation de cette empreinte
exacte. Qu'une mesure change, l'empreinte change, l'attestation cesse de s'appliquer, et le
rapport écrit « Non recompté » de lui-même. Une attestation mal formée arrête la génération.

La troisième passe du recompte, ciblée sur ce qui avait bougé après la deuxième — le 0,4 % des
DPE d'immeuble, les deux fenêtres de BAR-008, la table des releases — n'a trouvé aucune
divergence. L'attestation du 16 septembre porte l'empreinte `d08dba5d179c319e`.

Deux ajouts servent H2 : `metadonnees.csv` porte les millésimes, les dates, les supports et
l'état du recompte, pour que chaque page du document les imprime sans relire la base ; la table
« Ce qui a été lu » ne liste plus que les releases réellement importées, ce qui en retire
`DS-02@2026-08-01`, découverte mais jamais chargée.

## Critères d'acceptation

- `make market-barometer` régénère le rapport à l'identique sur la même base (graine et filtres
  écrits) ;
- tests : chaque mesure a un test sur fixture minimale, dont un cas « support insuffisant » et un
  cas « cohorte non couverte par DVF » ;
- `recompte-preuve` a été passé sur le rapport avant `Terminé`, et l'écart 14 532 / 9 754 de
  `dpe-signal-vente-35.md` est soit expliqué, soit remplacé par l'effectif du filtre écrit ;
- `make check` vert.
