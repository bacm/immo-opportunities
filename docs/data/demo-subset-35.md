# Sous-ensemble démo du 35 — cinq communes restaurées

**Date :** 17 septembre 2026 · **Ticket :** [A6](../backlog/A6-demo-sous-ensemble-vps.md)

**Base source.** Base locale `immo` du poste, département 35, avec :

- les releases actives du référentiel : DS-01@2026-06-01, DS-03@2026-02-a, DS-04@2026-06-15,
  DS-05@2026-06-17 ;
- les releases métier : DS-06@2019-04-archive, DS-06@2026-09-13, DS-07@2026-09-14-extract,
  DS-13@2026-09-16-extract, DS-08@2026-09-14, DS-09@*--2026-09-14. Elles n'ont pas de pointeur
  actif.

**Outils :** `scripts/export-demo-subset`, `scripts/restore-demo-subset`, `compose.demo.yaml`.

**Mesures.** Prises sur le poste de développement (Docker Desktop, 10 CPU, 11,7 Gio), stack démo
sous limites mémoire. Recomptées de façon indépendante (`recompte-preuve`) sur un premier export ;
les écarts relevés sont corrigés ci-dessous. **Rien n'a encore été mesuré sur la machine cible**
(voir la dernière section).

## Communes retenues

| Code | Commune | Strate (B4, D6) |
|---|---|---|
| 35238 | Rennes | urbain |
| 35288 | Saint-Malo | littoral |
| 35047 | Bruz | périurbain |
| 35360 | Vitré | ville moyenne |
| 35211 | Paimpont | rural |

La stratification est celle de B4 et D6. Ces cinq communes portent 7,7 % des parcelles
(102 676 / 1 333 327), mais 46 % des DPE (104 120 / 226 757) et 29 % des mutations
(91 645 / 312 639), comptés par `commune_code` : la démo est dense.

## Volumétries avant et après

Lignes comptées par `count(*)` le 17 septembre 2026. La colonne « Démo » inclut les objets
d'autres communes rattachés aux cinq communes (section « Frontières »). La dernière colonne
compte la démo filtrée sur `commune_code IN (35238, 35288, 35047, 35360, 35211)`.

| Table | Département 35 | Démo | Démo, 5 communes |
|---|---:|---:|---:|
| `reference.parcel` | 1 333 327 | 102 676 | 102 676 |
| `reference.building` | 741 379 | 84 010 | 83 905 |
| `reference.cadastral_building` | 865 335 | 100 154 | — |
| `reference.address` | 437 441 | 64 992 | 64 992 |
| `feature.feature_value` | 25 663 354 | 2 051 156 | — |
| `observation.energy_assessment` | 226 757 | 104 186 | 104 119 |
| `observation.transaction` | 312 639 | 91 683 | 91 645 |
| `observation.risk_observation` | 10 824 | 742 | 742 |
| `observation.urban_zone` | 21 136 | 1 722 | — |
| `meta.entity_source_observation` | 2 699 523 | 310 821 | — |
| `meta.entity_match` | 3 373 312 | 475 843 | — |

La source compte 104 120 DPE pour les cinq communes, et la démo 104 119 : l'écart est le DPE
écarté de la section « Frontières ».

Taille par schéma, tables et index compris (`pg_total_relation_size`), en Gio :

| Schéma | Département 35 | Démo |
|---|---:|---:|
| `meta` | 10,87 | 1,02 |
| `feature` | 10,48 | 0,71 |
| `reference` | 5,41 | 0,40 |
| `observation` | 2,66 | 0,41 |
| `tiles` | 1,67 | 0,15 |
| **base entière** (`pg_database_size`) | **31,1** | **2,70** |

## Export et restauration

| Mesure | Valeur |
|---|---|
| Fichier `immo-demo.sql.gz` | 280 839 262 octets |
| SHA-256 | `81a940137ad63f9ae5c91cd0fed81354223d67f5d2a7a647b2042d9c0dc0d76e` |
| Durée de l'export | 169 s |
| Durée de la restauration, `ANALYZE` compris | 69 s |
| Base restaurée | 2,70 Gio (critère : moins de 6 Go) |

**Reproductibilité.** Deux exports successifs des cinq communes donnent le même fichier (même
taille, même SHA-256). C'était déjà le cas pour Paimpont seul, au premier essai. Les lignes sont
triées par clé primaire, et le fichier est compressé sans date ni nom de fichier.

