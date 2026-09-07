# BUG-05 — DS-02 RNB n'est pas reproductible : l'URL épinglée est un alias mouvant

**Version :** v0.3 · **Taille :** M · **État :** Terminé
**Dépend de :** — · **Bloque :** B2b (volet appariement), toute reconstitution locale de DS-02
**Découvert par :** B2b, 4 septembre 2026

## Contexte à charger

- `contracts/datasets/DS-02/releases/2026-08-01-35.json`
- `docs/operations/referentiel-local-35.md` (§3)
- `docs/data/spatial-sources-audit.md` (§DS-02)
- `pipelines/scripts/import_rnb_release.py`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

`make rnb-import DEPARTMENT=35` échoue sur une base fraîche :

```text
ChecksumMismatchError: Expected sha256 b40a4d474d6cbc4cfec2aa8460714675f33349b3cd1e97b3dad4e7b7883d0751,
                       got      f979bc6b27c9050890d82c022712c1d4c98de0d324185a8cbd18474758f14d8c
```

Le garde-fou fonctionne : il refuse d'importer des octets qui ne sont pas ceux qui ont été
acceptés. Le défaut est en amont.

## Cause

Le manifeste `DS-02@2026-08-01` épingle une URL qui **n'est pas datée** :

```text
https://rnb-opendata.s3.fr-par.scw.cloud/files/RNB_35.csv.zip
```

Mesures du 4 septembre 2026 :

| | Manifeste | Amont aujourd'hui |
|---|---:|---:|
| taille | 190 932 054 | 191 011 813 |
| `last-modified` | — | 29 août 2026 |

Le listing du bucket ne contient que `files/RNB_<dept>.csv.zip` : **aucun objet daté n'existe**.
L'URL est un alias par construction, exactement ce que `latest_alias_forbidden_for_reproducible_imports`
interdit. Le producteur écrase le fichier à chaque millésime.

Le défaut est resté invisible parce que l'archive immuable avait été déposée dans MinIO lors du
premier import. Une base et un object store frais — le cas d'une copie neuve du dépôt — n'ont plus
rien : `raw-sources` ne contient que DS-01 et DS-05.

## Portée réelle

- **DS-02@2026-08-01 n'est plus reproductible.** Les 741 376 bâtiments et 1 240 351 relations
  bâtiment–parcelle publiés comme preuve ne peuvent pas être recalculés depuis le dépôt.
- L'acceptation de DS-02 reposait sur ces octets. Elle n'est pas fausse ; elle n'est plus vérifiable.
- Tout ticket qui apparie contre l'identité bâtiment canonique en dépend : B2b, B3, B4, B5.
- `docs/operations/referentiel-local-35.md` §3 décrit une séquence qui ne fonctionne plus.

Le même risque existe pour DS-01, déjà signalé : ses trois couches portent `"sha256": null`.
BUG-05 en est la démonstration sur une autre source.

## Décision prise le 7 septembre 2026

**Option 3 retenue comme mécanisme, option 1 comme sa conséquence.** Les deux ne sont pas des
alternatives : l'archive porte la reproductibilité, et il faut de surcroît épingler des octets
qu'on détient. L'option 2 est écartée, faute d'objet récupérable.

Deux mesures ont tranché :

| Fait mesuré | Conséquence |
|---|---|
| Le listing `?versions` du bucket ne renvoie qu'une version | option 2 impossible |
| Le fichier a changé deux fois en dix jours — 190 932 054 (manifeste) → 191 011 813 (29 août) → 191 084 366 (5 septembre) | l'option 1 seule serait périmée sous huit jours |

Le RNB est une base continûment mise à jour, sans millésime : le producteur ne fournira jamais la
reproductibilité. Soit on renonce à DS-02, soit le projet archive. L'architecture avait déjà
tranché — `meta.raw_asset` et MinIO en `immutable: true` — mais le manifeste versionné ne nommait
que l'URL amont, et le chemin vers l'archive ne vivait que dans la base. Base perdue, aucun retour.

## Décision d'origine — options soumises

| Option | Avantage | Inconvénient |
|---|---|---|
| Épingler le millésime courant en `DS-02@2026-08-29` | reproductible immédiatement | l'acceptation DS-02 et ses volumétries publiées sont à refaire ; B1 a mesuré contre l'ancien |
| Retrouver les octets du 1er août 2026 | conserve les preuves existantes | aucun objet daté côté producteur ; probablement irrécupérable |
| Archiver l'amont dans MinIO à chaque millésime et le documenter comme la seule copie | rend le problème visible et gérable | l'archive locale devient la source de vérité, à sauvegarder |

