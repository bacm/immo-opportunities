# Audit DS-06 à DS-09 — données métier

**Périmètre :** département 35  
**Date de l'audit :** 6 août 2026  
**Statut :** contrats et garde-fous techniques validés sur fixtures ; aucune release réelle n'est
encore acceptée ou publiable.

## Verdict par source

| Source | Release réelle archivée | Tests de contrat | Verdict actuel |
|---|---:|---:|---|
| DS-06 DVF (geo-dvf) | **oui** | oui | **`display_only`** — release réelle importée et auditée, segments et seuil de support à calibrer par E1 |
| DS-07 DPE ADEME | **oui** | oui | **`display_only`** — release réelle importée et auditée, revue manuelle D6 requise pour accepter |
| DS-08 GPU/CNIG | non | oui | **rejeté pour publication** — documents opposables et profils validés absents |
| DS-09 Géorisques | **oui** | oui | **`display_only`** — dix familles importées et auditées, revue manuelle D6 requise pour accepter |

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

### DS-07 — verdict du 14 septembre 2026 : `display_only`

**Preuve :** [`dpe-matching-35.md`](./dpe-matching-35.md) · **Release :**
`DS-07@2026-09-14-extract`, 231 416 diagnostics, 208 086 conservés, 335 communes.

**Source sans fichier, et le contrat l'avait prévu.** L'ADEME ne publie aucun fichier daté : la
seule voie d'accès est l'API `data-fair`, dont le contenu change en continu. `key_format:
YYYY-MM-DD-extract` anticipait exactement ce cas. L'extrait départemental — 24 pages, 226
colonnes, 458 Mo bruts — est constitué par pagination, archivé dans MinIO et checksumé avant
import. **L'URL n'est pas un chemin de retour** ; l'archive nommée au manifeste l'est.

**Ce qui est acquis.** Aucun enregistrement écarté à l'éligibilité : les 231 416 lignes sont des
diagnostics réglementaires déposés, antérieurs au snapshot. Import idempotent, clé portant la
version de transformation, réimport vérifié à l'identique. Rattachement par **identifiant
déclaré**, jamais par géométrie :

| Classe | Diagnostics | Part |
|---|---:|---:|
| Bâtiment, par `id_rnb` | 136 628 | 59,04 % |
| Adresse seule, par `identifiant_ban` | 71 458 | 30,88 % |
| Non rattaché, motif consigné | 23 330 | 10,08 % |

Le taux d'appariement au bâtiment va de **14,8 % à 80,2 %** entre communes de plus de 100
diagnostics — la dispersion est réelle et publiée telle quelle.

**Deux constats que la source impose.**

- **Elle se contredit sur son propre géocodage.** 17 135 diagnostics portent un
  `identifiant_ban` qui se résout dans notre référentiel alors que `statut_geocodage` annonce
  « aucune correspondance trouvée » — et leur `score_ban` médian y est *plus élevé* que sur les
  lignes géocodées. L'adresse est conservée, la confiance devient absente avec le motif
  `contradictory_geocoding_status`. Quarantaine par attribut de
  [BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md).
- **Un diagnostic annulé n'est jamais observable.** Le jeu servi est une vue virtuelle filtrée
  par l'ADEME sur `dpe_desactive = 0` ; le jeu sous-jacent répond 403. La règle qui l'écarterait
  existe et est testée, mais l'exclusion est celle du producteur, pas la nôtre, et le rapport le
  dit plutôt que de laisser croire à une couverture complète.

**Pourquoi `display_only` et non `accepted`.** La revue manuelle stratifiée n'a pas eu lieu.
C'est l'étape 4 de la procédure d'acceptation ci-dessous, et elle relève de
[D6](../backlog/D6-revue-manuelle-metier.md). B4 a montré ce que cette étape trouve : trois
défauts structurels qu'aucun contrôle automatique n'avait vus. 9 423 adresses portent plusieurs
diagnostics sans rattachement bâtiment — 47 284 diagnostics — et c'est précisément la population
qu'une revue humaine doit trancher.

**Ce que la release n'apporte pas.** `REN-001..008` ne sont **pas matérialisées** :
`feature.feature_value.building_id` réfère les enregistrements RNB, sujet que
[BUG-12](../backlog/BUG-12-deduplication-batiments-physiques.md) a invalidé. Les distributions
dont [E1](../backlog/E1-profiling-distributions.md) a besoin sont au rapport ; la matérialisation
attend [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md).

