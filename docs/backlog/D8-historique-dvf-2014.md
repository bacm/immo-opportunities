# D8 — Remonter l'historique DVF à 2014, depuis les publications DGFiP archivées

**Version :** v0.5 · **Taille :** L · **État :** À faire
**Nature :** implémentation · **Touche :** contracts/datasets/DS-06/, pipelines/src/immo_pipelines/market_data/, pipelines/scripts/import_dvf_release.py, docs/data/dvf-quality-35.md
**Dépend de :** D1 · **Bloque :** —
**Demandé par :** conversation du 15 septembre 2026

## Contexte à charger

- `docs/data/dvf-quality-35.md` (section sur la profondeur d'historique)
- `contracts/datasets/DS-06/v1.json`
- `pipelines/scripts/import_dvf_release.py`

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi

`geo-dvf` ne publie que 2021 à 2025 : DVF open data est une fenêtre glissante de cinq ans, et la
DGFiP retire les millésimes antérieurs de ses pages. Vérifié sur les quatre canaux officiels.

`https://data.cquest.org/dgfip_dvf/` conserve **onze publications semestrielles DGFiP**, de
`201904` à `202504`. Celle d'avril 2019 porte `valeursfoncieres-2014.txt` à `-2018.txt`, vérifiés
accessibles — 333 Mo pour 2014. L'historique atteignable passe donc de **cinq à douze ans**.

## Ce que douze ans débloquent

- **Comparables** : une commune rurale sans support statistique sur cinq ans peut en avoir sur
  douze. C'est le chiffre qui fonde [E7](./E7-decision-valorisation.md) — 152 communes sur 332
  atteignent aujourd'hui 30 ventes de maison ; la question change si ce nombre monte.
- **Absence de mutation** : sur cinq ans, 85,1 % des parcelles du 35051 n'ont aucune mutation —
  le cas ordinaire, donc aucun pouvoir discriminant. Sur douze ans, l'absence redevient un signal.
- **Tendance de prix** : `MKT-105 local_price_trend` sur cinq points est fragile.

## Ce que ce ticket doit trancher, pas contourner

**La source est une archive tierce, pas le producteur.** C'est le point à instruire honnêtement :

- nommer la publication exacte — `201904`, pas un alias — et épingler son checksum SHA-256 ;
- écrire dans le contrat que la provenance est un miroir, et laquelle ;
- vérifier, sur un millésime présent des deux côtés, que le miroir coïncide avec la source
  officielle. `202104` et `202404` portent des années que nous avons déjà : **c'est le contrôle
  qui rend le reste crédible**, et il doit précéder tout import.

Si la comparaison échoue, le ticket s'arrête et le dit.

## Le format n'est pas celui de D1

`geo-dvf` livre du CSV géocodé par Etalab dont l'`id_parcelle` **est** notre `cadastral_id`. Les
fichiers archivés sont le **DGFiP brut**, séparateur `|`, sans identifiant de parcelle constitué.

Il se reconstruit par concaténation des champs 19 à 23 — `Code departement`, `Code commune`,
`Prefixe de section`, `Section`, `No plan` — en 14 caractères. C'est une **transformation à
tester**, pas une jointure acquise : le cas des communes fusionnées et celui du préfixe de section
non nul sont les deux pièges attendus.

La pré-qualification des mutations complexes, absente de ces fichiers comme de geo-dvf, est déjà
notre code depuis [D1](./D1-import-dvf-ds06.md).

## Travail à réaliser

1. Comparer miroir et source officielle sur un millésime commun ; publier le résultat avant tout
   import.
2. Étendre le contrat DS-06 : publications archivées nommées, checksums, provenance déclarée.
3. Lire le format DGFiP brut et reconstruire `cadastral_id`, avec tests sur les deux pièges.
4. Importer 2014 à 2020 sur le 35, sous une clé d'idempotence portant la version de transformation.
5. Republier les taux de rattachement par millésime — la dérive de numérotation parcellaire sera
   plus forte sur l'ancien, et c'est une mesure attendue, pas une surprise.

## Tests obligatoires

- un préfixe de section non nul produit le bon identifiant à 14 caractères ;
- une commune fusionnée depuis 2014 est comptée comme non rattachée avec son motif, jamais
  rattachée de force ;
- un millésime déjà importé par D1 n'est pas réimporté à vide ;
- le contrôle miroir/source est rejouable.

## Critères d'acceptation

- la coïncidence miroir/source officielle est publiée sur un millésime commun ;
- la provenance tierce est écrite dans le contrat, pas seulement dans un commit ;
- les taux de rattachement sont publiés millésime par millésime ;
- aucun millésime n'est importé sans checksum épinglé.

## Preuve à produire

`docs/data/dvf-quality-35.md`, étendu : contrôle miroir/source, volumétrie et rattachement par
millésime de 2014 à 2025.