Aucune de ces options n'est neutre pour les preuves déjà publiées. C'est une décision produit.

## Travail réalisé

1. **Décision tranchée** ci-dessus.
2. **Le manifeste nomme la copie archivée.** Nouveau module
   [`cadastre/manifest.py`](../../pipelines/src/immo_pipelines/cadastre/manifest.py) : chargement,
   garde de reproductibilité, résolution de l'asset. La résolution essaie l'archive enregistrée en
   base, puis la copie nommée par le manifeste, puis l'amont — l'amont en dernier parce que c'est
   le seul chemin qui peut avoir changé. Chaque import imprime désormais `asset_origin`.
3. **Le contrôle est étendu à toutes les sources.** Un asset sans SHA-256, ou dont l'URL n'est pas
   datée et qui ne nomme aucune archive, est refusé **avant tout téléchargement**. Les trois
   couches de DS-01 portaient `"sha256": null` : leurs checksums, consignés dans
   [`DS-01-acceptance.md`](../data/DS-01-acceptance.md), ont été re-vérifiés contre le répertoire
   daté d'Etalab — les trois sont conformes, le répertoire est bien immuable — puis inscrits au
   manifeste.
4. **DS-02 ré-épinglé** en `DS-02@2026-09-05`, clé dérivée du `last-modified` de l'objet source :
   deux opérateurs archivant les mêmes octets obtiennent la même clé. `DS-02@2026-08-01` est
   conservé, marqué `withdrawn`, et refusé à l'import — c'est la trace de ce qui avait été
   accepté, pas une release utilisable.
5. **La duplication qui masquait le défaut est résorbée.** Les trois chemins d'import — asset
   Dagster DS-01, scripts DS-02 et DS-05 — recopiaient la même trentaine de lignes de résolution.
   Ils passent tous par `resolve_asset`.
6. `docs/operations/referentiel-local-35.md` corrigé, ainsi que l'audit spatial.

## Ce que la correction ne résout pas

Le dépôt seul ne suffit toujours pas à reconstituer DS-02 : sur une plateforme dont MinIO n'a pas
été restauré, la release n'est réimportable que tant que le producteur sert encore les mêmes
octets. C'est la nature de la source, pas un défaut résiduel — et c'est pourquoi le ré-épinglage
était nécessaire en plus de l'archive. La sauvegarde de `raw-sources` porte la garantie dans le
temps : `scripts/backup-platform` la couvre déjà en entier,
[G6](./G6-exploitation-restauration.md) en chronomètre la restauration.

**Cadence de ré-instantanéisation, à la main du produit :** ne re-snapshotter que lorsqu'on veut
délibérément de la donnée plus fraîche. Chaque nouvel instantané invalide les volumétries mesurées.

## Tests obligatoires

- un manifeste dont l'URL n'est pas datée et sans copie archivée est refusé avant téléchargement ;
- une reconstitution sur base **et** object store vides est vérifiée de bout en bout.

## Critères d'acceptation

- ✅ l'impossibilité de reconstituer DS-02 depuis le dépôt seul est documentée, et la release est
  ré-épinglée sur des octets vérifiables ;
- ✅ aucune source ne dépend plus d'une URL mouvante sans archive nommée ;
- ✅ 16 tests de régression dans
  [`test_release_manifest.py`](../../pipelines/tests/test_release_manifest.py) ;
- ✅ import réel rejoué de bout en bout sur le 35 : 741 379 bâtiments, 1 240 355 relations,
  0 en quarantaine, archive déposée sous la clé nommée par le manifeste.

## Conséquence pour les preuves existantes

Les 741 376 bâtiments et 1 240 351 relations bâtiment–parcelle du
[rapport spatial 35](../data/spatial-reference-35-report.md) portaient sur les octets du 1er août.
Ils sont à re-mesurer sur `DS-02@2026-09-05` — travail de [B3](./B3-rapport-appariements.md).

Le verdict `display_only` de DS-05 **n'est pas affecté** : ses relations parcellaires se résolvent
contre la géométrie cadastrale DS-01, et le volet adresse↔bâtiment est une jointure qui ne produit
aucune ligne en l'absence d'observations DS-02, sans échouer.
