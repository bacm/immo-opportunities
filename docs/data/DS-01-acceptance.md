# DS-01 — Rapport d’acceptation Cadastre Etalab

**Contrat :** [`contracts/datasets/DS-01/v1.json`](../../contracts/datasets/DS-01/v1.json)  
**Release cible :** `DS-01@2026-06-01`  
**Territoire cible :** département 35  
**État :** import départemental matérialisé, accepté et activé dans l’environnement local  
**Conclusion actuelle :** accepté pour les tests locaux ; aucun contrôle bloquant en échec.

## Droits d’usage

La source est publiée par la DGFiP et Etalab/DINUM sous Licence Ouverte 2.0. La réutilisation, y compris commerciale, et la production de données dérivées sont permises sous réserve de respecter l’attribution. Attribution retenue : « Données cadastrales Etalab, issues du PCI Vecteur DGFiP ».

Les données ouvertes contiennent le plan cadastral, pas les fichiers de propriétaires. Une emprise de bâti est une représentation cadastrale fiscale : elle peut être affichée et utilisée comme géométrie source, mais ne doit pas être présentée comme un bâtiment physique résolu. Le modèle la conserve donc dans `reference.cadastral_building`, distinct d’un futur `Building` résolu.

## Source et release

- page producteur : <https://cadastre.data.gouv.fr/datasets/cadastre-etalab> ;
- millésime figé : `2026-06-01`, sans alias `latest` ;
- format : GeoJSON compressé, EPSG:4326 ;
- cible canonique : EPSG:2154 ;
- assets du 35 : communes ~4 MiB, parcelles ~189 MiB, bâtiments ~51 MiB ;
- stockage : bucket privé et versionné `raw-sources`, clé contenant dataset, release, territoire, couche et SHA-256.

## Preuves exécutées

### Fixture minimale

Le 4 août 2026, `make cadastre-fixture COMPOSE_ENV_FILE=.env.example` a produit :

```json
{
  "archive_resume_verified": true,
  "canonical_reprojection_repairs": 1,
  "exact_duplicates_deduplicated": 1,
  "idempotent_skip": true,
  "incomplete_release_blocked": true,
  "normalized_rows_after_rollback": 0,
  "quarantined_rows": 1,
  "raw_assets_retained": 3,
  "valid_rows": 3
}
```

La fixture couvre Rennes (urbain), Pacé (périurbain) et Trimer (rural). Elle est explicitement simulée et ne satisfait pas le critère de données réelles.

### Fichier source réel

Le fichier officiel `cadastre-35346-parcelles.json.gz` de Trimer, release du 1er juin 2026, a été téléchargé temporairement et validé avec le contrat et la transformation de production :

```text
SHA-256    b08400d71e414abdaefffc137514c7a4902c601a29d549e319cdef2c87001d3f
source     839 parcelles
normalisé  839 parcelles
quarantaine 0
```

Sur l’asset départemental réel, 175 parcelles sur 1 333 327 omettent la propriété optionnelle
`contenance`; les 1 333 152 autres fournissent un entier. Cette nullité est conservée dans
`stated_area_m2` et comptabilisée par commune dans le contrôle `parcel_count`.

### Import départemental complet

La partition `release=2026-06-01 | department=35` contient :

| Couche | Source | Normalisé | Quarantaine | Dédupliqué | SHA-256 |
|---|---:|---:|---:|---:|---|
| Communes | 332 | 332 | 0 | 0 | `e704ff62739c6371bbcbe857635c2ade60b70134709f637886b7332f8c1b1bf0` |
| Parcelles | 1 333 327 | 1 333 327 | 0 | 0 | `ef8ea1a4ccaf709662c7276ed32ce18d4c46f9ef1b9701bd80f8c05449b5dcf1` |
| Bâtiments | 865 418 | 865 335 | 0 | 83 | `ecc71585cd6654f3bd4f3c278914dcca4cde429e03181aa88cccbc044d826497` |

Les 83 bâtiments écartés sont des répétitions exactes du même enregistrement canonique. Ils sont
comptés comme dédupliqués et produisent un avertissement non bloquant. Une réutilisation du même
identifiant avec un contenu différent reste un échec bloquant. La reprojection a nécessité une
réparation traçable pour 38 parcelles et 51 bâtiments.

Les trois archives représentent 255 191 903 octets compressés. Les relations PostGIS locales,
index inclus, occupent environ 10 MiB pour les communes, 1 195 MiB pour les parcelles et 847 MiB
pour les bâtiments.

### Base et services

- migration v0.2 appliquée sur la base locale existante sans interruption des autres volumes ;
- cycle `upgrade → downgrade 20260804_0001 → upgrade` réussi dans une base temporaire isolée ;
- import PostGIS/MinIO, idempotence, quarantaine et rollback non publié vérifiés ;
- smoke test complet réussi après redémarrage ciblé de l’API et de Dagster ;
- l’API locale retourne la parcelle réelle `35238000AB0001` et sa provenance complète ;
- Martin expose `cadastral_parcels` et `cadastral_buildings` ; la tuile Rennes
  `14/8115/5687` répond `200` avec 359 826 octets ;
- réseau d’egress `ingestion` réservé à `dagster-code` pour joindre les sources publiques, tout en
  maintenant PostgreSQL et MinIO sur leurs réseaux internes ;
- Martin peut lire `tiles.cadastral_parcels`, mais pas `reference`, `app` ou `audit` ;
- `api_rw` lit le référentiel sans l’écrire ; `pipeline_rw` l’alimente ; `backup_ro` peut l’exporter.

## Décision locale

Les décisions possibles restent :

- `accepted` : contrôles bloquants réussis, données utilisables pour l’analyse et l’affichage ;
- `display_only` : qualité insuffisante pour l’analyse mais acceptable pour le contexte visuel ;
- `rejected` : release non activable.

La release a été enregistrée en mode `accepted` puis activée pour le département 35 par
`local-admin`, avec la raison « Validation locale complète DS-01 ». Cette activation ne concerne
que la base Docker locale.

La publication ne réécrit aucune ligne source : elle déplace atomiquement le pointeur
`meta.active_dataset_release`. Elle **aligne en revanche les identités canoniques** sur la release
devenue active — `reference.area`, `reference.parcel`, `reference.property_unit`,
`reference.property_unit_member` et `meta.entity_source_identifier` — par un upsert exécuté dans
la même transaction que le déplacement du pointeur. Il n'existe donc pas d'état où le pointeur
désigne une release que le référentiel canonique ne décrit pas.

Cet alignement dépendait jusqu'au 4 septembre 2026 d'un appel manuel à
`reference.refresh_cadastre_spatial_reference`, sans appelant applicatif — voir
[BUG-04](../backlog/BUG-04-propagation-referentiel-spatial.md). Deux conséquences pratiques :
publier DS-01 rejoue 1,33 M upserts et n'est plus instantané — 2 min 11 s mesurées sur le 35 —
et `cadastre_release.py publish`
imprime désormais les volumes propagés, ce qui rend la propagation vérifiable au lieu d'être
supposée.

## Reste à exécuter

- réaliser l’échantillon visuel urbain, périurbain et rural ;
- mesurer une durée d’import fiable lors de la prochaine release ; les timestamps de ce premier
  import utilisaient l’horloge transactionnelle et ne permettent pas de calculer le débit ;
- comparer les comptes et distributions lorsqu’une deuxième release sera disponible.
