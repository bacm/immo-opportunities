# Audit des sources du référentiel spatial

**Périmètre :** département 35  
**Date de l'audit :** 5 août 2026  
**Statut :** en cours — DS-02 et DS-05 sont épinglées ; DS-03 et DS-04 ne sont pas encore
acceptables faute de manifeste réel importé et contrôlé.

## Décision par source

| Source | Release retenue | Archive immuable | Import réel | Décision |
|---|---|---:|---:|---|
| DS-02 RNB | `2026-09-05`, département 35 | oui | oui | ré-épinglée le 7 septembre 2026, volumétries à re-mesurer par B3 |
| DS-03 BDNB Open | `2026-02-a`, département 35 | oui | oui | **`display_only`** — critère d'appariement déclaré et corroboré, bloqué par DS-02 non acceptée |
| DS-04 BD TOPO | `2026-06-15`, département 35 | oui | oui | **`display_only`** — bâtiments et voirie exploitables, seuils d'appariement géométrique non calibrés |
| DS-05 BAN | `2026-06-17`, département 35 | oui | oui | **`display_only`** — adresses exploitables, relations parcellaires non calibrées |

Une URL `latest` ne constitue jamais une release. Le manifeste versionné doit contenir l'URL
résolue, la taille et le SHA-256 avant qu'un import puisse être accepté.

## DS-02 — Référentiel National des Bâtiments

- catalogue officiel : <https://www.data.gouv.fr/datasets/referentiel-national-des-batiments> ;
- licence déclarée : Licence Ouverte 2.0 ;
- format observé : ZIP contenant un CSV séparé par `;` ;
- colonnes observées : `rnb_id`, `point`, `shape`, `status`, `ext_ids`, `addresses`, `plots`,
  `validated_by`.

### Ré-épinglage du 7 septembre 2026 — le RNB n'a pas de millésime

La release `2026-08-01` a été **retirée** : ses octets sont irrécupérables. L'URL épinglée,
`files/RNB_35.csv.zip`, n'est pas datée — le producteur écrase l'objet sur place. Mesures :

| Relevé | Taille | `last-modified` |
|---|---:|---|
| Manifeste `2026-08-01` | 190 932 054 | — |
| 4 septembre 2026 | 191 011 813 | 29 août 2026 |
| 7 septembre 2026 | 191 084 366 | 5 septembre 2026 |

Le fichier a changé deux fois en dix jours. Le listing `?versions` du bucket ne renvoie **qu'une
seule version**, et le bucket n'expose aucun objet daté. Le RNB est une base continûment mise à
jour, non une suite de millésimes : aucune date de publication amont n'existe, et
`DS-02@2026-08-01` nommait en réalité le jour de notre téléchargement.

Le contrat en tire les conséquences : `key_format` devient « last-modified de l'objet source »,
ce qui rend la clé indépendante de l'opérateur — deux personnes archivant les mêmes octets
dérivent la même clé — et `archived_copy_required` est désormais vrai.

Release courante :

- archive retenue : objet servi le 5 septembre 2026, archivé le 7 ;
- taille : 191 084 366 octets ;
- SHA-256 : `becfb525c771fc7bbae1f7a4318a907d19c7ac87be6a8d6478fff93c311b89a6` ;
- SHA-1 publié par data.gouv.fr : `ba0fe9971d4bec407af8451920ffbde4b63dc0bf`, **vérifié
  conforme**. Comme le MD5 de l'IGN pour DS-04, il sert de contrôle de transfert : il suit
  l'objet mouvant et ne constitue pas un épinglage ;
- copie archivée nommée au manifeste :
  `DS-02/2026-09-05/department/35/buildings/becfb525….csv.zip`.

C'est cette copie, et non l'URL, qui porte la reproductibilité. Le manifeste la nomme désormais
explicitement : avant, le chemin vers l'archive n'existait que dans `meta.raw_asset`, donc une
base reconstituée n'avait aucun retour possible. Voir
[BUG-05](../backlog/BUG-05-ds02-rnb-non-reproductible.md).

**Portée de la correction.** Elle ne rend pas le dépôt seul suffisant : sur une plateforme dont
MinIO n'a pas été restauré, DS-02 n'est réimportable que tant que le producteur sert encore les
mêmes octets. La sauvegarde de `raw-sources` est ce qui porte la garantie dans le temps.

