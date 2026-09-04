# D2 — DS-08 GPU : documents, zones et contraintes

**Version :** v0.5 · **Taille :** L · **État :** À faire
**Dépend de :** D1 · **Bloque :** D5

## Contexte à charger

- `contracts/datasets/DS-08/v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md` (§DS-08)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Verdict actuel : « rejeté pour publication — documents opposables et profils validés absents ».
Les garde-fous sont testés sur fixtures ; il manque les documents réels.

**Interdit structurant :** aucune interprétation automatique libre du texte des règlements PLU. Le
produit ne rend pas de décision urbanistique opposable. Ce qui est importé, ce sont des documents,
des zones et des contraintes **structurées**, jamais une lecture de texte.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Une zone chevauchante sans gagnant clair rend le zonage inutilisable sans invalider la parcelle.

## Travail à réaliser

1. Identifier et épingler les documents d'urbanisme publiés sur le GPU pour les communes du 35 :
   un document par commune ou EPCI, avec sa version exacte et sa date d'opposabilité.
2. Archiver chaque document avec son checksum. Le périmètre est hétérogène : certaines communes
   relèvent d'un PLUi, d'autres d'un PLU, d'autres d'une carte communale ou du RNU. Cette
   hétérogénéité doit être modélisée, pas aplatie.
3. Importer `UrbanDocument`, `UrbanZone`, `UrbanConstraint` en conservant l'identifiant CNIG.
4. Rattacher les zones aux parcelles du référentiel spatial, avec gestion explicite des
   chevauchements.
5. Valider un **profil de règles** par version exacte de document. `URB-004` n'est calculé que si
   toutes les règles indispensables sont structurées et validées pour cette version précise.
6. Publier la couverture : combien de communes disposent d'un document opposable importé, combien
   ont un profil de règles validé, combien restent sans donnée.

## Points de vigilance

- **Risque déclaré :** appliquer un profil PLU à une mauvaise version du document. Le rattachement
  profil ↔ version doit être strict et testé, pas conventionnel.
- Un document périmé à la date du snapshot est inutilisable : la zone reste absente avec motif.
- Un chevauchement matériel sans gagnant clair est ambigu, pas arbitré.
- La validation des profils de règles est un travail humain non automatisable : le prévoir dans la
  charge, commune par commune. C'est la principale raison pour laquelle ce ticket est L et non M.
- Une zone GPU ne dit pas ce qui est constructible en pratique. Les features URB expriment un
  contexte réglementaire observé, jamais une autorisation.

## Tests obligatoires

- document non publié ou non opposable : refusé ;
- document périmé à la date du snapshot : zone absente avec motif ;
- zonage absent ou sans zone représentative : absent avec motif ;
- chevauchement sans gagnant clair : ambigu ;
- profil de règles non validé pour la version exacte : `URB-004` non calculé ;
- aucun texte libre interprété.

## Critères d'acceptation

- documents réels importés, versionnés et checksumés ;
- couverture publiée par commune, avec les communes sans document identifiées comme non couvertes ;
- profils de règles validés et rattachés à une version exacte ;
- verdict documenté ;
- distributions URB disponibles pour [E1](./E1-profiling-distributions.md).

## Preuves à produire

- manifestes `contracts/datasets/DS-08/releases/…` ;
- section DS-08 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/gpu-coverage-35.md`.
