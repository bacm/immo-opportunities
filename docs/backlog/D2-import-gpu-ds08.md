# D2 — DS-08 GPU : zonage et contraintes, sans interprétation de règlement

**Version :** v0.5 · **Taille :** M · **État :** En cours
**Dépend de :** D1 · **Bloque :** D5
**Touche :** pipelines/scripts/compute_urban_features.py, pipelines/scripts/import_gpu_release.py, pipelines/src/immo_pipelines/market_data/cnig.py, contracts/datasets/DS-08/, docs/data/gpu-coverage-35.md

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

### `URB-001` : la règle vient de la distribution observée, pas d'un seuil

Mesuré sur le PLUi de Rennes Métropole — 4 069 zones, aucune géométrie invalide — croisé avec les
parcelles de Rennes, Cesson-Sévigné et Saint-Grégoire : **51 577 parcelles**.

| | Parcelles | Part |
|---|---:|---:|
| Une seule zone | 35 869 | 69,5 % |
| **Plusieurs zones** | **15 708** | **30,5 %** |
| Maximum observé | 15 zones sur une parcelle | — |

Le partage est donc trop fréquent pour être traité en exception. Mais il est **massivement
déséquilibré** :

| Parmi les 15 708 parcelles multi-zones | Part |
|---|---:|
| Zone dominante à plus de 95 % | **92,0 %** |
| Zone dominante à plus de 90 % | 93,1 % |
| Seconde zone sous 1 % | **91,0 %** |
| **`typezone` réellement différents** | **19,6 %** |

Neuf parcelles sur dix touchent une seconde zone sur moins de 1 % de leur surface : c'est du bruit
de numérisation entre deux découpages, pas un zonage partagé. Et quatre partages sur cinq portent
sur des sous-zones du **même** `typezone` — `UC1` contre `UC2` — ce qui ne change pas ce qu'on
peut faire du terrain.

**La règle retenue est celle du rang, transposée de
[BUG-09](./BUG-09-recouvrement-batiment-parcelle.md) :** la zone représentative est celle qui
couvre la plus grande part de la parcelle. Aucun seuil n'est inventé, et la revue B4 a montré
qu'un seuil sur un recouvrement se paie cher — le relecteur y jugeait faux à 12,4 % et juste à
15,6 %.

**Une parcelle partagée entre deux `typezone` distincts reste enregistrée comme telle.** C'est la
réalité juridique : une parcelle à cheval est soumise aux deux règlements sur ses parties
respectives. La zone de rang 1 est représentative, les autres sont conservées comme relations
secondaires, et le scoring devra en tenir compte plutôt que de croire la parcelle homogène.

### `typezone` et `libelle` ne se comparent pas de la même façon

Deux colonnes, deux natures, et les confondre produirait des comparaisons fausses :

| Colonne | Exemple | Nature |
|---|---|---|
| `typezone` | `U`, `AUc`, `A`, `N` | **normalisé CNIG**, comparable entre documents |
| `libelle` | `UG2b`, `UC2`, `UD1a` | **code du règlement local**, sans portée hors du document |

`UG2b` à Rennes n'a aucun rapport avec `UG2b` ailleurs. `URB-001` doit porter les deux, et le
scoring ne peut comparer que `typezone`.

### Une zone de PLUi ne porte pas de code commune

Sur les 4 069 zones de Rennes Métropole, `insee` et `destdomi` sont vides **partout**. Un PLU
communal renseigne `INSEE`, mais on ne peut pas dépendre d'un champ qui disparaît sur les
documents intercommunaux.

Le rattachement zone ↔ parcelle est donc **nécessairement spatial** — ce n'est plus une préférence
de conception mais une contrainte de la donnée. `DOC_URBA_COM` donne le périmètre administratif du
document, pas le rattachement de chaque zone.

### Un document réellement malformé, et ce qu'il impose

**Dinard, `DU_35093`** — la commune sur laquelle la revue B4 a travaillé — est le seul document du
35 que l'épinglage ne sait pas lire. Le diagnostic, une fois la lecture partielle corrigée :

| Couche | Premier octet | Nature réelle |
|---|---|---|
| `DOC_URBA.dbf` | `0x50` | **archive Office renommée** — on y lit `[Content_Types].xml` |
| `DOC_URBA_COM.dbf` | `0x50` | **archive Office renommée** |
| `zone_urba`, `prescription_*`, `info_surf` | `0x03` | DBF valides |

Les octets sont complets — vérifié en comparant la taille lue à la taille déclarée par le ZIP,
donc la lecture partielle n'est pas en cause. Ce sont deux fichiers Office déposés sous une
extension `.dbf` par le producteur.

**Ce que cela coûte :** les cinq couches géographiques de Dinard sont lisibles, mais son
`DOC_URBA_COM` ne l'est pas. Le document ne peut donc pas déclarer les communes qu'il couvre, et
le rattachement administratif échoue. Le rattachement **spatial**, lui, resterait possible.

**Ce qui est décidé ici :** le document est consigné comme illisible, avec son motif, et Dinard
compte parmi les communes sans zonage importé. Deviner que `DU_35093` couvre la commune `35093`
depuis son nom serait une convention inventée — exactement ce que la règle « aucune convention
inventée » interdit. Le signaler au producteur est la bonne réponse ; le contourner n'en est pas
une.

**Ce que cela apprend :** un fichier peut porter la bonne extension, la bonne taille et le bon
nom, et n'être pas du tout ce qu'il prétend. La reconnaissance par nom ne suffit pas — l'import
doit vérifier la signature des couches qu'il lit, et échouer bruyamment sinon.

