# D2 — DS-08 GPU : zonage et contraintes, sans interprétation de règlement

**Version :** v0.5 · **Taille :** M · **État :** À faire
**Dépend de :** D1 · **Bloque :** D5

## Contexte à charger

- `contracts/datasets/DS-08/v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md` (§DS-08)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Verdict actuel : « rejeté pour publication — documents opposables et profils validés absents ».
Les garde-fous sont testés sur fixtures ; il manque les documents réels.

**Interdit structurant :** aucune interprétation automatique libre du texte des règlements PLU. Le
produit ne rend pas de décision urbanistique opposable. Ce qui est importé, ce sont des documents,
des zones et des contraintes **structurées**, jamais une lecture de texte.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Une zone chevauchante sans gagnant clair rend le zonage inutilisable sans invalider la parcelle.

## Ce que l'exploration de l'API a établi — 14 septembre 2026

L'API GPU est accessible et documentée : sa spécification est servie en YAML à
`/api/swagger.yaml`, et non aux emplacements habituels. Quatre points changent la conception du
ticket.

### La couverture communale est partielle, et l'hétérogénéité est réelle

| Sur le territoire `35`, en production | Documents |
|---|---:|
| PLU communaux | 164 |
| Cartes communales | 14 |
| Servitudes d'utilité publique | 9 |
| PSMV | 1 |
| **Documents d'urbanisme communaux** | **178**, couvrant **179 communes** |

Auxquels s'ajoutent **6 PLUi** couvrant **123 communes** du département — invisibles d'une requête
départementale, voir ci-dessous.

| Couverture réelle | Communes | Part |
|---|---:|---:|
| Document communal propre | 179 | 53,9 % |
| Couvertes par un PLUi | 123 | 37,0 % |
| Les deux — Rennes, PSMV et PLUi | 1 | — |
| **Couvertes au total** | **301** | **90,7 %** |
| **Sans document, donc au RNU** | **31** | **9,3 %** |

Rennes cumule un **PSMV**, approuvé le 22 février 2024, et le PLUi de Rennes Métropole. Ce n'est
pas une ambiguïté à arbitrer : un PSMV est un instrument distinct qui se substitue au PLU dans son
périmètre. C'est exactement l'hétérogénéité que le ticket demande de modéliser plutôt que
d'aplatir, et le modèle doit porter les deux.

### Les PLUi sont invisibles d'une requête départementale

Un PLUi porte le **SIREN de l'EPCI** comme code de territoire, pas un code commençant par `35`.
`territory=35` ne les retourne donc pas, et `territory=<code commune>` ne retourne rien non plus :
le filtre porte sur le code du territoire du document, jamais sur « couvre cette commune ».

Rennes Métropole est `DU_243500139`, PLUi `APPROVED` et `EN_VIGUEUR`, publié le 13 février 2026.
Il n'apparaît dans aucune requête départementale.

**Conséquence de conception : le rattachement doit être spatial, pas administratif.** Ce n'est pas
un pis-aller — le point 4 du ticket le demandait déjà, et cela évite d'avoir à importer une
correspondance EPCI ↔ communes qui serait une source de plus.

### Six PLUi sur vingt-trois candidats, tranchés par `DOC_URBA_COM`

La lecture partielle des archives a permis de vérifier chaque candidat sans en télécharger aucun :
on lit `DOC_URBA_COM`, quelques kilo-octets, au lieu de rapatrier 36,9 Go.

| PLUi | Communes | dont dans le 35 |
|---|---:|---:|
| Rennes Métropole | 43 | **43** |
| Bretagne Romantique | 25 | **25** |
| Bretagne Porte de Loire Communauté | 20 | **20** |
| Val d'Ille-Aubigné | 19 | **19** |
| Couesnon Marches de Bretagne | 8 | **8** |
| Brocéliande | 8 | **8** |

Dix-sept candidats sont écartés : leur emprise touche le département, aucune de leurs communes n'y
est. La `bbox` était bien un pré-filtre et rien de plus.

