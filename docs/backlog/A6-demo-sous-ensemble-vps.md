# A6 — Démo déployable : un sous-ensemble de communes sur une petite machine

**Version :** transverse · **Taille :** L · **État :** Terminé
**Touche :** scripts/export-demo-subset, scripts/restore-demo-subset, scripts/check-compose-config, scripts/tests/test_demo_subset.py, scripts/tests/conftest.py, compose.demo.yaml, backend/src/immo/spatial.py, backend/src/immo/explorer.py, backend/tests/test_demo_coverage.py, docs/data/demo-subset-35.md, .github/workflows/deploy-vps.yml, DEPLOYMENT.md
**Dépend de :** — · **Bloque :** A13
**Demandé par :** conversation du 15 septembre 2026

## Contexte à charger

- `compose.prod.yaml` et `compose.yaml` (service `postgres`, réglages et limites)
- `docs/operations/postgresql-tuning.md`
- `docs/operations/referentiel-local-35.md` (séquence de reconstitution de l'état)
- `.github/workflows/deploy-vps.yml`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le déploiement VPS n'est pas tenable en l'état : la base du seul département 35 pèse **27 Go
logiques, 33 Go sur le volume**, et les limites de `compose.prod.yaml` cumulent environ **24 Go de
RAM** — PostgreSQL 12 Go, MinIO 4, Keycloak 2, Redis 2, API 1, plus Dagster et l'observabilité. La
machine requise n'a rien d'une machine de démonstration.

Mesures du 15 septembre 2026 sur la base locale :

| Schéma | Taille | Part |
|---|---|---|
| `meta` | 11 Go | 40 % |
| `feature` | 7,6 Go | 27 % |
| `reference` | 5,5 Go | 20 % |
| `observation` | 2,1 Go | 8 % |
| `tiles` | 1,7 Go | 6 % |

Plus 1,9 Go de MinIO (archives pincées) et ~180 Mo d'observabilité.

## Choix retenus — 17 septembre 2026

Pris par l'agent avec le porteur, en conversation.

- **Machine cible** : le VPS Hetzner existant du porteur, 2 vCPU / 4 Go / 80 Go, qui sert déjà
  d'autres conteneurs derrière un Caddy et Cloudflare. Le palier 4 Go est **mesuré**, pas
  supposé ; s'il ne tient pas, le porteur agrandit la machine (« Rescale », CPU et RAM seuls,
  réversible).
- **Aucun port public pour la stack démo** : son Caddy écoute sur `127.0.0.1` ; le Caddy du
  porteur y renvoie un sous-domaine proxifié par Cloudflare.
- **Protection par Cloudflare Access**, réglée hors dépôt par le porteur, sur ce seul sous-domaine,
  avec l'origine fermée à tout ce qui ne vient pas de Cloudflare. Motif : l'Explorer, les tuiles et
  les mutations par parcelle répondent sans authentification, et SPEC §11.3 interdit de montrer
  une fiche de mutations à un tiers avant H4. Un `basic_auth` Caddy était l'alternative ; il
  entre en conflit avec le jeton Keycloak, qui passe par le même en-tête.
- **Pas d'Ansible sur cette machine** : `bootstrap` réécrit UFW, SSH et le noyau d'une machine
  qu'il croit vierge, et `deploy` hérite des six bloqueurs de `DEPLOYMENT.md` §2. La démo se
  déploie par un runbook court dans `DEPLOYMENT.md` ; `infra/ansible/` n'est pas touché, et
  la mesure sur la machine (étape 4) reste au porteur, qui seul y a accès.
- **Format de l'export** : un fichier SQL au format *plain* de `pg_dump` — sections `pre-data`
  et `post-data` de `pg_dump`, entre elles un `COPY` par table, lignes triées par clé primaire,
  puis les valeurs de séquence ; compressé par `gzip -n`, accompagné d'un manifeste SHA-256.
  Les clés étrangères sont en `post-data` : leur création à la restauration **prouve** la
  cohérence du sous-ensemble. Lecture dans une seule transaction `REPEATABLE READ`.
- **Une règle par table, sans exception silencieuse** : copie entière, filtre, ou schéma seul.
  Une table de la base sans règle fait échouer l'export.
- **Schéma seul** pour `app`, `audit` et `meta.matching_review_*` : comptes, organisations et
  identités de relecteurs n'ont rien à faire sur une démo.