**Import rejoué de bout en bout le 7 septembre 2026.** Sur base propre, cadastre
`DS-01@2026-06-01` publié : 741 379 lignes lues, 741 379 normalisées, 0 en quarantaine,
1 240 355 relations bâtiment–parcelle toutes `certain`. L'archive a été déposée sous la clé exacte
que nomme le manifeste, et un import ultérieur la retrouve sans dépendre de l'amont.

**Ce que le ré-épinglage invalide.** Les 741 376 bâtiments et 1 240 351 relations
bâtiment–parcelle du [rapport spatial 35](./spatial-reference-35-report.md) portaient sur les
octets du 1er août. L'écart est faible — 3 bâtiments et 4 relations de plus — mais réel : les
chiffres publiés ne décrivent plus la release active. Ils sont à re-mesurer sur la nouvelle release — travail de
[B3](../backlog/B3-rapport-appariements.md). Le verdict `display_only` de DS-05 n'est en revanche
pas affecté : ses relations se résolvent contre la géométrie cadastrale DS-01, et le volet
adresse↔bâtiment est une jointure qui ne produit rien en l'absence d'observations DS-02, sans
échouer.

Le RNB fournit l'identité bâtiment préférée. Une géométrie ponctuelle crée une identité stable mais
ne devient jamais une emprise inventée. Les identifiants BDNB et BD TOPO présents dans `ext_ids`
sont conservés comme identifiants externes observés via DS-02 ; ils ne valent pas import ni
acceptation de DS-03 ou DS-04. Les relations `plots` conservent leur taux de couverture et leur
provenance.

## DS-03 — BDNB Open

- catalogue officiel : <https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments> ;
- documentation du modèle : <https://bdnb.io/documentation/modele_donnees/> ;
- millésime courant : `2026-02-a`, modèle de données v0.7.10.

Le contrat distingue explicitement un groupe BDNB d'un bâtiment physique. Seules les valeurs
Open observées, accompagnées de leur producteur et de leur champ source, sont admises. Les champs
Expert, simulés ou prédits restent exclus. Une copie BDNB d'une valeur issue d'une source primaire
ne doit pas être comptée deux fois.

### La décision d'origine n'avait pas lieu d'être — 7 septembre 2026

L'audit du 5 août affirmait que « le millésime courant est distribué en export national
volumineux ; il n'est pas épinglé tant que son découpage et son checksum ne sont pas
reproductibles localement », et [B2a](../backlog/B2a-import-bdnb-ds03.md) en tirait un arbitrage
entre fraîcheur et reproductibilité. **Cette prémisse est fausse.**

Le producteur publie, pour le millésime courant, un **export départemental daté**, listé sur la
page du millésime et absent du catalogue data.gouv — qui ne référence que les exports France
entière (39 Go en CSV, 51 Go en GeoPackage). Il publie de surcroît un SHA-256 dans un fichier
`_metadata.yml` voisin de l'archive.

| | GeoPackage retenu | CSV compagnon |
|---|---:|---:|
| Taille | 804 719 036 | 619 682 182 |
| SHA-256 publié par le CSTB | `eea296e0…18c9` | `a2f50054…b28f6` |
| Vérifié conforme | oui | oui |

Le CSTB est le premier producteur du dépôt à publier un SHA-256 de son propre asset : DS-04 ne
donne qu'un MD5, DS-02 qu'un SHA-1 via data.gouv. Aucun découpage local n'est en jeu, donc rien
dans cette release ne dépend d'une procédure de notre côté. Il n'y a **aucun arbitrage à rendre**.

Manifeste : [`contracts/datasets/DS-03/releases/2026-02-a-35.json`](../../contracts/datasets/DS-03/releases/2026-02-a-35.json).
Le GeoPackage est retenu conformément au `preferred_format` du contrat ; le CSV est archivé comme
pièce d'audit de la politique de champs, sans être importé.

### Le modèle, mesuré sur l'archive épinglée

| Table | Lignes | Rôle |
|---|---:|---|
| `batiment_groupe_compile` | 546 301 | le **groupe** BDNB, avec sa géométrie |
| `batiment_construction` | 783 684 | le **bâtiment physique**, avec sa géométrie et sa hauteur |
| `rel_batiment_construction_rnb` | 726 364 | rattachement au RNB, au niveau construction |

La distinction que le contrat exige de ne pas aplatir est donc portée par la source elle-même :
546 301 groupes pour 783 684 constructions physiques. Le rattachement au RNB se fait au niveau
**construction**, pas groupe — c'est la cardinalité à respecter.