### La casse des noms de champs CNIG varie d'un document à l'autre

**Ce piège a failli faire disparaître Rennes Métropole de l'import.** Le PLU communal écrit ses
champs en majuscules — `INSEE`, `IDURBA` — et le PLUi de Rennes Métropole en minuscules —
`insee`, `idurba`. Une lecture sensible à la casse retourne une chaîne vide sans lever d'erreur,
et le document paraît alors ne couvrir aucune commune.

Le symptôme était invraisemblable — « Rennes Métropole couvre une commune, hors du 35 » — et c'est
la seule raison pour laquelle il a été vu. Un document moins notoire serait passé inaperçu.

**Toute lecture d'attribut CNIG doit donc être insensible à la casse, et un test doit le
garantir.**

### Repérer les PLUi candidats par leur emprise, puis trancher par la géométrie

Chaque document expose une `bbox`. Sur les 565 PLUi en production en France, **23** ont une emprise
qui touche celle du 35. La liste contient des voisins légitimes — Dinan Agglomération,
Mont-Saint-Michel-Normandie, Couesnon Marches de Bretagne — et au moins une aberration :
« PLUI DE PUISAYE-FORTERRE », dans l'Yonne. Une `bbox` fausse existe donc dans la source.

La `bbox` est donc un **pré-filtre**, jamais un critère : seule l'intersection réelle des zones
avec nos parcelles décide. C'est aussi ce qui rend l'aberration inoffensive.

### L'API impose ses formes

- les paramètres à valeurs multiples veulent une syntaxe de tableau — `documentFamily[]=DU` —
  et un `documentFamily=DU` échoue en 400 avec « cette valeur doit être de type array|null » ;
- `limit` est borné à 1000 ;
- `/document/{id}/details` **ne liste pas les communes couvertes**, ce qui confirme le
  rattachement spatial ;
- `/document/{id}/download` fournit l'archive CNIG, et `/document/{id}/files` les pièces écrites.

### L'archive CNIG et la correspondance avec nos tables

Une archive par document, servie par `/document/{id}/download`. Sur `DU_35018`, un PLU communal :
**33,5 Mo**, dont seulement **1,7 Mo de données structurées** — le reste est le règlement, le PADD
et les orientations d'aménagement, en PDF. Ce sont exactement les pièces que D2 n'a pas le droit
d'interpréter, et celles que l'humain de [D2b](./D2b-profils-de-regles.md) lira.

Les couches sont en **Lambert-93**, notre SRID canonique : aucune reprojection.

| Couche CNIG | Champs utiles | Table cible |
|---|---|---|
| `DOC_URBA` | `IDURBA`, `TYPEDOC`, `DATAPPRO`, `DATEFIN`, `ETAT`, `SIREN`, `INTERCO` | `observation.urban_document` |
| `DOC_URBA_COM` | `IDURBA` → `INSEE` | `urban_document.commune_codes` |
| `ZONE_URBA` | `LIBELLE`, `LIBELONG`, `TYPEZONE`, `DESTDOMI`, `DATAPPRO`, `DATVALID` | `observation.urban_zone` |
| `PRESCRIPTION_SURF`, `PRESCRIPTION_LIN` | `TYPEPSC`, `LIBELLE` | `observation.urban_constraint` |
| `INFO_SURF` | `TYPEINF`, `LIBELLE` | information, **non opposable** — à ne pas confondre avec une prescription |

**`DOC_URBA_COM` résout le rattachement d'un PLUi à ses communes** sans importer de correspondance
EPCI ↔ communes : la donnée est dans l'archive. Le rattachement spatial aux parcelles reste
nécessaire et reste la référence, mais la liste administrative est désormais disponible pour le
contrôler.

`IDURBA` — par exemple `35018_20161215` — porte la **version exacte** du document. C'est la clé du
risque déclaré de la v0.5, et elle vient de la source.