- **Parent absent** : si la clé étrangère est `ON DELETE SET NULL`, la référence est exportée
  nulle, comme le schéma le prévoit quand le parent disparaît, et le nombre de références
  nullifiées est publié dans la preuve ; sinon la ligne est écartée, et comptée.
- **Couverture honnête** (critère « zone non couverte ») : le pointeur actif DS-01 ne couvre une
  commune que si elle a des parcelles, règle que la docstring de `commune_coverage` pose déjà
  pour les autres sources ; la fenêtre de carte n'est couverte que si une commune **ayant des
  parcelles** la coupe. Le second point corrige aussi la base complète, qui déclare aujourd'hui
  couverts les Côtes-d'Armor, le Finistère et le Morbihan.
- **`reference.area` entière** : les communes absentes restent nommées et situées, et la
  couverture les dit non couvertes.
- **Frontières, décidé après le recomptage** : un objet des cinq communes montre, sur la base
  complète, des bâtiments, bâtiments cadastraux, ventes et DPE d'autres communes. L'export les
  ajoute, sans jamais ajouter une parcelle d'une autre commune, qui ferait passer sa commune pour
  couverte. Sans cela, une parcelle de Rennes montrait 0 DPE contre 99.
- **Chargeur des tests de scripts** : `scripts/tests/conftest.py` inscrit le module dans
  `sys.modules`, sans quoi `dataclass` échoue sur un script chargé par son chemin.

## Résultat — 17 septembre 2026

Preuve : [`docs/data/demo-subset-35.md`](../data/demo-subset-35.md), recomptée.

- Export des cinq communes : 281 Mo compressés, empreinte stable d'un export à l'autre ; base
  restaurée de 2,70 Gio en 69 s, clés étrangères recréées sans orphelin.
- Stack démo sous 3,3 Gio de limites, 0,8 à 1,2 Gio consommés ; p95 des tuiles de Rennes à froid
  entre 2 et 104 ms selon le zoom, **sur le poste**.
- API démo identique à la base complète sur 72 parcelles tirées ou en bordure ; hors des cinq
  communes, `not_covered` et `outside_coverage`.
- `deploy-vps.yml` : job sauté sur `push` sans `VPS_HOST`.
- **Non fait ici** : l'étape 4 sur la machine cible, que seul le porteur peut exécuter → [A13](./A13-demo-mesuree-sur-le-vps.md).
- Défauts antérieurs trouvés par le recomptage : ordre variable des lots d'une vente →
  [BUG-21](./BUG-21-ordre-des-lots-non-deterministe.md) ; liste vide pour une parcelle inconnue →
  [BUG-22](./BUG-22-parcelle-absente-liste-vide.md).

## Ce qui rend le découpage abordable

`commune_code` est présent sur **21 tables**, dont toutes celles de `reference`, `observation` et
`tiles` qui pèsent. Le sous-ensemble est donc un **filtre**, pas un parcours de graphe. Quatre
exceptions demandent une jointure :

| Table | Rattachement |
|---|---|
| `feature.feature_value` | `property_unit_id` / `building_id` |
| `meta.entity_*` | `entity_id` |
| `observation.road_segment` | aucune commune — filtre spatial |
| tables de liaison (`building_parcel`, `property_unit_member`, `physical_building_member`) | par leurs parents |

## Sous-ensemble proposé

La stratification déjà utilisée par [B4](./B4-revue-manuelle-appariements.md) et
[D6](./D6-revue-manuelle-metier.md) — urbain, littoral, périurbain, ville moyenne, rural :

**35238 Rennes · 35288 Saint-Malo · 35047 Bruz · 35360 Vitré · 35211 Paimpont**

Mesuré, pas estimé :

| Table | Sous-ensemble | Total | Part |
|---|---|---|---|
| parcelles | 102 676 | 1 333 327 | 7,7 % |
| bâtiments | 83 905 | 741 379 | 11,3 % |
| adresses | 64 992 | 437 441 | 14,9 % |
| valeurs de features | 1 540 140 | 19 984 270 | 7,7 % |
| DPE | 96 433 | 208 086 | **46,3 %** |
| mutations DVF | 36 574 | 133 066 | **27,5 %** |
| risques | 742 | 10 824 | 6,9 % |

La réduction n'est pas uniforme, et c'est ce qui rend ce choix défendable : 7,7 % des parcelles
emportent près de la moitié des DPE et plus du quart des mutations, le parc et l'activité de marché
se concentrant sur Rennes, Saint-Malo et Vitré. Une démo dense plutôt qu'un échantillon anémique.

