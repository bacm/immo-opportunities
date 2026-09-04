# B2a — Importer et auditer DS-03 BDNB Open sur le 35

**Version :** v0.3 · **Taille :** L · **État :** À faire
**Dépend de :** — · **Bloque :** B3, B5

## Contexte à charger

- `contracts/datasets/DS-03/v1.json`
- `docs/data/spatial-sources-audit.md` (§DS-03)
- `pipelines/src/immo_pipelines/spatial/importer.py`
- `pipelines/src/immo_pipelines/cadastre/catalog.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DS-03 n'a qu'un contrat. L'audit note : « archive départementale historique identifiée pour le
millésime `2024-10-a` ; le millésime courant est distribué en export national volumineux, non
épinglé tant que son découpage et son checksum ne sont pas reproductibles localement ».

**Piège identifié et à ne pas commettre :** le RNB transporte 715 315 identifiants BDNB externes
dans son champ `ext_ids`. Ces identifiants sont des *références observées*, pas une observation de
BDNB. Ils ne dispensent d'aucun import et ne permettent de calculer aucune feature BDNB.

## Décision ouverte

| Option | Avantage | Inconvénient |
|---|---|---|
| Millésime `2024-10-a`, archive départementale | checksum et découpage immédiats | millésime ancien, fraîcheur dégradée à documenter |
| Millésime courant, export national découpé localement | fraîcheur | le découpage doit être déterministe et checksumé, sinon la release n'est pas reproductible |

Si l'export national est retenu, le découpage fait partie de la release : il faut archiver l'export
national **et** publier la procédure de découpage, avec le checksum du fichier départemental produit.
Un découpage non reproductible interdit l'acceptation.

## Travail à réaliser

1. Trancher la décision ci-dessus et l'inscrire dans l'audit.
2. Résoudre l'URL exacte (jamais un alias `latest`), relever taille et SHA-256, écrire
   `contracts/datasets/DS-03/releases/<release>-35.json`.
3. Archiver l'asset dans MinIO avec son checksum avant tout import.
4. Implémenter l'import : parsing, quarantaine motivée, conservation intégrale des identifiants
   sources, rattachement aux entités canoniques existantes.
5. Distinguer explicitement un **groupe BDNB** d'un **bâtiment physique** — le contrat l'impose déjà,
   l'import doit le matérialiser et non aplatir la cardinalité.
6. Exclure toute valeur BDNB Expert, simulée ou prédite. Seules les valeurs Open observées, avec
   leur producteur et leur champ source, sont admises.
7. Empêcher le double comptage : une valeur BDNB recopiée d'une source primaire déjà importée ne
   doit compter qu'une fois dans les features.
8. Produire le rapport d'acceptation et prononcer un verdict.

## Tests obligatoires

- un groupe BDNB couvrant plusieurs bâtiments physiques n'est jamais réduit à un bâtiment ;
- une valeur Expert ou prédite présente dans le fichier est rejetée avec motif, pas ignorée ;
- une valeur dupliquée depuis une source primaire déjà importée ne contribue qu'une fois ;
- réimport stable : identifiants internes inchangés ;
- une feature exigeant DS-03 reste absente avec le motif `source_not_accepted` tant que la release
  n'est pas acceptée.

## Critères d'acceptation

- release réelle, immuable, checksumée et enregistrée au catalogue ;
- aucun identifiant source écrasé ;
- verdict documenté, `accepted` / `rejected` / `display_only` ;
- taux d'appariement mesuré par commune ;
- les identifiants BDNB issus du RNB restent typés comme références externes et n'ont pas été
  promus en observations.

## Preuves à produire

- manifeste `contracts/datasets/DS-03/releases/<release>-35.json` ;
- section DS-03 de [`spatial-sources-audit.md`](../data/spatial-sources-audit.md) mise à jour ;
- rapport de distribution intégré à [B3](./B3-rapport-appariements.md).