### Le schéma confirme la scission

`observation.urban_zone` porte déjà, et séparément, `rule_profile`, `rule_profile_version`,
`rule_profile_validated_at`, `rule_profile_validated_by`, `required_rule_count` et
`validated_rule_count`. Ces colonnes sont nullables et vides tant que D2b n'a rien validé, et les
deux dernières **sont** `URB-005`.

Le modèle avait donc prévu dès l'origine que l'import et la validation humaine soient deux gestes
distincts. La scission du 14 septembre ne fait que l'expliciter dans le backlog.

### Ce qu'on archive, et ce dont on garde seulement la trace

**Pourquoi archiver.** L'amont bouge sous nos pieds : c'est la leçon de
[BUG-05](./BUG-05-ds02-rnb-non-reproductible.md), où une URL épinglée était un alias mouvant et le
checksum a sauté à la première relance. Ici c'est plus net encore — le GPU **supprime** des
documents, et une requête sans filtre de statut en retourne vingt, tous en `document.deleted`.
Or [E3](./E3-publier-snapshots.md) exige qu'un score publié reste explicable et reproductible
après changement de millésime : si le document disparaît, l'import qui a produit le score n'est
plus rejouable.

**Pourquoi pas tout.** 95 % du volume sont des pièces écrites qu'il est interdit d'interpréter
ici. Et elles restent atteignables à l'unité : `/document/{id}/files` les liste,
`/document/{id}/files/{nom}` les sert, et `ZONE_URBA.URLFIC` nomme le règlement applicable à
chaque zone.

| | Par document | Le 35 | La Bretagne | La France |
|---|---:|---:|---:|---:|
| Archive complète | 33,5 Mo | ~6 Go | ~24 Go | ~430 Go |
| **Couches structurées seules** | **1,7 Mo** | **~340 Mo** | **~1,4 Go** | **~22 Go** |

**Décision du 14 septembre 2026.**

- archiver les **couches structurées**, celles qui sont réellement importées, chacune avec son
  empreinte ;
- relever le **SHA-256 de l'archive complète** au manifeste, pour la provenance, sans la stocker ;
- laisser [D2b](./D2b-profils-de-regles.md) archiver les pièces écrites des quelques dizaines de
  documents qu'il validera.

Le principe tient en une phrase : **on archive ce qu'on importe, on checksume ce qu'on archive, et
de ce qu'on n'importe pas on garde la trace plutôt que les octets.**

**Le risque assumé, écrit pour qu'il ne soit pas découvert plus tard.** Si le GPU supprime un
document, nous gardons de quoi rejouer l'import et expliquer le score, mais nous perdons la
possibilité de relire le règlement. Pour les communes qui portent un candidat, D2b aura archivé
les pièces ; pour les autres, elles n'étaient pas nécessaires.

### Une dépendance ajoutée : `pyshp`

Les couches CNIG sont des shapefiles. Le dépôt évite GDAL par principe — la lecture GeoPackage
passe par `sqlite3` et `shapely`. `pyshp` est l'équivalent minimal pour le shapefile : pur Python,
sans binaire à installer, et il n'introduit aucune dépendance système.

## Travail à réaliser

1. Identifier et épingler les documents : **178 communaux** par `territory=35`, plus les PLUi
   dont l'emprise touche le département — **23 candidats**, à confirmer par intersection
   réelle des zones avec nos parcelles et non par leur `bbox`.
2. Archiver les **couches structurées** de chaque document, chacune avec son checksum, et relever au manifeste l'empreinte de l'archive complète sans la stocker — voir la décision ci-dessus. Le périmètre est hétérogène : certaines communes
   relèvent d'un PLUi, d'autres d'un PLU, d'autres d'une carte communale ou du RNU. Cette
   hétérogénéité doit être modélisée, pas aplatie.
3. Importer `UrbanDocument`, `UrbanZone`, `UrbanConstraint` en conservant l'identifiant CNIG.
4. Rattacher les zones aux parcelles du référentiel spatial, avec gestion explicite des
   chevauchements.