**Taille attendue : 3 à 4 Go**, index reconstruits. Le seul poste incertain est `meta`, dont la part
varie fortement selon le type d'entité — 3 % des observations de source, 8,6 % des identifiants. À
mesurer, pas à supposer.

## Travail à réaliser

1. **`scripts/export-demo-subset --commune …`** produisant un `pg_dump` restaurable. Ordre des clés
   étrangères respecté, sélection par `commune_code` là où il existe, par jointure ailleurs.
2. **`compose.demo.yaml`** : retire `dagster-code`, `dagster-webserver`, `dagster-daemon`, MinIO et
   l'observabilité, abaisse le réglage PostgreSQL au gabarit de la machine. Le backend ne référence
   ni `minio`, ni `boto3`, ni `redis` — vérifié le 15 septembre 2026 ; leur retrait est sans effet
   sur l'API. Il n'existe pas de profils Compose aujourd'hui : les noms `edge`, `app`, `data`,
   `ingestion`, `observability`, `backup` sont des **réseaux**.
3. **Conditionner `deploy-vps.yml`** à la présence des variables `VPS_*` au lieu d'échouer. Il est
   rouge à chaque push depuis au moins le 4 septembre — un workflow rouge en permanence rend
   invisible le jour où il rougit pour une vraie raison.
4. **Restaurer et mesurer** sur la machine cible : taille réelle, empreinte mémoire, p95 des tuiles
   sur Rennes.

## Points de vigilance

- **Une couverture partielle doit se déclarer partielle.** `meta.dataset_coverage_metric` filtré aux
  communes retenues, et les pointeurs `meta.active_dataset_release` / `active_regional_release`
  emportés avec le dump — sans eux l'API ne trouve plus de release active et l'application paraît
  cassée. Un sous-ensemble présenté comme le département est une affirmation fausse, au même titre
  qu'une donnée simulée présentée comme réelle.
- **Ne pas recalculer.** Les features sont matérialisées ; la démo restaure, elle n'importe pas.
  C'est ce qui permet de supprimer Dagster de la stack.
- **`reference.area`** est minuscule (332 communes) : la garder entière évite des liens brisés vers
  les EPCI et le département.
- Le premier déploiement réel de ce ticket est une occasion que
  [G6](./G6-exploitation-restauration.md) doit **réutiliser plutôt que refaire** — son exercice de
  restauration chronométrée sur VPS vierge en dépend directement.

## Dimensionnement attendu

| Service | Démo | `compose.prod.yaml` |
|---|---|---|
| PostgreSQL | 3 Go, `shared_buffers` 1 Go, `effective_cache_size` 3 Go | 12 Go |
| Keycloak | 1 Go | 2 Go |
| API, Martin, web, Caddy | 1,5 Go | 3,8 Go |
| Dagster ×3, MinIO, observabilité | supprimés | ~8 Go |

Cible : **4 vCPU / 8 Go / 80 Go SSD**. Le palier 2 vCPU / 4 Go reste à éprouver — il demanderait de
brider le tas de Keycloak et laisserait peu de marge sur les tuiles de Rennes.

## Critères d'acceptation

- l'export est reproductible : même liste de communes, même contenu, checksum stable ;
- la base restaurée pèse moins de 6 Go et la stack démarre sous 8 Go de RAM ;
- l'Explorer fonctionne sur les cinq communes : carte, recherche d'adresse, fiche, mutations, DPE,
  zonage, risques ;
- hors des cinq communes, l'application dit **zone non couverte** et ne présente pas une absence de
  donnée comme une absence d'objet — le comportement livré par [C2](./C2-zone-non-couverte.md) ;
- aucune métrique de couverture ne porte sur un territoire absent du dump ;
- `deploy-vps.yml` ne rougit plus quand les variables ne sont pas configurées.

## Hors périmètre

- **Le score.** Le schéma `scoring` pèse 488 ko et les deux définitions sont en
  `publication_eligible: false` : cette démo montre la **donnée**, pas le classement. Une démo qui
  montre le produit demande D6, puis E1, E2 et E3. Les deux chemins sont indépendants ; celui-ci
  n'attend rien.
- L'exercice de sauvegarde et de restauration chronométrée, qui reste à G6.
- Toute extension au-delà du 35, qui reste à [G1](./G1-extension-22-29-56.md).

## Preuve à produire

`docs/data/demo-subset-35.md` : communes retenues et leur justification, volumétries avant/après par
schéma, taille restaurée mesurée, empreinte mémoire observée, p95 des tuiles, et la liste explicite
de ce que la démo ne contient pas.
