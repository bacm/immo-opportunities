# Audit DS-06 à DS-09 — données métier

**Périmètre :** département 35  
**Date de l'audit :** 6 août 2026  
**Statut :** contrats et garde-fous techniques validés sur fixtures ; aucune release réelle n'est
encore acceptée ou publiable.

## Verdict par source

| Source | Release réelle archivée | Tests de contrat | Verdict actuel |
|---|---:|---:|---|
| DS-06 DVF (geo-dvf) | **oui** | oui | **`display_only`** — release réelle importée et auditée, segments et seuil de support à calibrer par E1 |
| DS-07 DPE ADEME | non | oui | **rejeté pour publication** — release et contrôle d'appariement réels absents |
| DS-08 GPU/CNIG | non | oui | **rejeté pour publication** — documents opposables et profils validés absents |
| DS-09 Géorisques | non | oui | **rejeté pour publication** — releases par famille de risque absentes |

Le verdict « rejeté pour publication » ne porte pas sur la qualité intrinsèque de la source. Il
indique qu'aucun fichier réel, immuable et checksumé n'est présent pour exécuter les contrôles
d'acceptation. Une source sans verdict `accepted` dans `meta.dataset_release` produit des features
absentes avec le motif `source_not_accepted`.

## Garanties testées

### DS-06 — verdict du 14 septembre 2026 : `display_only`

**Preuve :** [`dvf-quality-35.md`](./dvf-quality-35.md) · **Release :** `DS-06@2026-09-13`,
millésimes 2021 à 2025, 133 066 mutations et 337 019 lots.

**Source changée, et le contrat le dit.** DVF+ du Cerema n'est distribué que par un dossier Box
authentifié — l'API répond 401. Ni archivage, ni checksum, ni import relançable n'y sont
possibles. La release importée est `geo-dvf` d'Etalab, la même donnée DGFiP géocodée, dont
l'`id_parcelle` est directement notre `cadastral_id`.

**Ce qui est acquis.** Release archivée dans MinIO, cinq empreintes SHA-256 relevées et vérifiées
avant import, import idempotent dont la clé porte la version de transformation. Rattachement au
référentiel spatial à **97,49 %**, et les 2,5 % manquants sont un décalage temporel mesuré — le
taux monte de 96,32 % en 2021 à 99,34 % en 2025 — non un défaut d'appariement. Qualification des
mutations complexes écrite, testée, et corrigée une fois : **65,5 % des mutations n'ont aucun prix
allouable**, et chacune porte son motif.

**Pourquoi `display_only` et non `accepted`.** Deux éléments manquent, et aucun ne relève de la
qualité de la source :

- **les segments de marché ne sont pas définis.** Le ticket D1 impose que leurs frontières
  viennent de la donnée observée et non d'un découpage administratif. L'étendue du prix du terrain
  — de 1 € à 181 € entre quartiles, mêlant terres agricoles et terrains à bâtir — montre qu'un
  segment mal tracé produirait des comparables absurdes ;
- **le support statistique minimal n'est pas calibré.** 305 communes ont au moins 5 ventes de
  maison exploitables sur cinq ans, 267 au moins 10, et 152 au moins 30. Retenir l'un de ces
  seuils ici serait exactement le choix a priori que le produit s'interdit.

Les deux relèvent de [E1](../backlog/E1-profiling-distributions.md). Faire entrer DS-06 dans le
périmètre d'analyse avant que ses segments existent produirait des médianes sur trois
transactions, c'est-à-dire le risque de fausse précision déclaré par la v0.5.

### DS-06 — DVF+ (audit initial, avant import)

- une transaction postérieure au snapshot est exclue et un résultat déjà sélectionné qui fuit le
  futur fait échouer le calcul ;
- une mutation multi-parcelles ou multi-locaux sans prix alloué par bien n'est jamais convertie en
  prix au m² ;
- chaque candidat conserve distance, segment, date, type, surface, transformation de prix et motif
  d'inclusion ou d'exclusion ;
- les segments ne mélangent pas silencieusement les marchés urbains, ruraux, littoraux ou
  touristiques ;
- médiane pondérée, quartiles, dispersion, récence, liquidité et tendance restent absents quand le
  support statistique requis manque.

### DS-07 — DPE

- seuls les diagnostics déposés, non simulés, non annulés et antérieurs au snapshot sont éligibles ;
- le dernier diagnostic directement rattaché au bâtiment est retenu ;
- plusieurs diagnostics seulement rattachés à la même adresse produisent `ambiguous_match` ;
- l'absence de diagnostic est neutre et ne crée ni signal de vacance ni signal de dégradation ;
- la classe, la consommation, l'âge, les caractéristiques déclarées et la confiance d'appariement
  gardent la référence du diagnostic choisi.

### DS-08 — GPU

- le document doit être publié, opposable et valide à la date du snapshot ;
- un zonage absent, périmé ou sans zone représentative reste absent avec un motif ;
- les chevauchements matériels sans gagnant clair sont ambigus ;
- un profil de règles n'est utilisable que s'il a été validé pour la version exacte du document ;
- `URB-004` n'est calculé que si toutes les règles indispensables sont structurées et validées ;
- aucun texte libre de règlement n'est interprété automatiquement.

### DS-09 — Géorisques

- la granularité `point`, `zone`, `parcel` ou `commune` est obligatoire et persistée ;
- une observation communale reste dans `commune_context_only` et ne devient jamais une exposition
  parcellaire ;
- zéro intersection n'est produit que lorsque la couverture fine concernée est connue ;
- les distances aux sites pollués et cavités ne sont calculées qu'avec une géométrie et une
  couverture déclarée.

## Couverture et fraîcheur

La migration ajoute `meta.dataset_coverage_metric`, unique par release et commune, avec compte de
lignes, compte apparié, couverture, observation la plus fraîche et date de mesure. L'endpoint
`GET /api/v1/market-data/coverage?commune_code=35000` expose séparément une métrique nulle et une
métrique absente.

## Étapes nécessaires pour accepter une release

1. Archiver chaque actif source exact et son SHA-256 dans un manifeste de release.
2. Exécuter un import idempotent et conserver son rapport de quarantaine.
3. Produire les distributions par commune et comparer au millésime précédent.
4. Réaliser une revue manuelle stratifiée des comparables, appariements DPE, zones GPU et risques.
5. Enregistrer le verdict `accepted`, `display_only` ou `rejected`, puis seulement activer le
   pointeur atomique de la release.
