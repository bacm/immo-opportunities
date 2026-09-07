# B2a — Importer et auditer DS-03 BDNB Open sur le 35

**Version :** v0.3 · **Taille :** L · **État :** Terminé
**Dépend de :** — · **Bloque :** B3, B5

## Contexte à charger

- `contracts/datasets/DS-03/v1.json`
- `docs/data/spatial-sources-audit.md` (§DS-03)
- `pipelines/src/immo_pipelines/spatial/importer.py`
- `pipelines/src/immo_pipelines/cadastre/catalog.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DS-03 n'a qu'un contrat. L'audit note : « archive départementale historique identifiée pour le
millésime `2024-10-a` ; le millésime courant est distribué en export national volumineux, non
épinglé tant que son découpage et son checksum ne sont pas reproductibles localement ».

**Piège identifié et à ne pas commettre :** le RNB transporte 715 315 identifiants BDNB externes
dans son champ `ext_ids`. Ces identifiants sont des *références observées*, pas une observation de
BDNB. Ils ne dispensent d'aucun import et ne permettent de calculer aucune feature BDNB.

## Décision sans objet — 7 septembre 2026

L'arbitrage ci-dessous supposait qu'il fallait choisir entre un millésime ancien et un découpage
local de l'export national. **La prémisse était fausse.** Le producteur publie un export
**départemental daté** pour le millésime courant `2026-02-a`, listé sur la page du millésime et
absent du catalogue data.gouv qui ne référence que les exports France entière. Il publie de plus
un SHA-256 dans un `_metadata.yml` voisin — le premier producteur du dépôt à le faire.

Release épinglée : GeoPackage de 804 719 036 octets, SHA-256 `eea296e0…18c9`, vérifié conforme.
Aucun découpage local n'est en jeu. Détail dans
[l'audit spatial §DS-03](../data/spatial-sources-audit.md#ds-03--bdnb-open).

### L'arbitrage tel qu'il était posé

| Option | Avantage | Inconvénient |
|---|---|---|
| Millésime `2024-10-a`, archive départementale | checksum et découpage immédiats | millésime ancien, fraîcheur dégradée à documenter |
| Millésime courant, export national découpé localement | fraîcheur | le découpage doit être déterministe et checksumé, sinon la release n'est pas reproductible |

## Avancement

Étapes 1 et 2 faites : décision tranchée et inscrite dans l'audit, release résolue, checksumée et
épinglée dans
[`contracts/datasets/DS-03/releases/2026-02-a-35.json`](../../contracts/datasets/DS-03/releases/2026-02-a-35.json).

Le modèle est mesuré : 546 301 groupes BDNB pour 783 684 constructions physiques, et
726 364 relations vers le RNB **au niveau construction**. La cardinalité que l'étape 5 interdit
d'aplatir est donc portée par la source.

La politique de champs de l'étape 6 a une base objective : le dictionnaire `metadonnees_colonne`
livré dans l'archive déclare le régime d'accès des 1 888 colonnes du modèle, et l'export
départemental ne contient **aucune** colonne `ayant_droit_*`. Le contrôle bloquant
`expert_fields_excluded` est donc vérifiable contre la déclaration du producteur.

**Étapes 3 à 8 faites.** Verdict `display_only`, release publiée. Rapport complet dans
[l'audit spatial §DS-03](../data/spatial-sources-audit.md#ds-03--bdnb-open).

546 301 groupes lus, 546 301 normalisés, **0 en quarantaine**. Contrôle bloquant
`expert_fields_excluded` au vert : 1 888 colonnes documentées inspectées, aucune `ayant_droit_*`.

| Décision | Groupes | Liens |
|---|---:|---:|
| certain | 422 194 | 422 194 |
| ambigu | 104 823 | 303 219 |
| rejeté | 0 | 0 |
| non apparié | 19 284 | — |

## Périmètre retenu, et pourquoi

**Six champs, pas 293.** Le niveau « bâtiment physique » de la BDNB est la BD TOPO —
`batiment_construction.hauteur` et sa géométrie sont documentées `(ign)` par le producteur. DS-04
les fournit nativement depuis [B2b](./B2b-import-bdtopo-ds04.md) : les importer aurait été un
doublon. `batiment_construction` ne sert donc que de pont vers le RNB.

L'apport propre de la BDNB tient dans six colonnes Fichiers Fonciers, dont deux que nulle autre
source du MVP ne fournit : `annee_construction` (376 206 groupes) et `nb_niveau` (391 416). Elles
servent REN-001 et REN-003.

Les copies de sources primaires sont écartées **à l'import**, non au calcul : le contrat prévoit
qu'une valeur primaire supplante sa copie BDNB au calcul des features, mais DS-07 n'existe pas
encore, donc les 149 colonnes DPE auraient été de fait la seule source DPE disponible — donc
utilisées, exactement ce que le contrat veut empêcher.

Trois ensembles déclarés `open_data_lo` par le producteur restent écartés pour des raisons de
périmètre produit : les tables `proprietaire` et `rel_batiment_groupe_proprietaire`, les
indicateurs modélisés `batenr_*`, et l'usage recalculé `synthese_propriete_usage`.

## La règle de décision ne repose sur aucun seuil inventé

`certain` exige le cumul de deux conditions : le groupe se résout en un **unique** bâtiment RNB,
et **toutes** ses relations portent le type `Alignement 1 BC = 1 RNB, recouvrement ≥ 95 %`.

Ce type énonce son critère, il n'est pas une confiance opaque — c'est ce qui distingue DS-03 de
DS-05, dont les paliers étaient les nôtres et sans mesure.

**Vérifié plutôt que cru.** Sur la totalité des 422 194 rattachements certains : médiane de
recouvrement à 1,0000, moyenne 0,9890, et 406 950 soit **96,4 %** au-delà de 95 %. L'écart
résiduel s'explique entièrement par un groupe plus vaste que le bâtiment — rapport de surface 1,00
puis 1,37 puis 2,72 selon la classe — et non par un rattachement faux.

**Limite assumée :** le producteur affirme ce recouvrement au niveau *construction*, nous le
mesurons au niveau *groupe*, faute de détenir la géométrie des constructions que nous avons
écartée comme doublon. Vérifier son affirmation à son propre niveau exigerait d'importer ce que
nous avons délibérément exclu.

## Conséquence persistée pour B5

Chaque lien certain porte `group_building_overlap_ratio` et `group_area_over_building_area` dans
sa preuve. Même certain, un attribut publié au niveau groupe peut décrire plus que le bâtiment
auquel il est rattaché : sur 11 384 cas — 2,7 % — le groupe dépasse le bâtiment de plus de 20 %.
[B5](./B5-features-morphologiques.md) doit filtrer là-dessus, et non se fier au seul statut
`certain`, sans quoi un `nb_log` de groupe surcompterait en silence.

## Pourquoi `display_only` et non `accepted`

Le blocage ne vient pas de la qualité de DS-03. Ses 422 194 rattachements certains désignent des
bâtiments dont l'identité vient du RNB, et `DS-02@2026-09-05` n'est pas acceptée : elle attend
[B4](./B4-revue-manuelle-appariements.md). Faire entrer DS-03 dans le périmètre d'analyse pendant
que son support d'identité n'y est pas serait incohérent.

Motif donc différent de DS-04 et DS-05, qui attendent la calibration de leurs propres seuils. À la
clôture de B4, DS-03 est la release la mieux placée pour devenir la première `accepted` au-delà du
cadastre.

## Travail à réaliser

1. Trancher la décision ci-dessus et l'inscrire dans l'audit.
2. Résoudre l'URL exacte (jamais un alias `latest`), relever taille et SHA-256, écrire
   `contracts/datasets/DS-03/releases/<release>-35.json`.
3. Archiver l'asset dans MinIO avec son checksum avant tout import.
4. Implémenter l'import : parsing, quarantaine motivée, conservation intégrale des identifiants
   sources, rattachement aux entités canoniques existantes.
5. Distinguer explicitement un **groupe BDNB** d'un **bâtiment physique** — le contrat l'impose déjà,
   l'import doit le matérialiser et non aplatir la cardinalité.
6. Exclure toute valeur BDNB Expert, simulée ou prédite. Seules les valeurs Open observées, avec
   leur producteur et leur champ source, sont admises.
7. Empêcher le double comptage : une valeur BDNB recopiée d'une source primaire déjà importée ne
   doit compter qu'une fois dans les features.
8. Produire le rapport d'acceptation et prononcer un verdict.

## Tests obligatoires

- un groupe BDNB couvrant plusieurs bâtiments physiques n'est jamais réduit à un bâtiment ;
- une valeur Expert ou prédite présente dans le fichier est rejetée avec motif, pas ignorée ;
- une valeur dupliquée depuis une source primaire déjà importée ne contribue qu'une fois ;
- réimport stable : identifiants internes inchangés ;
- une feature exigeant DS-03 reste absente avec le motif `source_not_accepted` tant que la release
  n'est pas acceptée.

## Critères d'acceptation

- release réelle, immuable, checksumée et enregistrée au catalogue ;
- aucun identifiant source écrasé ;
- verdict documenté, `accepted` / `rejected` / `display_only` ;
- taux d'appariement mesuré par commune ;
- les identifiants BDNB issus du RNB restent typés comme références externes et n'ont pas été
  promus en observations.

## Preuves à produire

- manifeste `contracts/datasets/DS-03/releases/<release>-35.json` ;
- section DS-03 de [`spatial-sources-audit.md`](../data/spatial-sources-audit.md) mise à jour ;
- rapport de distribution intégré à [B3](./B3-rapport-appariements.md).
