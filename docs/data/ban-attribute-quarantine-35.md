# Quarantaine par attribut — déblocage de l'acceptation DS-05

**Date :** 4 septembre 2026
**Périmètre :** département 35, release `DS-05@2026-06-17`
**Ticket :** [BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md) — option C retenue

## Problème corrigé

L'importeur ne savait produire que deux états pour une ligne source : **valide** ou **en
quarantaine**. Le contrôle `conflicting_ban_identifier` exigeait « zéro conflit » et bloquait la
release entière, alors que ces conflits sont une propriété structurelle de la BAN : ils seront
présents dans le millésime suivant et dans ceux du 22, 29 et 56.

DS-05 ne pouvait donc jamais atteindre `accepted`, ce qui immobilisait v0.3, puis v0.4, puis
l'ensemble du chemin critique.

## Mesures sur l'archive réelle

Archive `adresses-35.csv.gz`, SHA-256 vérifié conforme au manifeste
[`2026-06-17-35.json`](../../contracts/datasets/DS-05/releases/2026-06-17-35.json)
(`22160b6d…ccc3d0`). Analyse conduite avec `iter_ban_records`, sans base de données.

| Mesure | Valeur |
|---|---:|
| Lignes normalisées | 437 679 |
| Quarantaines de parsing | 0 |
| Identifiants distincts | 437 441 |
| Identifiants répétés à l'identique | 8 (8 lignes en excès) |
| Identifiants conflictuels | 217 (447 lignes, 230 en excès) |
| Part des lignes conflictuelles | 0,102 % |
| Communes concernées | 82 sur 332 |
| **Conflits portant sur l'identité de l'adresse** | **0** |
| Conflits portant sur la position | 216 |

Écart entre positions d'un même identifiant : médiane **47,8 m**, p90 **252,9 m**, maximum
**3 128,5 m**. 28 identifiants seulement restent sous 10 m.

Détail identifiant par identifiant :
[`ban-conflicting-identifiers-35.csv`](./ban-conflicting-identifiers-35.csv) — 217 lignes, avec
commune, champs divergents et écart de position.

## Décision appliquée

L'identité de l'adresse est **stable et fiable** ; la géolocalisation ne l'est pas. L'attribut
devient donc manquant avec un motif, et l'enregistrement est conservé.

| Divergence | Traitement | Bloquant |
|---|---|---|
| Identité (`numero`, `rep`, `nom_voie`, `code_postal`, `code_insee`, `nom_commune`) | quarantaine de l'enregistrement, `conflicting_ban_identity` | **oui** |
| Position, relation parcellaire, type de position, certification | attribut retiré avec motif, adresse conservée | non |

Aucun seuil d'acceptation n'a été introduit sur la part d'attributs ambigus : le comportement du
produit est identique à 0,05 % comme à 5 %. Un seuil n'aurait de sens que comme alerte de
surveillance entre millésimes, jamais comme contrôle bloquant.

## Mise en œuvre

- migration [`20260904_0016_attribute_quarantine`](../../backend/migrations/versions/20260904_0016_attribute_quarantine.py) :
  table générique `meta.attribute_quarantine`, et `reference.address.geom` devenue nullable ;
- [`spatial/ban.py`](../../pipelines/src/immo_pipelines/spatial/ban.py) : `BAN_IDENTITY_FIELDS` et
  `identity_checksum`, qui séparent une divergence d'identité d'une divergence d'attribut ;
- [`spatial/importer.py`](../../pipelines/src/immo_pipelines/spatial/importer.py) :
  `BAN_QUARANTINABLE_ATTRIBUTES`, détection en deux phases, contrôles
  `conflicting_ban_identity` (bloquant) et `ambiguous_ban_attribute` (avertissement) ;
- l'attribut est retiré de **toutes** les variantes d'un identifiant : la déduplication qui suit
  ne choisit donc plus rien arbitrairement, les variantes restantes étant identiques ;
- la couche d'observation conserve la géométrie brute de chaque variante — l'évidence de la
  divergence reste auditable ;
- une adresse sans position ne fonde aucune relation **spatiale**. Elle conserve en revanche sa
  relation RNB fondée sur la clé d'interopérabilité, qui repose sur l'identité et non sur la
  géométrie ;
- API : `longitude` et `latitude` deviennent optionnelles et `position_status` porte le motif
  (FR-007). Contrat OpenAPI et client TypeScript régénérés.

## Généricité

Le mécanisme est délibérément indépendant de BAN : `meta.attribute_quarantine` porte
`entity_type`, `entity_id`, `attribute` et `reason_code`, sans référence à une source. Il est la
dépendance déclarée de D1 à D4, dont les anomalies relèvent du même troisième état :

| Source | Cas concerné |
|---|---|
| DS-06 DVF+ | mutation complexe non décomposable en prix unitaire |
| DS-07 DPE | diagnostic rattaché à l'adresse mais pas au bâtiment |
| DS-08 GPU | zones chevauchantes sans gagnant clair |
| DS-09 Géorisques | observation communale ne valant pas exposition parcellaire |

## Limites connues

**La fiabilité de l'identifiant lui-même est douteuse dans une partie des cas.** Un écart médian de
47,8 m entre deux positions du même identifiant n'est pas du bruit de géocodage : il suggère que
la BAN a fusionné deux adresses réellement distinctes sous un identifiant, ou qu'un identifiant a
été recyclé. `ambiguous_position` est donc un euphémisme. Cela ne change pas le traitement — on
conserve le libellé, on écarte la position — mais le cas n'est pas propre.

**Le contrôle bloquant de divergence d'identité vaut 0 sur le seul millésime observé.** Il n'a
jamais été déclenché par des données réelles ; il est couvert par un test sur donnée fabriquée, et
on ignore s'il se déclenchera un jour à bon escient.

**Le comportement SQL n'est pas couvert par un test automatisé.** Le dépôt n'a pas de banc d'essai
PostgreSQL : les suites `backend` et `pipelines` sont pures ou fondées sur le texte des migrations.
Les tests livrés couvrent la discrimination identité / attribut qui pilote ce SQL, ainsi que le
contrat de migration. **La vérification du comportement réel relève de l'import de
[B1](../backlog/B1-audit-ban-ds05.md)**, et doit y être explicitement relevée.

## Tests livrés

| Test | Couvre |
|---|---|
| `test_divergent_position_keeps_the_address_identity_intact` | cas réel majoritaire : 216 identifiants sur 217 |
| `test_divergent_address_label_breaks_the_identity` | garde-fou bloquant, sur donnée fabriquée |
| `test_divergent_parcel_relation_keeps_the_address_identity_intact` | divergence de `cad_parcelles` |
| `test_exact_duplicate_shares_both_checksums` | déduplication sans avertissement bloquant |
| `test_identity_checksum_ignores_every_quarantinable_attribute` | disjonction identité / attribut |
| `test_attribute_quarantine_migration_contract` (6 tests) | généricité, unicité, `geom` nullable, downgrade, rôle |
| `test_address_without_position_is_returned_unlocated_with_a_motive` | l'API renvoie l'adresse sans coordonnée et avec son motif (FR-007) |

`ruff check`, `pyright` et les 128 tests des deux suites passent.

## Défaut constaté hors périmètre

`ruff format --check` échoue sur deux fichiers **antérieurs** à ce travail et non modifiés par lui :
`backend/tests/test_scoring_optional_filters.py` et
`pipelines/tests/test_entity_match_schema_contract.py`. `make check` n'était donc pas vert avant
cette intervention. À traiter dans [A1](../backlog/A1-preuve-ci-github.md), dont c'est exactement
l'objet.
