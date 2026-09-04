# BUG-03 — Le modèle de quarantaine ne connaît que l'enregistrement, pas l'attribut

**Version :** v0.3 · **Taille :** M · **État :** Terminé
**Bloque :** B1, C1, et par transitivité tout le chemin critique
**Sera réutilisé par :** D1, D2, D3, D4

## Contexte à charger

- `pipelines/src/immo_pipelines/spatial/ban.py`
- `pipelines/src/immo_pipelines/spatial/importer.py`
- `contracts/datasets/DS-05/v1.json`
- `pipelines/tests/test_ban.py`

Ne rien charger d'autre sans nécessité démontrée.

## Nature du problème

Le symptôme est apparu sur BAN, mais la cause n'est pas propre à BAN.

L'importeur ne sait produire que deux états pour une ligne source : **valide** ou **en quarantaine**.
Or une grande partie des anomalies réelles se situe entre les deux : l'enregistrement est bon, un
seul de ses attributs est inutilisable. Sans troisième état, il faut choisir entre jeter une
information certaine et publier une information douteuse — les deux étant contraires à la règle
« une valeur manquante reste manquante avec un motif ».

Ce cas n'a rien d'exceptionnel, il est structurel et va se répéter à chaque source de v0.5 :

| Source | Cas « enregistrement bon, attribut inutilisable » |
|---|---|
| DS-05 BAN | identifiant réutilisé avec des positions divergentes |
| DS-06 DVF+ | mutation complexe non décomposable en prix unitaire |
| DS-07 DPE | diagnostic rattaché à l'adresse mais pas au bâtiment (`ambiguous_match`) |
| DS-08 GPU | zones chevauchantes sans gagnant clair |
| DS-09 Géorisques | observation communale ne valant pas exposition parcellaire |

**BAN est simplement le premier endroit où l'absence de ce mécanisme bloque.** C'est ce qui
justifie le travail, bien plus que les 217 adresses concernées.

## Symptôme observé sur BAN

Le contrôle `conflicting_ban_identifier` est enregistré avec `severity = 'error'` et
`is_blocking = true` dès qu'au moins un identifiant conflictuel est détecté :

```sql
-- pipelines/src/immo_pipelines/spatial/importer.py:204-209
CASE WHEN %(conflicting_identifier_count)s = 0 THEN 'passed' ELSE 'failed' END,
CASE WHEN %(conflicting_identifier_count)s = 0 THEN 'info'   ELSE 'error'  END,
```

Le seuil est donc « zéro conflit », posé sur une propriété **statistique** de la source. Ces
conflits seront présents dans le millésime suivant et dans ceux du 22, 29 et 56 : la release DS-05
ne peut jamais atteindre `accepted`, ce qui bloque v0.3, puis v0.4, puis tout le reste.

## Mesures sur l'archive réelle

Archive `adresses-35.csv.gz`, release `DS-05@2026-06-17`, SHA-256 vérifié conforme au manifeste
[`contracts/datasets/DS-05/releases/2026-06-17-35.json`](../../contracts/datasets/DS-05/releases/2026-06-17-35.json)
(`22160b6d…ccc3d0`). Analyse effectuée avec `iter_ban_records` du dépôt, sans base de données.

| Mesure | Valeur |
|---|---:|
| Lignes normalisées | 437 679 |
| Quarantaines de parsing | 0 |
| Identifiants distincts | 437 441 |
| Identifiants répétés à l'identique | 8 (8 lignes en excès) |
| Identifiants conflictuels | 217 (447 lignes, 230 en excès) |
| Part des lignes conflictuelles | 0,102 % |
| Communes concernées | 82 sur 332 |

**Nature des divergences** — aucun conflit ne porte sur l'identité de l'adresse :

| Champs divergents | Identifiants |
|---|---:|
| `lat, lon, x, y` | 53 |
| `cad_parcelles, lat, lon, x, y` | 52 |
| `lat, lon, type_position, x, y` | 36 |
| `certification_commune, lat, lon, x, y` | 28 |
| `cad_parcelles, lat, lon, type_position, x, y` | 26 |
| autres combinaisons position / parcelle / certification | 21 |
| `certification_commune` seul | 1 |

- **0** identifiant sur 217 présente une divergence de `numero`, `rep`, `nom_voie`,
  `code_postal`, `code_insee` ou `nom_commune` ;
- **216** présentent des positions divergentes : écart médian **47,8 m**, p90 **252,9 m**,
  maximum **3 128,5 m** ; 28 identifiants seulement restent sous 10 m ;
- **11** identifiants seulement portent une relation `cad_parcelles` non vide et stable entre
  leurs variantes — l'enjeu de préservation des relations déclarées est donc négligeable.

Le libellé de l'adresse est stable et fiable, **la géolocalisation ne l'est pas**.

## Décision retenue — option C

| Option | Effet | Verdict |
|---|---|---|
| A — statu quo | le contrôle reste bloquant au niveau release | **écartée** — immobilise le projet |
| B — quarantaine de ligne | les 447 lignes sont écartées | **écartée** — jette une identité certaine et ne résout rien pour D1–D4 |
| **C — quarantaine d'attribut** | l'identité d'adresse est conservée, la **position** devient manquante avec le motif `ambiguous_position` | **retenue** |

Sous l'option C, une adresse sans position :
- reste cherchable par libellé (FR-001) ;
- n'est pas affichable sur la carte et doit le signaler explicitement (FR-007) ;
- ne fonde aucune relation spatiale `adresse ↔ parcelle`, qui reste absente avec motif.