**Cohérence.** La restauration se fait en une seule transaction, et les clés étrangères sont
recréées à la fin (post-data) : une ligne orpheline aurait fait échouer la restauration. Le
recomptage a vérifié chacune des 137 clés étrangères avec une requête `NOT EXISTS` : aucun
orphelin. Il a trouvé des nombres identiques à la base source pour les contraintes, les index
(208), les vues (10), les politiques RLS (12) et les déclencheurs (22). Sur Paimpont, les
privilèges des rôles (533) sont eux aussi identiques. Les 25 tables en « schéma seul » sont
vides, et les lignes par table du manifeste égalent les `count(*)` de la démo.

## Frontières

Un objet des cinq communes montre, sur la base complète, des objets d'autres communes. Pour ne pas
présenter une absence de donnée comme une absence d'objet, l'export les **ajoute**, dans une
limite : une parcelle d'une autre commune n'est jamais ajoutée, car elle ferait passer sa commune
pour couverte. Ce qui ne peut pas être ajouté est **coupé**. Le manifeste compte tout :

| Frontière | Lignes | Traitement |
|---|---:|---|
| bâtiments d'autres communes posés sur une parcelle retenue | 105 | ajoutés |
| bâtiments cadastraux d'autres communes qui coupent la limite des cinq communes (6 la chevauchent, 97 la touchent) | 103 | ajoutés |
| ventes d'autres communes portant un lot retenu | 38 | ajoutées |
| DPE d'autres communes rattachés à un bâtiment ou une adresse retenus | 67 | ajoutés |
| `reference.building_parcel` dont un seul côté est retenu | 206 | coupés |
| `meta.entity_match` dont un seul côté est retenu | 1 106 | coupés |
| `reference.property_unit_member` | 0 | — |
| `energy_assessment.address_id` hors des adresses retenues | 65 | mis à NULL, comme `ON DELETE SET NULL` |
| `energy_assessment.building_id` hors des bâtiments retenus | 56 | idem |
| `energy_assessment` sans adresse ni bâtiment restant | 1 | écarté (`energy_assessment_target`) |
| `transaction_property.parcel_id` hors des parcelles retenues | 308 | mis à NULL : lot d'une vente sur plusieurs communes |

Les nullifications sont comptées **avant** l'écartement. Le DPE écarté compte dans les 65 et dans
les 56 : la démo montre donc 64 adresses et 55 bâtiments mis à NULL, et aucun DPE sans les deux.

## L'Explorer sur la démo

Stack `compose.yaml` + `compose.demo.yaml`, projet Compose `immo-demo`, port 8090. Réponses de
l'API démo comparées à celles de la base complète, `request_id` retiré et listes triées :

| Échantillon | Routes | Réponses identiques |
|---|---|---:|
| 40 parcelles, 8 par commune (tirage `md5`) | fiche, mutations, DPE, parcelle cadastrale | 160 / 160 |
| 32 parcelles des cinq communes en bordure : bâtiment voisin, vente d'une autre commune, cas relevés par le recomptage | les mêmes | 128 / 128 |
| 5 parcelles d'autres communes touchant un bâtiment retenu | les mêmes | fiche et parcelle cadastrale : 404 ; mutations et DPE : liste vide |

Le premier export ne couvrait pas les frontières dans ce sens. Le recomptage y avait trouvé
20 réponses divergentes sur 72 en bordure, par exemple 0 DPE contre 99 sur la parcelle
35238000DS0064. Ces cas sont désormais identiques.

**Défaut antérieur à A6.** Mutations et DPE d'une parcelle absente rendent 200 et une liste vide,
y compris pour une parcelle qui n'existe nulle part (35999000ZZ9999) : sur la démo, une parcelle
hors des cinq communes montre 0 mutation là où la base complète en a 3, alors que sa fiche
rend 404. Le défaut est suivi par
[BUG-22](../backlog/BUG-22-parcelle-absente-liste-vide.md).

**Autre défaut antérieur.** `/parcels/{id}/transactions` rend les lots ex æquo d'une même vente dans
un ordre variable, y compris sur la base complète (35238000DK0446). D'où le tri des listes avant
comparaison.

Couverture, par `/api/v1/spatial/coverage` et `/api/v1/property-units` :

| Territoire | Réponse |
|---|---|
| Les cinq communes | `partial` : seul DS-02 manque, comme sur la base complète, faute de pointeur actif |
| Acigné (35001), hors du sous-ensemble | `not_covered`, les cinq sources nommées (`partial` sur la base complète) |
| Fenêtre sur Rennes | `covered`, parcelles listées |
| Fenêtre sur Acigné | `outside_coverage`, aucune parcelle |
| Fenêtre dans le Morbihan | `outside_coverage` |

**Recherche et connexion.**

- La recherche trouve les adresses des cinq communes (« 10 Rue de Paris 35500 Vitré ») et les
  communes absentes (« ACIGNE ») : la carte s'y centre, puis dit « non couverte ».
