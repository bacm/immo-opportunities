# A6 — Démo déployable : un sous-ensemble de communes sur une petite machine

**Version :** transverse · **Taille :** L · **État :** À faire
**Touche :** scripts/export-demo-subset, compose.demo.yaml, docs/data/demo-subset-35.md, .github/workflows/deploy-vps.yml, infra/ansible/playbooks/deploy.yml, DEPLOYMENT.md
**Dépend de :** — · **Bloque :** —
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