`rel_batiment_construction_rnb` est déclarée `expérimental` par le producteur et porte son propre
`type_appariement`. Même statut que `cad_parcelles` pour la BAN : une relation source à conserver
avec son type déclaré, jamais à promouvoir en certaine sans calibration.

### La politique de champs a une base objective

L'archive embarque le dictionnaire du producteur, `metadonnees_colonne`, qui déclare pour chacune
des 1 888 colonnes du modèle son régime d'accès :

| `contrainte_acces` | Colonnes |
|---|---:|
| `open_data_lo` | 758 |
| `ayant_droit_bdnb_expert` | 373 |
| `ayant_droit_ffo` / `ayant_droit_ffo_expert` | 426 |
| `ayant_droit_simulation_dpe` | 141 |
| `ayant_droit_dv3f` / `simulation_dvf` | 100 |
| autres droits (rpls, valeur verte, pie, bruit) | 90 |

**Vérification faite : l'export départemental ne contient aucune colonne `ayant_droit_*`.** Les
56 tables du CSV et les 33 du GeoPackage n'exposent que des colonnes `open_data_lo`. Le contrôle
bloquant `expert_fields_excluded` du contrat est donc vérifiable automatiquement, contre le
dictionnaire livré dans l'archive elle-même — et non contre une liste que nous aurions rédigée.

Le dictionnaire signale aussi 189 colonnes `expérimental` et 60 `déprécié` parmi les colonnes
ouvertes : le statut doit accompagner la valeur, il ne suffit pas de savoir qu'elle est ouverte.

### Ce que « ouvert » ne suffit pas à autoriser

Trois ensembles sont déclarés `open_data_lo` par le producteur et restent néanmoins à écarter,
pour des raisons qui tiennent au périmètre produit et non à la licence :

- **`proprietaire` et `rel_batiment_groupe_proprietaire`** portent `denomination`, `siren`,
  `forme_juridique`, `code_postal` et un `personne_id` MAJIC. C'est de la donnée de propriétaire,
  que le périmètre produit exclut explicitement, et que le contrat DS-03 déclare lui-même absente
  (`personal_data: false`). À ne pas importer.
- **`batiment_groupe_contrainte_opportunite_renovation`** — malgré son nom, 10 indicateurs
  `batenr_*` de potentiel géothermique et solaire. Valeurs modélisées, non observées, et hors des
  deux stratégies du produit.
- **`batiment_groupe_synthese_propriete_usage`** — un indicateur d'usage recalculé par la BDNB.
  L'usage observé existe par ailleurs, déclaré, dans `batiment_groupe_ffo_bat`.

### Le double comptage, table par table

Sur les 293 colonnes de la vue compilée, la majorité recopie des sources primaires que le projet
importe pour son propre compte :

| Thème dans la vue compilée | Colonnes | Source primaire |
|---|---:|---|
| `dpe_*` | 149 | DS-07 |
| `dvf_*` | 34 | DS-06 |
| `bdtopo_*` | 13 | DS-04, **déjà importée** |
| `rpls_*`, `rnc_*`, `hthd_*`, autres | 44 | hors périmètre MVP |
| `ffo_*` | 6 | **apport propre de la BDNB** |
| structure et géométrie | 37 | — |

Seules 6 colonnes `ffo_*` constituent un apport que nulle autre source du MVP ne fournit.

### Import réel du 7 septembre 2026

546 301 groupes lus, 546 301 normalisés, **0 en quarantaine**. Le contrôle bloquant
`expert_fields_excluded` est au vert : 1 888 colonnes documentées inspectées sur 33 tables,
aucune colonne `ayant_droit_*`.

Périmètre importé, conforme au contrat qui ne définit que deux couches — `building_groups` vers
les observations et `source_relations` vers les appariements :

- le **groupe** BDNB comme observation, avec sa géométrie et les six champs `ffo_*` ;
- le pont groupe → construction → RNB comme relation source.

`batiment_construction` n'est traversée que pour sa clé. Sa géométrie et sa hauteur sont
documentées `(ign)` par le producteur : **le niveau « bâtiment physique » de la BDNB est la
BD TOPO**, que DS-04 fournit nativement. Les importer aurait été un doublon, pas un apport.

| Décision | Groupes | Liens | Bâtiments visés |
|---|---:|---:|---:|
| certain | 422 194 | 422 194 | 422 194 |
| ambigu | 104 823 | 303 219 | 300 309 |
| rejeté | 0 | 0 | 0 |
| non apparié | 19 284 | — | — |