5. Publier la couverture : combien de communes disposent d'un document opposable importé, combien
   relèvent d'un PLUi, combien restent sans donnée — donc au RNU.
6. Calculer `URB-005` **complétude des règles**, qui vaut zéro partout tant que
   [D2b](./D2b-profils-de-regles.md) n'a rien validé. C'est un résultat, pas un échec : la feature
   existe pour dire à quel point l'interprétation réglementaire est incomplète.

## Ce que ce ticket livre, et ce qu'il ne livre pas

| Feature | Formule | Ce ticket |
|---|---|---|
| `URB-001` code de zone | recouvrement représentatif avec la zone opposable | **livrée** |
| `URB-003` contraintes connues | comptage typé et aire d'intersection | **livrée** |
| `URB-005` complétude des règles | règles validées / règles requises | **livrée**, à zéro |
| `URB-002` profil de règles | profil structuré validé manuellement | [D2b](./D2b-profils-de-regles.md) |
| `URB-004` emprise résiduelle | après toutes les règles indispensables validées | [D2b](./D2b-profils-de-regles.md) |

### Pourquoi la scission — arbitrage du 14 septembre 2026

Le ticket portait les cinq features, dont deux exigent qu'un humain lise un règlement et en
structure les règles. Mesuré sur l'API GPU : **12 795 documents d'urbanisme** en production en
France — 9 463 PLU, 2 723 cartes communales, 565 PLUi, 42 PSMV, 2 POS. À trente minutes par
document, ce qui est optimiste, cela représente près de **quatre années-personne**. La Bretagne
seule en demanderait une dizaine de semaines, le 35 environ deux et demie.

Aucune astuce ne réduit ce coût, puisque l'interprétation automatique du texte est interdite ici
et le restera.

Mais **trois features sur cinq n'en dépendent pas** : le zonage et les contraintes se rattachent
spatialement, sans lire une ligne de règlement. La validation n'est donc pas un prérequis de
l'import, c'est un **enrichissement** — et `URB-005` existe précisément pour publier à quel point
il manque.

Surtout, l'ordre de travail s'inverse. Valider 12 795 règlements avant de savoir quelles communes
portent des candidats, c'est travailler à l'envers : le produit **classe**, et on ne valide un
règlement que là où un candidat émerge. Quelques dizaines de communes, pas douze mille documents.
D'où D2b, après [E3](./E3-publier-snapshots.md).

## Points de vigilance

- **Risque déclaré :** appliquer un profil PLU à une mauvaise version du document. Le modèle doit
  porter la version exacte dès cet import, même si aucun profil n'existe encore — sinon
  [D2b](./D2b-profils-de-regles.md) n'aura rien à quoi s'accrocher.
- Un document périmé à la date du snapshot est inutilisable : la zone reste absente avec motif.
- Un chevauchement matériel sans gagnant clair est ambigu, pas arbitré.
- Une zone GPU ne dit pas ce qui est constructible en pratique. Les features URB expriment un
  contexte réglementaire observé, jamais une autorisation.

## Tests obligatoires

- document non publié ou non opposable : refusé ;
- document périmé à la date du snapshot : zone absente avec motif ;
- zonage absent ou sans zone représentative : absent avec motif ;
- chevauchement sans gagnant clair : ambigu ;
- profil de règles non validé pour la version exacte : `URB-004` non calculé ;
- aucun texte libre interprété.

## Critères d'acceptation

- documents réels importés, versionnés et checksumés ;
- couverture publiée par commune, avec les communes sans document identifiées comme non couvertes ;
- profils de règles validés et rattachés à une version exacte ;
- verdict documenté ;
- distributions URB disponibles pour [E1](./E1-profiling-distributions.md).

## Preuves à produire

- manifestes `contracts/datasets/DS-08/releases/…` ;
- section DS-08 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/gpu-coverage-35.md`.
