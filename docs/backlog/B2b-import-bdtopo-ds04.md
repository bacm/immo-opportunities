# B2b — Importer et auditer DS-04 BD TOPO sur le 35

**Version :** v0.3 · **Taille :** L · **État :** Terminé
**Dépend de :** BUG-05 · **Bloque :** B3, B5

## Contexte à charger

- `contracts/datasets/DS-04/v1.json`
- `docs/data/spatial-sources-audit.md` (§DS-04)
- `pipelines/src/immo_pipelines/spatial/importer.py`
- `pipelines/src/immo_pipelines/spatial/resolution.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DS-04 n'a qu'un contrat. L'audit note : « aucun export départemental daté et checksumé n'est encore
inscrit dans le dépôt » et « le téléchargement dynamique ou le WFS peuvent servir à découvrir la
donnée, mais ne satisfont pas seuls la reproductibilité ».

Comme pour BDNB, les 604 098 identifiants BD TOPO présents dans le RNB sont des références
observées et **ne valent pas import**.

Couches attendues : `BATIMENT` et `TRONCON_DE_ROUTE`.

## Conséquence actuelle de l'absence

Les bâtiments légers et la voirie restent des **valeurs manquantes**, jamais des zéros. Concrètement,
toute feature morphologique dépendant de l'accès à la voirie ne peut pas être calculée
aujourd'hui — c'est un manque assumé et motivé, à ne pas contourner.

## Travail à réaliser

1. Identifier un export départemental daté sur le catalogue IGN, résoudre l'URL exacte.
2. Relever taille et SHA-256, écrire `contracts/datasets/DS-04/releases/<release>-35.json`.
3. Archiver l'asset avant import ; le WFS ne peut servir qu'à la découverte, jamais à l'import.
4. Importer les couches `BATIMENT` et `TRONCON_DE_ROUTE`, en conservant les identifiants IGN.
5. Rattacher les bâtiments BD TOPO aux bâtiments canoniques RNB par la chaîne de préférence déjà
   définie : identifiant officiel, relation source explicite, intersection spatiale, proximité.
   Documenter le taux de chaque méthode.
6. Traiter la voirie comme une couche de contexte : elle sert à calculer une distance ou un accès,
   elle ne crée pas d'entité canonique.
7. Rapport d'acceptation et verdict.

## Résultat au 7 septembre 2026 — `display_only`

Les sept étapes sont faites. Preuves complètes dans
[l'audit spatial §DS-04](../data/spatial-sources-audit.md#ds-04--bd-topo).

**Release épinglée.** `BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15`, 528 975 501 octets,
SHA-256 `0d06d6e7…c559e`, MD5 amont vérifié conforme. Manifeste
[`contracts/datasets/DS-04/releases/2026-06-15-35.json`](../../contracts/datasets/DS-04/releases/2026-06-15-35.json).

**Import réel.** 1 365 389 objets lus, 1 365 389 normalisés, **0 en quarantaine** : 974 172
bâtiments et 391 217 tronçons. Archive résolue depuis la copie immuable, sans téléchargement.

**Débordement départemental mesuré**, comme l'audit l'avait annoncé :

| Périmètre | Bâtiments | Avec lien RNB | Sans lien |
|---|---:|---:|---:|
| Dans le 35 | 801 170 | 783 459 | 17 711 |
| Hors 35 | 173 002 | 22 | 172 980 |

Voirie : 323 302 tronçons dans le 35, 67 915 hors département.

**Taux par méthode.** L'appariement vient de la source, comme prévu :

| Méthode | Décision | Liens |
|---|---|---:|
| `official_identifier` | certain | 692 633 |
| `official_identifier` | ambigu | 46 106 |
| `source_relation` | certain | 1 |
| `spatial_intersection` | ambigu | 87 255 |
| `proximity` | non exécutée | — |

Distribution par observation sur les 332 communes : 692 621 certains, 90 841 ambigus, 0 rejetés,
17 711 non appariés.

**Aucune emprise inventée — vérifié en base.** Les 3 864 bâtiments RNB ponctuels conservent
`geom IS NULL`. L'importeur n'écrit jamais `reference.building`, et les 692 634 identifiants DS-04
rattachés portent tous `is_preferred = false`.

## Trois décisions prises pendant l'implémentation

**1. La proximité n'est pas exécutée.** Contrairement à l'intersection spatiale, elle exige un
seuil de distance pour produire le moindre candidat, et aucun seuil observé n'existe. Les 87 255
liens d'intersection sont tous ambigus, avec le recouvrement mesuré comme preuve et
`threshold_calibrated: false`. C'est ce qui vaut à DS-04 son verdict `display_only` plutôt que
`accepted` — même raisonnement que DS-05.

**2. Il manquait un lieu pour la décision de rattachement.** `meta.entity_match` relie deux
entités canoniques et sa contrainte impose `left_entity_type <> right_entity_type` : elle ne peut
pas porter « cette observation BD TOPO s'attache à ce bâtiment RNB ». Et
`entity_source_observation.entity_id` ne portait qu'un rattachement binaire et sans motif, ce qui
rendait « non apparié » indistinguable de « rejeté ». D'où `meta.entity_observation_link`
(migration `20260907_0019`), qui porte méthode, confiance, décision et preuve. DS-03 et DS-07
poseront le même problème — voir [B2a](./B2a-import-bdnb-ds03.md) et [D4](./D4-import-dpe-ds07.md).

**3. La voirie a sa propre table.** `entity_source_observation` n'admet que les cinq types
canoniques, et un tronçon ne doit pas en devenir un sixième. `observation.road_segment` le place
aux côtés des autres observations non canoniques.

## Ce qui reste ouvert

- **DS-02 est `pending`**, pas accepté : DS-04 s'attache à une identité bâtiment dont la release
  attend encore la revue manuelle de [B4](./B4-revue-manuelle-appariements.md). L'état est celui
  qui précédait ce ticket, pas une régression, mais B4 devra trancher les deux ensemble.
- **Les seuils de recouvrement et de divergence d'emprise ne sont pas calibrés.** C'est B4.
- Une dépendance nouvelle, `py7zr` : DS-04 est la seule source distribuée en `7z`, et cela évite
  d'ajouter `p7zip` à l'image pour un unique format.

## Points de vigilance

- Une géométrie BD TOPO divergente d'une emprise RNB ne doit pas remplacer silencieusement cette
  dernière : le RNB reste l'identité bâtiment préférée. La divergence est une **observation**, et
  au-delà d'un écart à mesurer elle produit un appariement ambigu.
- Les 3 864 bâtiments RNB ponctuels ne doivent pas recevoir une emprise BD TOPO par appariement
  approximatif : ce serait inventer une emprise, explicitement interdit.
- La proximité sans seuil adapté au contexte est un risque déclaré de v0.3. Tout seuil vient du
  profiling observé.

## Tests obligatoires

- un bâtiment BD TOPO sans correspondance RNB est conservé comme observation non appariée, avec motif ;
- une géométrie divergente au-delà du seuil mesuré produit un match ambigu, pas un remplacement ;
- un bâtiment RNB ponctuel n'hérite jamais d'une emprise ;
- la voirie ne crée aucune entité canonique ;
- réimport stable.

## Critères d'acceptation

- release réelle, immuable, checksumée, enregistrée au catalogue ;
- taux d'appariement par méthode et par commune mesuré ;
- verdict documenté ;
- aucune emprise inventée.

## Preuves à produire

- manifeste `contracts/datasets/DS-04/releases/<release>-35.json` ;
- section DS-04 de [`spatial-sources-audit.md`](../data/spatial-sources-audit.md) ;
- contribution au rapport [B3](./B3-rapport-appariements.md).