### DS-07 — DPE (audit initial, avant import)

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

### DS-09 — verdict du 14 septembre 2026 : `display_only` sur dix familles

**Preuves :** [`georisques-source-inventory-35.md`](./georisques-source-inventory-35.md) —
l'inventaire écrit avant le premier lot — et
[`georisques-coverage-35.md`](./georisques-coverage-35.md).

**10 824 observations**, dont **6 985 à granularité fine**. Une release par famille : elles n'ont
ni la même granularité, ni la même fraîcheur, ni le même producteur.

| Famille | Accès | Granularité | Observations |
|---|---|---|---:|
| Installations classées | API départementale | `point` | 3 588 |
| Arrêtés de catastrophe naturelle | API communale | `commune` | 1 485 |
| Exposition aux argiles | téléchargement national | `zone` | 1 428 |
| Risques recensés GASPAR | API communale | `commune` | 1 730 |
| Servitudes d'utilité publique | GPU | `zone` | 1 248 |
| Mouvements de terrain | API départementale | `point` | 372 |
| Potentiel radon | API communale | `commune` | 332 |
| Atlas des zones inondables | API communale | `commune` | 273 |
| Sites et sols pollués | API départementale | `zone` + `commune` | 189 |
| Cavités souterraines | API départementale | `point` | 179 |

**La source a trois modes d'accès, et le ticket en supposait un.** Aucun téléchargement daté par
famille et par département n'existe : quatre familles s'obtiennent par une API départementale,
quatre par 332 appels communaux, une par un fichier national de 623 Mo, et les servitudes par le
Géoportail de l'urbanisme. Le contrat l'avait prévu — `archived API response only when no
download exists`.

**Quatre pièges relevés, tous consignés.**

- **Un paramètre territorial inconnu est ignoré, pas rejeté.**
  `installations_classees?code_departement=35` répond `200` avec **138 248 résultats** — la France
  entière — parce que le paramètre attendu s'appelle `departement`. Sur `ssp/instructions`, c'est
  l'inverse. Le filtre est donc vérifié **ligne à ligne**, jamais déduit du code HTTP.
- **Le lien de pagination pointe une machine interne du producteur**,
  `api-georisques.bike-prod.brgm.fr`, injoignable et en clair. Les pages sont reconstruites sur
  l'hôte public.
- **Un `500` peut vouloir dire « paramètre manquant ».** La temporisation se décide sur le corps
  de la réponse, sans quoi une requête mal formée serait rejouée cinq fois.
- **Un `403` du GPU n'est pas toujours un refus.** Un document a échoué une fois puis répondu ;
  quatre autres le refusent aux trois tentatives. La distinction est mesurée, pas supposée.

**Ce que ces données fondent.** `RISK-001` (argiles), `RISK-003` (sites pollués), `RISK-004`
(cavités) et `RISK-101` sont calculables sur données réelles.

**`RISK-002` reste absente avec motif, et c'est un résultat.** Aucune source du 35 ne donne une
zone inondable **typée**. GASPAR et l'atlas disent qu'une commune est concernée — c'est communal.
La servitude `PM1` donne bien des géométries de zone, seul zonage opposable du département, mais
elle porte les risques naturels prévisibles **sans dire lequel** : son assiette est une
« enveloppe des zonages réglementaires ». En déduire « inondation » serait la faute commise sur le
champ `ETAT` du CNIG pendant D2 — interpréter de mémoire un code non documenté. Les périmètres
restent visibles dans `RISK-101` sous `sup_PM1`.

**Couverture partielle des servitudes, et le manifeste le dit.** Cinq des neuf servitudes du 35
sont lisibles, dont `PM1` et `PM3`. Les quatre autres — canalisations, aéronautique, télécoms —
sont refusées au téléchargement par le producteur. Aucune feature RISK ne les consulte.

**Pourquoi `display_only` et non `accepted`.** La revue manuelle stratifiée relève de
[D6](../backlog/D6-revue-manuelle-metier.md), étape 4 de la procédure ci-dessous.

### DS-09 — Géorisques (audit initial, avant import)

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
