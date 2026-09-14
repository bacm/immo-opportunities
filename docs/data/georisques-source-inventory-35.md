# DS-09 Géorisques — inventaire de la source avant le premier lot

**Date :** 14 septembre 2026 · **Département :** 35 · **Ticket :** [D3](../backlog/D3-import-georisques-ds09.md)

`ARCHITECTURE.md` §10.6 impose d'inventorier la variété d'une source **avant son premier lot**.
Ce fichier est cet inventaire. Il est écrit avant toute ligne d'import parce que ce qu'il montre
change la forme du ticket.

## Ce que le ticket supposait, et ce que la source est

Le ticket D3 demande « une release par famille de risque », épinglée et checksumée, et le contrat
DS-09 déclare `preferred_format: versioned download; archived API response only when no download
exists`.

Il n'existe **pas** de téléchargement daté par famille et par département. La source se présente
sous **trois modes d'accès différents**, et aucune famille n'en partage entièrement un avec une
autre.

## Les trois modes d'accès

### 1. API départementale — un appel, tout le département

| Famille | Endpoint | Paramètre | Résultats sur le 35 | Granularité |
|---|---|---|---:|---|
| Installations classées | `installations_classees` | `departement=35` | 4 350 | `point` |
| Cavités souterraines | `cavites` | `departement=35` | 179 | `point` |
| Mouvements de terrain | `mvt` | `departement=35` | 372 | `point` |
| Sites et sols pollués (SSP/SIS) | `ssp/instructions` | **`code_departement=35`** | 191 | `zone` |

**Le nom du paramètre départemental n'est pas le même d'un endpoint à l'autre**, et l'erreur est
silencieuse : `installations_classees?code_departement=35` répond `200` avec **138 248**
résultats — la France entière — au lieu des 4 350 du département. Un paramètre inconnu n'est pas
rejeté, il est ignoré. Tout import doit donc vérifier que ce qu'il reçoit est bien ce qu'il a
demandé, et non se fier au code HTTP.

### 2. API communale — un appel par commune, 335 fois

| Famille | Endpoint | Granularité |
|---|---|---|
| Radon | `radon?code_insee=…` | `commune` |
| Risques recensés (GASPAR) | `gaspar/risques?code_insee=…` | `commune` |
| Atlas des zones inondables | `gaspar/azi?code_insee=…` | `commune` |
| Arrêtés de catastrophe naturelle | `gaspar/catnat?code_insee=…` | `commune` |

Ces quatre familles ne connaissent **que** `code_insee`. Un filtre départemental y répond `500`.
Elles produisent donc du `commune_context_only` par construction — ce qui est le bon sort : « la
commune est concernée par un PPRI » n'est pas « la parcelle est en zone inondable ».

### 3. Téléchargement national — un fichier, toute la France

| Famille | Fichier | Poids | Granularité |
|---|---|---:|---|
| Retrait-gonflement des argiles | `files.georisques.fr/argiles/AleaRG_Fxx_L93.zip` | **623 Mo** | `zone` |

Une seule couche nationale, `ExpoArgile_Fxx_L93.shp`, **823 Mo décompressés**, sans découpage
départemental : le répertoire central du ZIP, lu à distance, ne contient que cinq membres. Il n'y
a rien à extraire sélectivement, contrairement aux archives CNIG de D2.

L'URL ne porte pas de marqueur de version, mais son `Last-Modified` est **le 16 juin 2021** et le
site distingue explicitement une « version 2020 » d'une « version 2026 » : ce n'est pas un alias
mouvant en pratique, et l'`ETag` comme l'empreinte permettent de le constater à chaque reprise.

### 4. Les servitudes, qui ne sont dans aucun des trois

Neuf SUP en production sur le territoire `35` au catalogue du Géoportail de l'urbanisme :

| Document | Catégorie | Ce qu'elle constate |
|---|---|---|
| `130010937_SUP_35_PM1` | PM1 | plans de prévention des risques naturels — **le zonage inondation opposable** |
| `130010937_SUP_35_PM3` | PM3 | plans de prévention des risques technologiques |
| `120068051_SUP_35_I1` | I1 | canalisations de transport d'hydrocarbures |
| `552049447_SUP_35_T1` | T1 | voies ferrées |
| `120064019_SUP_35_T5` | T5 | servitudes aéronautiques de dégagement |
| `120064019_SUP_35_PT1`, `PT2` | PT1, PT2 | transmissions radioélectriques |
| `172014607_SUP_35_AC1`, `AC4` | AC1, AC4 | monuments historiques, sites patrimoniaux |

Elles s'obtiennent par l'API du GPU, avec la machinerie que D2 a écrite — `market_data.cnig` et
`market_data.remote_zip` — et donnent des géométries de **zone**.

`PM1` est le seul chemin vers un zonage inondation **opposable** sur le 35 : les endpoints GASPAR
n'en donnent que le fait communal.

## Deux anomalies relevées sur l'échantillon

**Une adresse peut contredire son code commune.** Le premier établissement classé renvoyé pour le
35 porte `commune: "Guipavas"` et `codePostal: 29490` — dans le Finistère — avec
`codeInsee: 35032`, Bourgbarré, et des coordonnées qui tombent effectivement en Ille-et-Vilaine.
L'identité et la position sont cohérentes ; c'est le libellé d'adresse qui est faux. Sort prévu :
quarantaine par attribut ([BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md)),
l'enregistrement est conservé, l'adresse part avec son motif.

**Un `500` peut vouloir dire « paramètre manquant ».** `cavites` sans filtre répond `500 Des
paramètres de recherches sont manquants`, pas `400`. Le code HTTP ne distingue donc pas une panne
passagère d'une requête mal formée : la temporisation doit se décider sur le corps de la réponse,
pas sur son statut, sans quoi une erreur de code se rejouerait cinq fois avant d'échouer.

## Ce que cet inventaire implique pour D3

| Feature | Famille qui la fonde | Disponible ? |
|---|---|---|
| `RISK-001` exposition argiles | argiles | oui — au prix d'un téléchargement national de 623 Mo |
| `RISK-002` zones inondables | SUP `PM1` | oui — zonage opposable ; GASPAR n'apporte que le contexte communal |
| `RISK-003` sites pollués | `ssp/instructions` | oui — géométries de zone réelles |
| `RISK-004` cavités | `cavites` | oui — 179 points |
| `RISK-101` contraintes applicables | toutes | oui |

Aucune famille requise n'est hors d'atteinte. Mais **dix familles, trois modes d'acquisition et
quatre endpoints aux paramètres incompatibles** ne tiennent pas dans la taille `L` annoncée par le
ticket : chaque mode demande son propre épinglage, sa propre garde de filtrage et son propre
verdict.