- La page de connexion Keycloak est servie.
- L'émetteur OIDC (`…/auth/realms/immo`) est celui qu'attend l'API.

**Limite antérieure à A6.** L'Explorer n'affiche ni zonage ni risques, sur aucune des deux bases.
`/property-units/{id}/market-context` rend une réponse vide, identique sur les deux bases.

## Mémoire et tuiles

Limites de `compose.demo.yaml`, et consommation relevée par `docker stats`. La première colonne
de mesure est prise juste après un redémarrage de PostgreSQL et de Martin ; le recomptage a relevé
la seconde, après des lectures complètes de la base.

| Service | Limite | Après redémarrage | Après lectures complètes |
|---|---:|---:|---:|
| PostgreSQL | 1 536 Mio | 364 Mio | 517 Mio |
| Keycloak | 900 Mio | 324 Mio | 564 Mio |
| API | 512 Mio | 69 Mio | 70 Mio |
| Martin | 256 Mio | 26 Mio | 26 Mio |
| Caddy | 128 Mio | 15 Mio | 18 Mio |
| web | 64 Mio | 7 Mio | 7 Mio |
| **Total** | **3 396 Mio** | **~805 Mio** | **~1 200 Mio** |

La consommation de PostgreSQL inclut le cache de pages de son conteneur. Elle monte avec les
lectures, jusqu'à sa limite.

**Tuiles.** Emprise approximative de Rennes (−1,75 ; 48,08 ; −1,62 ; 48,15), au plus 40 tuiles
par couche et par zoom, **à froid**, juste après le redémarrage de PostgreSQL et de Martin.

| Zoom | Couches | Tuiles | p50 | p95 | max |
|---|---|---:|---:|---:|---:|
| 13 | parcelles | 12 | 24 ms | 104 ms | 104 ms |
| 14 | parcelles | 35 | 7 ms | 32 ms | 32 ms |
| 15 | parcelles, bâtiments | 80 | 4 ms | 36 ms | 88 ms |
| 16 | parcelles, bâtiments | 80 | 1 ms | 4 ms | 7 ms |
| 17 | parcelles, bâtiments | 80 | 1 ms | 3 ms | 3 ms |
| 18 | parcelles, bâtiments | 80 | 1 ms | 2 ms | 3 ms |

Trois précisions :

- **Tuiles vides.** À partir du zoom 15, 15 à 34 des 80 tuiles sont vides (HTTP 204). Elles tirent
  les p95 vers le bas.
- **Cache.** Le cache de Martin rend ensuite chaque tuile en 1 ms environ. Le recomptage, à chaud,
  trouve des p95 compris entre 1 et 33 ms.
- **Portée.** Ces chiffres viennent d'un poste à SSD local. Ils ne disent rien des disques ni du
  CPU partagé d'un VPS.

## Ce que la démo ne contient pas

- **Les 327 autres communes du 35**, ni leurs parcelles. Elles restent nommées et situées, car
  `reference.area` et `reference.administrative_area` gardent leurs 332 communes. La couverture les
  dit non couvertes. Seuls les bâtiments, ventes et DPE rattachés aux cinq communes y figurent
  (section « Frontières »).
- **Le score** : snapshots, publications, backtests et ablations (schéma seul). Les deux définitions
  de score sont copiées, en `publication_eligible = false`.
- **Les comptes et le travail des organisations** : schémas `app` et `audit` (schéma seul).
- **La revue manuelle B4** : `meta.matching_review_*`, qui porte l'identité des relecteurs
  (schéma seul).
- **Les contrôles qualité de département** : seuls ceux de portée communale sont copiés (30 lignes).
- **Les métriques de couverture et d'appariement hors des cinq communes** : la base source en
  porte respectivement pour 335 et 332 communes ; la démo en garde 75 et 25 lignes, qui sont
  toutes celles des cinq communes.
- **Dagster, MinIO, Redis et les archives de sources** : la démo restaure, elle n'importe pas.
- **Les liens coupés** et les références mises à NULL, dénombrés plus haut.

## Machine cible — à mesurer

La démo est destinée au VPS du porteur (2 vCPU, 4 Go, 80 Go), qui sert déjà d'autres conteneurs.
Les limites déclarées totalisent 3,3 Gio. La consommation observée va de 0,8 à 1,2 Gio selon la
charge. La marge dépend donc aussi de ce qui tourne déjà sur la machine.

Restent à mesurer par le porteur, selon `DEPLOYMENT.md` §5 :

- la taille restaurée ;
- l'empreinte mémoire ;
- le p95 des tuiles de Rennes, à froid ;
- l'usage de la mémoire d'échange (swap).

Si la machine utilise sa mémoire d'échange, le palier 4 Go ne suffit pas.