### Périmètre : les documents d'urbanisme, pas les servitudes

Les types retenus sont `PLU`, `PLUi`, `CC`, `POS` et `PSMV`.

Les **SUP** — neuf sur le territoire `35` — sont exposées par le même catalogue mais traitées par
[D3](./D3-import-georisques-ds09.md), décision du 14 septembre 2026 : une SUP ne dit pas ce que la
collectivité veut faire de son territoire, elle constate une contrainte extérieure qui s'impose au
document d'urbanisme sans en dépendre. C'est la nature même de ce que D3 traite.

Les **SCoT** sont exclus aussi : ils ne s'appliquent pas à la parcelle.

### Prévoir les variantes avant le lot, pas après chaque échec

**Méthode corrigée le 14 septembre 2026**, sur remarque pendant l'import : chaque variante non
prévue coûtait un lot complet, une correction, une relance. Cinq cycles pour cinq variantes.

L'erreur n'était pas de découvrir ces cas — ils sont inconnaissables d'avance — mais de **lancer
un lot de 184 documents en supposant que tous ressembleraient aux trois premiers testés**.

> **La règle qui en découle ne vit plus ici.** Elle s'applique à tout pipeline nouveau ou modifié,
> et elle est écrite dans [`ARCHITECTURE.md` §10.6](../../ARCHITECTURE.md#106-résistance-à-la-variété-des-sources).
> Ce qui suit en est l'instance observée sur DS-08.

Ce qu'un import de ce type doit prévoir **avant** son premier lot :

| Variante | Observée sur le 35 | Traitement |
|---|---|---|
| Attribut obligatoire vide | `DATAPPRO` absent — 2 documents | repli sur la date du catalogue, **provenance marquée** |
| Encodage non déclaré | `.cpg` absent — 5 documents | UTF-8 si déclaré, Latin-1 sinon, qui ne peut pas échouer |
| Géométrie invalide | 3 documents | comptée et écartée, le document passe sans elle |
| Débit limité | `429` — 4 documents | temporisation 5 s, 15 s, 45 s, puis échec passager |
| Erreur au message illisible | `pyshp` lève un entier nu | le type est joint au message |
| Carte communale sans zonage | 14 documents | résultat normal, pas une anomalie |
| Parcours séquentiel d'un `.shp` | `DU_35136` | lecture **par index** via le `.shx` |

**Le septième cas mérite d'être retenu**, parce qu'il ne ressemble pas à un défaut de donnée.
`DU_35136` échouait sur un `KeyError` négatif de `pyshp` — un octet de remplissage lu comme un
type de forme. Or ses 309 géométries sont **toutes lisibles une à une** : c'est le parcours
séquentiel du `.shp` qui s'arrête au premier en-tête mal aligné, là où l'accès indexé passe par le
`.shx`, qui existe précisément pour ça. Le document entier était perdu pour un défaut
d'alignement, et la lecture indexée le récupère en totalité.

**Le 429 est le plus instructif.** Ce n'est pas un défaut du document, c'est une demande
d'attendre — et le traiter en échec définitif condamnait quatre documents valides. Un import qui
sollicite un service public doit temporiser, pas insister.

Trois de ces six variantes n'ont été trouvées qu'en lisant les échecs d'un lot interrompu. La
règle qui en découle : **inventorier la variété d'un échantillon avant de traiter le tout**, et
faire échouer un document sans faire échouer le lot.

### Un chemin d'erreur est un résultat, pas une exception

Quatre défauts de même famille se sont succédé sur ce seul ticket. Aucun n'était visible d'un
contrôle automatique, et trois n'ont été vus que parce que le chiffre attendu était connu.

| Défaut | Symptôme | Ce qui l'a révélé |
|---|---|---|
| Casse des champs CNIG | « Rennes Métropole couvre 1 commune, hors du 35 » | l'invraisemblance du chiffre |
| Convention de nommage versionnée | Couesnon absent du manifeste, sans erreur | un comptage 5 au lieu de 6 |
| Lecture partielle tronquée | erreur d'en-tête ZIP imputée au producteur | la trace d'exécution |
| Échec réseau consigné comme définitif | deux documents absents pour toujours | la relecture du manifeste |

Le dernier est le plus instructif : le mécanisme de reprise, écrit pour ne rien perdre,
**transformait un incident réseau en absence permanente**. Un document consigné illisible était
compté comme traité et jamais repris.

**La règle qui s'en dégage, et qui vaut pour tout import de ce ticket :**

1. **Un cas non prévu échoue bruyamment.** Une archive sans couche reconnue n'est pas « hors
   périmètre », c'est un nom qu'on ne sait pas lire. Un document silencieusement absent est pire
   qu'un import qui s'arrête.
2. **Un échec est consigné dans le manifeste, pas seulement journalisé.** Taire un document
   illisible ferait passer une couverture partielle pour une couverture complète.
3. **Un échec passager n'est pas un échec définitif.** Un délai dépassé ne dit rien du document ;
   le consigner comme définitif le condamne. Le script sort en code 3 pour dire que le manifeste
   est incomplet.
4. **Une lecture partielle vérifie ce qu'elle a reçu.** Une réponse courte produit une erreur qui
   nomme l'URL, la plage et le nombre d'octets — jamais un message qui accuse la donnée.
5. **Un fichier peut mentir sur sa nature.** `DU_35093` porte deux archives Office sous une
   extension `.dbf`. L'import vérifie la signature des couches qu'il lit.

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
