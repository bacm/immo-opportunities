# BUG-04 — Publier DS-01 ne propage pas le référentiel spatial canonique

**Version :** v0.3 · **Taille :** S · **État :** Terminé
**Découvert par :** B1
**Fichier concerné :** [`pipelines/src/immo_pipelines/cadastre/catalog.py`](../../pipelines/src/immo_pipelines/cadastre/catalog.py)

## Contexte à charger

- `pipelines/src/immo_pipelines/cadastre/catalog.py`
- `backend/migrations/versions/20260805_0006_spatial_storage_and_features.py` — la seule
  définition vivante de `reference.refresh_cadastre_spatial_reference`
- `pipelines/tests/test_release_acceptance_gate.py`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

`reference.refresh_cadastre_spatial_reference(department_code)` n'avait **aucun appelant
applicatif**. La fonction existait, était testée en contrat de migration, et n'était invoquée
que par un opérateur qui pensait à la lancer à la main.

Conséquence : `catalog.publish()` déplaçait `meta.active_dataset_release` sans que
`reference.area`, `reference.parcel`, `reference.property_unit`,
`reference.property_unit_member` et `meta.entity_source_identifier` suivent. Le pointeur
désignait une release que le référentiel canonique ne décrivait pas.

Le défaut ne se voyait pas localement parce que l'appel manuel avait été fait une fois, le
4 septembre 2026, avant l'import BAN. Il se serait vu au premier millésime cadastral suivant, et
à chaque département ajouté par [G1](./G1-extension-22-29-56.md).

## Nature du problème

Ce n'est pas un oubli d'appel dans un script : c'est une responsabilité non attribuée. Aucune
couche ne possédait l'invariant « les identités canoniques décrivent la release DS-01 active ».
La fonction SQL sait l'établir, la publication sait quand il change, et rien ne les reliait.

## Résolution — 4 septembre 2026

`DatasetCatalog.publish()` propage désormais, **dans la transaction qui déplace le pointeur** :

```python
counts = (
    self._propagate_cadastre_spatial_reference(department_code)
    if data_source_id == "DS-01"
    else None
)
```

Quatre propriétés, chacune nécessaire :

- **après** le déplacement du pointeur — la fonction lit `meta.active_dataset_release`, et ne
  verrait rien d'utile avant ;
- **dans la même transaction** — un échec de propagation annule la publication ; il n'existe
  aucune fenêtre où le pointeur avance seul ;
- **entre `SET LOCAL ROLE pipeline_rw` et `RESET ROLE`** — `EXECUTE` n'est accordé qu'à ce rôle ;
- **DS-01 seulement** — la fonction lit `'DS-01'` en dur et alimente les identités parcellaires.
  Publier DS-05 ne doit rien y déclencher.

La propagation vaut aussi pour `action='rollback'` : un retour arrière déplace le pointeur autant
qu'une publication, le référentiel doit suivre dans les deux sens.

`publish()` retourne les volumes propagés (`SpatialReferenceCounts`), que
`pipelines/scripts/cadastre_release.py publish` imprime. La propagation devient observable au lieu
d'être supposée.

### Tests

| Test | Ce qu'il verrouille |
|---|---|
| `test_publishing_a_cadastre_release_propagates_the_spatial_reference` | publier DS-01 interroge la fonction et retourne ses volumes |
| `test_propagation_runs_inside_the_publication_transaction_as_pipeline_rw` | ordre `SET LOCAL ROLE` → publication → propagation → `RESET ROLE`, et aucun commit intermédiaire |
| `test_publishing_a_non_cadastre_release_propagates_nothing` | DS-05 ne déclenche rien, `publish()` retourne `None` |
| `test_a_rollback_publication_realigns_the_spatial_reference_too` | le retour arrière propage aussi |

### Vérification sur données réelles

Une sentinelle a été posée sur la seule colonne que la propagation réécrit :
`reference.area.name` de la commune `35238` mise à `SENTINELLE-PROPAGATION`. Publier
`DS-01@2026-06-01` sur le 35 l'a ramenée à `RENNES`, ce qui prouve que l'upsert écrit réellement,
sous `pipeline_rw`, et non qu'il est seulement appelé.

Sortie du script :

```json
{"action": "publish", "department": "35", "release_id": "DS-01@2026-06-01",
 "spatial_reference": {"area_count": 332, "parcel_count": 1333327,
                       "property_unit_count": 1333327}}
```

Volumes inchangés après propagation (332 / 1 333 327 / 1 333 327), `meta.publication_event`
incrémenté, DS-05 toujours en `display_only`.

### Limites

- **La propagation est additive.** Elle insère et met à jour, elle ne retire jamais une identité
  qui a quitté la release active. Ce n'est pas une corruption : les vues
  `reference.parcel_geometry` et `reference.property_unit_geometry` étant portées par la release
  active, une parcelle disparue perd sa géométrie et devient une identité sans géométrie — l'état
  que B1 nomme `unpublished_parcel_geometry`. Une valeur manquante reste manquante avec un motif.
  Retirer ces identités demanderait une décision de cycle de vie qui n'est pas prise ici.
- **Publier DS-01 n'est plus instantané** : la propagation traverse 1,33 M parcelles dans la
  transaction de publication. Mesurée à **2 min 11 s** sur le 35, référentiel déjà aligné — donc
  sur des upserts sans effet ; une première population n'a pas été chronométrée séparément. Sur un
  département c'est acceptable ; à l'échelle Bretagne, [G1](./G1-extension-22-29-56.md) devra
  décider si la publication reste synchrone ou devient un asset Dagster distinct.
- Le passage des scripts d'import à Dagster reste [BUG-02](./BUG-02-scripts-import-hors-dagster.md).