Distribution identique sur les 332 communes du 35. Remplissage des champs propres :
376 206 groupes portent une année de construction, 391 416 un nombre de niveaux et de logements.
2 613 géométries sont déclarées fictives par le producteur ; elles sont conservées **étiquetées**,
jamais présentées comme relevées.

### La règle de décision, et pourquoi elle ne repose sur aucun seuil inventé

Un rattachement n'est `certain` que si deux conditions se cumulent : le groupe se résout en un
**unique** bâtiment RNB, et **toutes** les relations construction ↔ RNB qui y contribuent portent
le type `Alignement 1 BC = 1 RNB, recouvrement géométrique ≥ 95 %`.

Ce type n'est pas une confiance opaque : le producteur **énonce son critère**. Sa distribution sur
les 726 364 relations :

| Type déclaré | Relations |
|---|---:|
| Alignement 1 BC = 1 RNB, recouvrement ≥ 95 % | 700 985 |
| Association 1 RNB pour 1 BC, surfaces divergentes | 8 246 |
| Scission de BC, recouvrement ≥ 95 % | 7 285 |
| Fusion de BC, recouvrement ≥ 95 % | 4 687 |
| Recouvrement partiel du BC par un RNB | 1 815 |
| Géométrie BC fictive, correspondance RNB ponctuelle | 1 692 |
| Recouvrement partiel par plusieurs RNB | 1 654 |

C'est ce qui distingue DS-03 de DS-05 : les paliers 0,99 / 0,95 / 0,80 et la frontière de 10 m de
la BAN étaient **les nôtres et sans mesure**. Ici le seuil est celui du producteur, il est publié
avec la donnée, et nous l'avons vérifié.

**Un groupe couvrant plusieurs bâtiments n'est jamais réduit à l'un d'eux.** Les 104 823 groupes
concernés produisent 303 219 liens, tous ambigus, portant le motif « ses attributs de niveau
groupe n'appartiennent à aucun d'eux en particulier ». Ne rien choisir est la seule réponse juste :
choisir serait arbitraire, attribuer à tous compterait plusieurs fois.

### Vérification de l'affirmation du producteur — et sa limite

Recouvrement mesuré entre géométrie de groupe et emprise RNB, sur **la totalité** des
422 194 rattachements certains — pas sur un échantillon :

| | Valeur |
|---|---:|
| Médiane | 1,0000 |
| 5e percentile | 1,0000 |
| Moyenne | 0,9890 |
| Au moins 95 % | 406 950 / 422 194 — **96,4 %** |
| Sous 50 % | 2 294 — 0,54 % |

L'écart résiduel s'explique entièrement, et n'infirme pas l'appariement :

| Classe de recouvrement | Cas | Surface groupe / surface bâtiment |
|---|---:|---:|
| ≥ 95 % | 406 950 | 1,000 |
| 50 à 95 % | 12 950 | 1,371 |
| < 50 % | 2 294 | 2,721 |

Le groupe est simplement plus vaste que le bâtiment auquel il se rattache — il englobe des
constructions sans lien RNB. Le rattachement reste juste ; c'est l'étendue de l'attribut qui
diffère de celle du bâtiment.

**La limite est réelle et assumée :** le producteur affirme un recouvrement au niveau
*construction*, et nous mesurons au niveau *groupe*, faute de détenir la géométrie des
constructions — que nous avons écartée comme doublon de DS-04. Vérifier l'affirmation à son propre
niveau exigerait d'importer ce que nous avons délibérément exclu.

**Conséquence persistée pour [B5](../backlog/B5-features-morphologiques.md).** Chaque lien certain
porte désormais dans sa preuve `group_building_overlap_ratio` et
`group_area_over_building_area`. Même certain, un attribut de groupe peut décrire plus que son
bâtiment : sans ce garde-fou, un `nb_log` de groupe surcompterait en silence sur les
11 384 cas — 2,7 % — où le groupe dépasse le bâtiment de plus de 20 %. Le calcul des features doit filtrer là-dessus, et non faire confiance au seul statut
`certain`.

### Le double comptage, écarté à l'import et non au calcul

Le contrat prévoit qu'« une valeur primaire supplante sa copie BDNB au calcul des features ». Nous
avons choisi de ne pas importer les copies du tout, parce que la déduplication au calcul serait
restée théorique : DS-07 n'existe pas encore, donc les 149 colonnes DPE de la BDNB auraient été
de fait la seule source DPE disponible, donc utilisées — exactement ce que le contrat veut
empêcher.

