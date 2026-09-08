# BUG-08 — Une release remplacée n'est jamais retirée

**Version :** dette transverse · **Taille :** M · **État :** À faire
**Dépend de :** — · **Bloque :** —
**Découvert par :** question de dimensionnement, 8 septembre 2026

## Contexte à charger

- `backend/migrations/versions/20260804_0002_cadastre_catalog.py`
  (`meta.rollback_unpublished_dataset_release`)
- `backend/migrations/versions/20260805_0005_spatial_reference.py`
  (contraintes `ON DELETE` de `meta.entity_source_observation`)
- `pipelines/src/immo_pipelines/cadastre/catalog.py` (`rollback_unpublished`)

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Rien ne retire les données d'une release remplacée. Au prochain millésime BD TOPO, l'import
ajoutera 974 172 observations **sans retirer les 974 172 précédentes**.

Ce n'est pas une fuite : c'est l'`append-only by release` que les contrats déclarent, et il sert
la reproductibilité. Le défaut est qu'aucune sortie n'existe, et que rien ne le signale.

## Ce qui existe, et ce qui manque

`meta.rollback_unpublished_dataset_release` purge bien une release, mais seulement les tables
**DS-01** :

```sql
DELETE FROM reference.cadastral_parcel     WHERE release_id = ...
DELETE FROM reference.cadastral_building   WHERE release_id = ...
DELETE FROM reference.administrative_area  WHERE release_id = ...
DELETE FROM meta.data_quality_check        WHERE release_id = ...
DELETE FROM meta.import_run                WHERE release_id = ...
```

Aucune ligne ne touche `meta.entity_source_observation`, `meta.entity_source_identifier`,
`meta.entity_match` ni `meta.entity_observation_link` — soit **10 Go sur les 17** de la base du
seul département 35, où vivent DS-02 à DS-05.

Deux limites s'ajoutent, toutes deux voulues :

- la fonction refuse de purger une release **publiée** (`has publication history and cannot be
  purged`), ce qui protège l'immuabilité ;
- `entity_source_observation.release_id` est en `ON DELETE RESTRICT` : la ligne de release ne peut
  pas être supprimée tant que ses observations existent.

## Mesure

Base du 35 au 8 septembre 2026 : 17 Go, une seule release par source. Un tour complet de
millésimes sur les cinq sources spatiales ajouterait environ **7 Go**, sans rien retirer.

## La question est produit, pas technique

Le sujet n'est pas d'économiser du disque — il est bon marché, et la base ne contient aucun
déchet : zéro tuple mort, aucune duplication. La question est : **que devient une release
remplacée ?**

| Option | Conséquence |
|---|---|
| Tout garder | volume prévisible, historique complet, aucune décision à prendre |
| Garder les N derniers millésimes | borne le volume, mais fixe une profondeur arbitraire |
| Retirer sur décision explicite | cohérent avec le reste du modèle, demande un geste et une trace |

Aucune n'est évidente, et la troisième ressemble le plus au reste du système — l'acceptation et la
publication sont déjà des gestes explicites et tracés.

## Travail à réaliser

1. Trancher la question ci-dessus.
2. Étendre la purge aux tables spatiales, ou documenter explicitement pourquoi elle s'arrête à
   DS-01.
3. Décider du sort d'une release **publiée** puis remplacée — le cas que la fonction refuse
   aujourd'hui, et qui est pourtant le cas normal d'un changement de millésime.
4. Rendre le volume par release visible à l'administration, pour que la décision s'appuie sur un
   chiffre.

## Tests obligatoires

- purger une release non publiée retire ses observations spatiales, pas seulement DS-01 ;
- une release publiée reste protégée ;
- le référentiel actif n'est jamais affecté par la purge d'une autre release.

## Critères d'acceptation

- le sort d'une release remplacée est décidé et documenté ;
- aucune donnée ne subsiste sans que quelqu'un ait décidé qu'elle subsiste.

## Ce que ce ticket n'est pas

Une optimisation de taille. La base ne contient aucun déchet aujourd'hui, et la réduire n'apporte
rien : le disque est la ressource la moins chère de la stack. Ce ticket porte sur un **trou dans
le cycle de vie**, qui se manifestera au premier remplacement réel — v0.8 au plus tard.
