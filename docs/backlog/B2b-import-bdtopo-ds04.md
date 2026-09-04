# B2b — Importer et auditer DS-04 BD TOPO sur le 35

**Version :** v0.3 · **Taille :** L · **État :** À faire
**Dépend de :** — · **Bloque :** B3, B5

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