L'option C n'est pas retenue pour préserver 216 adresses sur 437 441 — cet enjeu est nul. Elle est
retenue parce qu'elle construit le troisième état de quarantaine dont D1 à D4 auront besoin de
toute façon. **L'implémentation doit rester minimale en conséquence :** ces 217 adresses ne méritent
aucun raffinement particulier.

## Limite connue à documenter

Un écart médian de 47,8 m entre deux positions du même identifiant n'est pas du bruit de
géocodage : c'est trop grand. Cela suggère que la BAN a fusionné deux adresses réellement distinctes
sous un identifiant, ou qu'un identifiant a été recyclé entre millésimes.

`ambiguous_position` est donc un euphémisme : dans une partie des cas, c'est l'**identité** qui est
douteuse, pas seulement la position. Cela ne change pas la décision — on conserve le libellé, on
écarte la position — mais le cas doit être présenté comme une limite connue, pas comme un cas propre.

## Travail à réaliser

1. Introduire un état de quarantaine **par attribut**, distinct de la quarantaine par
   enregistrement, dans [`spatial/ban.py`](../../pipelines/src/immo_pipelines/spatial/ban.py) et
   [`spatial/importer.py`](../../pipelines/src/immo_pipelines/spatial/importer.py). Le concevoir
   comme un mécanisme générique réutilisable, pas comme un cas BAN.
2. Reclasser `conflicting_ban_identifier` en `warning` non bloquant.
3. Ajouter un contrôle bloquant sur ce qui doit réellement l'être : la divergence d'**identité**
   d'adresse entre variantes d'un même identifiant.
4. Propager le motif `ambiguous_position` jusqu'à l'API et l'UI (FR-007).
5. Ne pas introduire de seuil d'acceptation sur la part de positions ambiguës — voir ci-dessous.

### Pas de seuil d'acceptation sur cette dimension

Une version antérieure de ce ticket demandait que « la part de positions ambiguës admissible vienne
du profiling ». C'était une erreur : elle réintroduisait exactement le vice à corriger, un nombre
choisi qui bloque une release.

Dès lors que le mécanisme d'absence motivée fonctionne, le comportement du produit est identique à
0,05 % comme à 5 % de positions ambiguës. Aucun seuil d'acceptation n'est donc nécessaire.

Un seuil garde du sens pour un **autre usage** : détecter une régression entre millésimes — « la
source s'est brutalement dégradée, allez voir ». Il doit alors être formulé comme une alerte de
surveillance, jamais comme un contrôle bloquant.

### Réserve sur le nouveau contrôle bloquant

Le contrôle de divergence d'identité vaut **0 sur le seul millésime observé**. C'est un garde-fou
qui ne s'est jamais déclenché, donc jamais éprouvé en conditions réelles. Il doit être couvert par
un test sur donnée fabriquée, et on doit assumer qu'on ignore s'il se déclenchera un jour à bon escient.

## Tests obligatoires

- un identifiant réutilisé avec position divergente produit une adresse conservée et une position
  absente motivée — jamais une position moyennée ni choisie ;
- un identifiant réutilisé avec libellé divergent bloque la release (test sur donnée fabriquée,
  ce cas étant absent du millésime réel) ;
- un identifiant répété à l'identique est dédupliqué sans avertissement bloquant ;
- une adresse sans position n'entre dans aucune relation spatiale ;
- réimport de la même archive : identifiants internes stables, mêmes motifs, mêmes compteurs ;
- l'API n'expose jamais une adresse conflictuelle avec une position arbitraire.

## Critères d'acceptation

- l'état de quarantaine par attribut existe et est générique, non spécifique à BAN ;
- la release `DS-05@2026-06-17` sur le 35 atteint un verdict explicite ;
- les 217 identifiants sont traçables individuellement avec leur motif ;
- aucun seuil d'acceptation n'a été introduit sur la part de positions ambiguës ;
- la limite connue sur la fiabilité des identifiants est documentée ;
- une note ADR est écrite si la règle d'acceptation des releases s'en trouve modifiée.

## Preuves produites

- [rapport de quarantaine par attribut](../data/ban-attribute-quarantine-35.md) — mesures,
  décision, mise en œuvre, limites connues ;
- [table des 217 identifiants](../data/ban-conflicting-identifiers-35.csv) avec commune, champs
  divergents et écart de position ;
- section DS-05 de [`spatial-sources-audit.md`](../data/spatial-sources-audit.md) mise à jour ;
- migration [`20260904_0016`](../../backend/migrations/versions/20260904_0016_attribute_quarantine.py) ;
- contrat OpenAPI et client TypeScript régénérés (`longitude` / `latitude` optionnelles,
  `position_status` ajouté).

Le contrat DS-05 n'a pas été versionné : aucun seuil d'acceptation n'a été introduit ni modifié,
la règle changée vit dans l'importeur et ses contrôles qualité.

## Reste à vérifier en B1

Le comportement SQL n'est pas couvert par un test automatisé — le dépôt n'a pas de banc d'essai
PostgreSQL. Les compteurs attendus lors de l'import réel du 35 sont : 0 identité conflictuelle,
217 identifiants portant au moins un attribut retenu, 437 441 adresses normalisées, 238 lignes
dédupliquées. Tout écart est un défaut à instruire.