| Thème écarté | Colonnes | Motif |
|---|---:|---|
| `dpe_*` | 149 | copie de DS-07 |
| `dvf_*` | 34 | copie de DS-06 |
| `bdtopo_*` | 13 | copie de DS-04, déjà importée |
| `rpls_*`, `rnc_*`, `hthd_*`, autres | 44 | hors périmètre MVP |

Trois ensembles sont pourtant déclarés `open_data_lo` et restent écartés pour des raisons de
périmètre produit, non de licence : les tables `proprietaire` et `rel_batiment_groupe_proprietaire`
(donnée de propriétaire, que le contrat DS-03 déclare lui-même absente),
`batiment_groupe_contrainte_opportunite_renovation` (10 indicateurs `batenr_*` de potentiel
géothermique et solaire, modélisés) et `batiment_groupe_synthese_propriete_usage` (usage recalculé
par la BDNB, alors que l'usage déclaré existe dans `ffo_bat`).

### Verdict du 7 septembre 2026 — `display_only`

**Ce qui est acquis.** La release est reproductible et vérifiée par le SHA-256 du producteur.
L'import est intégralement normalisé, sans quarantaine. La cardinalité groupe / bâtiment physique
est respectée et non aplatie. Le critère d'appariement est déclaré par la source, sa distribution
est mesurée, et nous l'avons corroboré à 96,4 % sur la population entière, médiane à 1,0000. Les six champs `ffo_*`
apportent ce que nulle autre source du MVP ne fournit : l'année de construction et le nombre de
niveaux, sur respectivement 376 206 et 391 416 groupes.

**Ce qui bloque, et ce n'est pas la qualité de DS-03.** Les 422 194 rattachements certains
désignent des bâtiments dont l'identité vient du RNB — et `DS-02@2026-09-05` n'est pas acceptée :
elle attend la revue manuelle de [B4](../backlog/B4-revue-manuelle-appariements.md). Faire entrer
DS-03 dans le périmètre d'analyse pendant que l'identité à laquelle elle s'accroche n'y est pas
serait incohérent.

D'où le verdict, **pour un motif différent de DS-04 et DS-05** : ceux-là attendent la calibration
de leurs propres seuils, DS-03 attend seulement l'acceptation de son support d'identité. À la
clôture de B4, DS-03 est la release la mieux placée pour devenir la première `accepted` au-delà du
cadastre.

## DS-04 — BD TOPO

- catalogue officiel : <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-TOPO> ;
- licence déclarée : Licence Ouverte 2.0 ;
- couches attendues : `BATIMENT` et `TRONCON_DE_ROUTE`.

Le téléchargement dynamique ou le WFS peuvent servir à découvrir la donnée, mais ne satisfont
pas seuls la reproductibilité. La release restera inactive jusqu'à archivage d'un export exact.
Les bâtiments légers et la voirie restent donc des valeurs manquantes, jamais des zéros.

### Release résolue le 4 septembre 2026

L'export départemental daté existe et a été épinglé. Il est découvert par le flux Atom du
Géoplateforme, `resource/BDTOPO?zone=D035`, qui liste 31 éditions du 35 depuis 2008 ; la plus
récente au format GeoPackage Lambert-93 a été retenue.

- édition : `BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15` ;
- URL résolue, datée, sans alias :
  <https://data.geopf.fr/telechargement/download/BDTOPO/BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15/BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15.7z> ;
- taille : 528 975 501 octets ;
- SHA-256 : `0d06d6e76f1ca0131e7bb228d9e1aa387001f77a1442f06481fe4a66002c559e` ;
- MD5 publié par le producteur : `4cff570dfdf9a665e7984e516c56dd6d`, **vérifié conforme** au
  téléchargement. Le producteur ne publie pas de SHA-256 : le MD5 amont sert de contrôle de
  transfert, le SHA-256 mesuré localement est le checksum du contrat.

Manifeste : [`contracts/datasets/DS-04/releases/2026-06-15-35.json`](../../contracts/datasets/DS-04/releases/2026-06-15-35.json).

L'archive `7z` contient un GeoPackage unique de 3 085 385 728 octets, soit 55 tables. Le format
`7z` est nouveau dans le dépôt : aucune source déjà importée ne l'utilise, et ni l'image
`docker/pipelines` ni l'environnement local ne savent le lire aujourd'hui.

### Ce que contient réellement l'export — mesuré sur l'archive épinglée

| Table | Enregistrements | Identifiants `cleabs` distincts | Géométrie nulle |
|---|---:|---:|---:|
| `batiment` | 974 172 | 974 172 | 0 |
| `troncon_de_route` | 391 217 | 391 217 | 0 |
| `batiment_rnb_lien_bdtopo` | 957 009 | — | 0 |

**L'export n'est pas découpé au département.** Il déborde sur les départements limitrophes :

| Périmètre | Communes de la table `commune` | Tronçons (`insee_commune_gauche`) |
|---|---:|---:|
| 35 | 332 | 323 251 |
| 53, 22, 56, 50, 44, 49 | 143 | 63 366 |
| non renseigné | — | 4 598 |

Les 974 172 bâtiments ne sont donc **pas** le compte du 35. Toute volumétrie départementale devra
être établie après résolution spatiale de la commune contre la release DS-01 active, et les objets
hors département comptés explicitement, jamais écartés en silence.

### L'appariement au RNB est fourni par la source, il n'est pas à reconstruire

C'est le fait le plus structurant de cet audit. L'export transporte l'identifiant RNB officiel :

- `batiment.identifiants_rnb` est renseigné pour 939 818 bâtiments sur 974 172, soit **96,5 %** ;
- 29 236 bâtiments portent plusieurs identifiants RNB, séparés par `/` ;
- 34 354 bâtiments n'en portent aucun ;
- la table `batiment_rnb_lien_bdtopo` publie 957 009 liens, tous pourvus d'un `identifiant_rnb`,
  dont 911 501 pointent vers un seul bâtiment et 911 449 se résolvent contre un `cleabs` présent
  dans l'export — 52 liens pendants ;
- les deux sources concordent sur 857 506 couples.

Conséquence pour [B2b](../backlog/B2b-import-bdtopo-ds04.md) : la chaîne de préférence commence
par l'identifiant officiel, qui couvre l'essentiel. L'intersection spatiale et la proximité — les
deux méthodes qui exigeraient un seuil, donc un profiling — ne concernent qu'une minorité. Les
29 236 bâtiments multi-RNB sont des appariements **ambigus par construction**, pas des erreurs.

Attention : `batiment_rnb_lien_bdtopo.informations_rnb` est une copie figée de métadonnées RNB
datées de 2023, dont des `identifiants_ban` d'autres départements. C'est une observation conservée
telle quelle, jamais une source d'appariement.

### Ce que l'export débloque

- `construction_legere` distingue 212 841 constructions légères de 761 331 constructions
  ordinaires — les « bâtiments légers » qui étaient jusqu'ici une valeur manquante ;
- `etat_de_l_objet` : 972 590 en service, 843 en construction, 729 en ruine, 10 en projet ;
- la voirie alimente `LAND-008` (`road_access_proxy`). Elle porte de quoi qualifier l'accès sans
  rien inventer : `nature` (256 952 routes à 1 chaussée, 41 885 routes empierrées, 37 999 chemins,
  36 915 sentiers, 249 escaliers…), `prive` (490 tronçons privés, 387 006 publics, 3 721 non
  renseignés) et `fictif` (39 tronçons). Le choix de ce qui compte comme « voie publique » pour
  `LAND-008` relève du profiling de [B5](../backlog/B5-features-morphologiques.md), pas de l'import.

### Import réel du 7 septembre 2026

Exécuté sur base propre, cadastre `DS-01@2026-06-01` publié et RNB `DS-02@2026-09-05` importé.
Archive résolue depuis la copie immuable, sans téléchargement : `asset_origin: database_archive`.

| | Lues | Normalisées | Quarantaine |
|---|---:|---:|---:|
| `batiment` | 974 172 | 974 172 | 0 |
| `troncon_de_route` | 391 217 | 391 217 | 0 |
| **Total** | **1 365 389** | **1 365 389** | **0** |

Aucune quarantaine : les 1,37 M géométries sont valides après passage en deux dimensions.
L'altimétrie est perdue — les colonnes canoniques sont 2D — et rien d'autre.

### Le débordement départemental, mesuré

| Périmètre | Bâtiments | Avec lien RNB | Sans lien |
|---|---:|---:|---:|
| Dans le 35 | 801 170 | 783 459 | 17 711 |
| Hors 35 | 173 002 | 22 | 172 980 |

Les 974 172 bâtiments de l'export ne sont donc **pas** le compte du 35 : 173 002 relèvent des 143
communes limitrophes. Ils sont conservés comme observations non appariées avec leur motif — le
référentiel RNB chargé ne couvre que le 35, donc leur identité canonique n'existe pas ici. Ce ne
sont pas des anomalies, et ils ne sont pas écartés.

Même partage pour la voirie, à partir des codes INSEE portés par la source : 323 302 tronçons dans
le 35, 67 915 hors département.

### Taux d'appariement par méthode

| Méthode | Décision | Liens |
|---|---|---:|
| `official_identifier` | certain | 692 633 |
| `official_identifier` | ambigu | 46 106 |
| `source_relation` | certain | 1 |
| `spatial_intersection` | ambigu | 87 255 |
| `proximity` | non exécutée | — |

Distribution en quatre classes par observation, sur les 332 communes du 35 :

| certain | ambigu | rejeté | non apparié |
|---:|---:|---:|---:|
| 692 621 | 90 841 | 0 | 17 711 |

**L'appariement vient presque entièrement de la source.** L'identifiant officiel porte 692 633 des
692 634 rattachements certains ; la table de liens n'en ajoute qu'un seul, parce qu'elle ne sert
que là où `identifiants_rnb` est absent. C'est le résultat attendu de l'audit : la chaîne de
préférence se résout sur l'identité déclarée, pas sur la géométrie.

**Aucun rattachement géométrique n'est déclaré certain.** Les 87 255 liens d'intersection spatiale
sont tous ambigus : le taux de recouvrement au-delà duquel deux emprises décrivent le même
bâtiment ne vient d'aucune mesure. Le recouvrement mesuré est conservé comme preuve, avec
`threshold_calibrated: false`. C'est le même raisonnement qui a valu son verdict à DS-05.

**La proximité n'a pas été exécutée.** Contrairement à l'intersection, elle exige un seuil de
distance pour produire le moindre candidat, et aucun seuil observé n'existe. Un seuil inventé est
interdit. Cette méthode attend [B4](../backlog/B4-revue-manuelle-appariements.md).

Les 46 106 liens ambigus par identifiant officiel correspondent aux emprises que la source
elle-même déclare couvrir plusieurs bâtiments RNB. Ce sont des ambiguïtés **par construction**,
pas des erreurs, et aucun choix arbitraire n'est fait entre les candidats.

### Aucune emprise inventée — vérifié

Les 3 864 bâtiments RNB ponctuels conservent `geom IS NULL` après l'import. L'importeur n'écrit
jamais `reference.building.geom` : les emprises BD TOPO restent dans
`meta.entity_source_observation`, et le RNB garde l'identité bâtiment préférée. Les 692 634
identifiants DS-04 rattachés portent tous `is_preferred = false`.

À ne pas confondre : 23 816 identifiants DS-04 supplémentaires proviennent du champ `ext_ids` du
RNB, portés par la release DS-02. Ce sont des **références observées via le RNB**, pas des
observations de DS-04.

### Verdict du 7 septembre 2026 — `display_only`

**Ce qui est acquis.** La release est reproductible, l'import relançable et intégralement
normalisé, sans quarantaine. Le débordement départemental est mesuré et motivé. 692 621 bâtiments
du 35 sont rattachés de façon certaine par l'identité déclarée par la source. La voirie est
disponible et qualifiée — `nature`, `prive`, `fictif` — ce qui débloque le calcul de `LAND-008`.
Les 212 841 constructions légères cessent d'être une valeur manquante.

**Ce qui manque.** Les 90 841 rattachements ambigus ne peuvent pas être tranchés sans vérité
terrain : ni le seuil de recouvrement, ni le seuil de divergence entre emprise BD TOPO et emprise
RNB ne sont calibrés. Une feature qui entrerait dans un score en dépendant hériterait de cette
incertitude.

D'où le verdict, identique à celui de DS-05 et pour la même raison : les attributs bâtiment et la
voirie peuvent alimenter la carte et les calculs qui ne dépendent que du rattachement certain ; les
rattachements ambigus ne peuvent pas fonder une feature entrant dans un score.

Passage à `accepted` conditionné à [B4](../backlog/B4-revue-manuelle-appariements.md) : seuils
recalibrés depuis la distribution observée, ou justifiés par une revue manuelle stratifiée.

## DS-05 — Base Adresse Nationale

- documentation officielle :
  <https://doc.adresse.data.gouv.fr/docs/documentation-generale/utiliser-la-base-adresse-nationale/les-fichiers-de-la-base-adresse-nationale> ;
- archive retenue : CSV départemental archivé du 17 juin 2026 ;
- taille : 17 098 791 octets ;
- SHA-256 : `22160b6d570c1ca557fd5eb60e99f4d83a80be715422fce5a828f3d847ccc3d0` ;
- `cad_parcelles` est traité comme une relation source expérimentale et vérifié contre la géométrie
  de la parcelle Cadastre active.

Le fichier comporte 437 679 lignes normalisées pour 437 441 identifiants distincts. L'audit brut a
détecté 8 identifiants répétés à l'identique, soit 8 lignes en excès dédupliquées sans perte de
l'archive, et 217 identifiants réutilisés avec des contenus différents, portés par 447 lignes dont
230 en excès.

Aucun de ces 217 conflits ne porte sur l'identité de l'adresse : `numero`, `rep`, `nom_voie`,
`code_postal`, `code_insee` et `nom_commune` restent stables entre les variantes. 216 divergent par
leur position, avec un écart médian de 47,8 m et un maximum de 3 128,5 m.

Depuis le 4 septembre 2026, ces conflits ne bloquent donc plus la release : l'identité est
conservée et seul l'attribut contradictoire devient manquant avec un motif. Une divergence portant
sur l'identité elle-même reste, elle, bloquante. Voir
[le rapport de quarantaine par attribut](./ban-attribute-quarantine-35.md) et le détail des 217
identifiants dans [`ban-conflicting-identifiers-35.csv`](./ban-conflicting-identifiers-35.csv).

### Verdict du 4 septembre 2026 — `display_only`

Import réel exécuté sur base propre, cadastre `DS-01@2026-06-01` publié comme référentiel actif.
Compteurs persistés : 437 679 lignes lues, 437 441 normalisées, 0 en quarantaine, 238 dédupliquées
— identiques à ceux que [le décompte de l'archive](./ban-census-35.json) prédisait, ce qui lève la
limite laissée ouverte par [BUG-01](../backlog/BUG-01-chiffres-audit-ban.md). Preuves complètes
dans [`ban-import-35.json`](./ban-import-35.json).

**Ce qui est acquis.** L'identité des adresses est vérifiée : aucun identifiant réutilisé avec une
identité contradictoire, contrôle bloquant `conflicting_ban_identity` au vert. Les 216 adresses
sans position n'entrent dans **aucune** relation spatiale. Les relations `cad_parcelles` se
résolvent à 98,8 % contre la géométrie cadastrale active ; les 3 760 restantes (3 302 adresses,
1,15 %) sont conservées en relation `rejected` motivée, jamais écartées en silence.

**Ce qui manque.** Les paliers de confiance 0,99 / 0,95 / 0,80 et la frontière de 10 m qui sépare
`certain` de `ambiguous` ne viennent d'aucune mesure. La distribution observée des distances
point ↔ parcelle déclarée les contredit : la densité **croît** en traversant 10 m et culmine entre
20 et 50 m. Voir [le rapport spatial 35](./spatial-reference-35-report.md#audit-ban).

Une confiance est une probabilité que la relation soit juste. Aucune géométrie ne l'estime sans
vérité terrain : cela relève de [B4](../backlog/B4-revue-manuelle-appariements.md).

D'où le verdict. Les adresses sont saines et peuvent alimenter la recherche et la carte ; les
relations parcellaires ne peuvent pas fonder une feature entrant dans un score. C'est exactement
la portée de `display_only`, désormais opposable techniquement : la release figure dans
`meta.active_dataset_release` et est exclue de `meta.analysis_dataset_release`.

Passage à `accepted` conditionné à B4 : paliers recalibrés depuis la distribution observée, ou
justifiés par une revue manuelle stratifiée.

## Garanties transversales

- **tout manifeste est refusé avant téléchargement s'il ne permet pas de retrouver ses octets** :
  SHA-256 obligatoire, et au moins un chemin de récupération — URL datée ou copie archivée
  nommée. Les trois couches de DS-01 portaient `"sha256": null` ; leurs checksums ont été
  re-vérifiés contre le répertoire daté d'Etalab le 7 septembre 2026 et inscrits au manifeste ;
- les tables sources restent versionnées et append-only ;
- les identités canoniques utilisent des identifiants texte stables et conservent les identifiants
  sources en relation plusieurs-à-plusieurs ;
- les décisions `certain`, `ambiguous` et `rejected` sont persistées avec méthode, version,
  confiance, justification, preuves et releases ;
- une ambiguïté critique bloque la publication mais ne disparaît pas du catalogue d'audit ;
- l'API ne lit que les entités dont la release source est acceptée et activée ;
- les géométries de parcelles ne sont pas recopiées dans chaque `PropertyUnit` : les vues
  canoniques s'appuient sur la release Cadastre active et ses index.

