# Rapport du référentiel spatial — département 35

**Date :** 5 août 2026, section « Audit BAN » recomptée le 4 septembre 2026  
**État :** provisoire — RNB chargé, audit BAN en cours, BDNB et BD TOPO non chargées.

## Périmètre canonique

| Entité ou relation | Volume réel local | Source principale |
|---|---:|---|
| Communes | 332 | DS-01 |
| Parcelles | 1 333 327 | DS-01 |
| Property units mono-parcelle | 1 333 327 | DS-01 |
| Bâtiments RNB | 741 376 | DS-02 |
| Bâtiments RNB polygonaux | 737 512 | DS-02 |
| Bâtiments RNB ponctuels | 3 864 | DS-02 |
| Relations bâtiment–parcelle | 1 240 351 | DS-02 ↔ DS-01 |
| Bâtiments avec au moins une parcelle certaine, métriqués par commune | 737 333 | DS-02 ↔ DS-01 |
| Bâtiments sans parcelle, métriqués par commune | 3 607 | DS-02 ↔ DS-01 |

Les identités canoniques ne recopient pas les géométries cadastrales. Les vues
`reference.parcel_geometry` et `reference.property_unit_geometry` lisent la release DS-01 active,
ce qui garde le modèle viable lorsque le périmètre passera du département à la Bretagne puis à la
France.

## Qualité RNB

- 741 376 lignes sources normalisées, aucune quarantaine et aucun doublon de `rnb_id` ;
- 737 512 emprises polygonales et 3 864 identités ponctuelles sans polygone inventé ;
- 715 315 identifiants BDNB externes et 604 098 identifiants BD TOPO externes conservés ;
- 737 351 bâtiments disposent d'au moins un lien parcellaire explicite ;
- les taux d'appariement sont persistés pour chacune des 332 communes ;
- 403 bâtiments sans code commune et 33 portant un code absent du référentiel actif sont soumis à
  `rnb-commune-spatial@1`. Une commune n'est affectée que si le point représentatif est couvert par
  une unique géométrie communale active ; plusieurs candidates créent un match ambigu bloquant.

La somme des liens est supérieure au nombre de bâtiments liés : le maximum observé est de 37
parcelles pour un bâtiment. Cette cardinalité est modélisée nativement et n'est pas aplatie.

## Audit BAN

Tous les chiffres de cette section sont recomptés depuis l'archive `adresses-35.csv.gz` dont le
SHA-256 correspond au manifeste épinglé (`22160b6d…ccc3d0`), et régénérables par :

```bash
make ban-census ARCHIVE=/chemin/vers/adresses-35.csv.gz
```

La sortie est archivée dans [`ban-census-35.json`](./ban-census-35.json). Le décompte refuse de
s'exécuter si le fichier ne correspond pas au checksum du manifeste, et vérifie sa propre
conservation de lignes. Il ne touche à aucune base.

**Deux unités sont distinguées partout et ne doivent jamais être confondues** : les *lignes
concernées* par un cas, et les *lignes en excès* qu'il produit. Un identifiant présent deux fois
concerne deux lignes et n'en produit qu'une en excès. La version précédente de cette section
confondait les deux ([BUG-01](../backlog/BUG-01-chiffres-audit-ban.md)).

| Grandeur | Valeur |
|---|---:|
| Lignes lues | 437 679 |
| Lignes illisibles mises en quarantaine | 0 |
| Identifiants distincts | 437 441 |
| Communes représentées | 332 sur 332 |
| Relations `cad_parcelles` déclarées | 326 161 |

Identifiants apparaissant plusieurs fois — les trois classes sont mesurées disjointes sur ce
millésime (intersection nulle), sans que rien ne le garantisse sur le suivant :

| Cas | Identifiants | Lignes concernées | Lignes en excès | Traitement |
|---|---:|---:|---:|---|
| Identité contradictoire | 0 | 0 | 0 | enregistrement en quarantaine, **bloquant** |
| Attribut contradictoire, identité stable | 217 | 447 | 230 | attribut retiré avec motif, adresse conservée |
| Répétition à l'identique | 8 | 16 | 8 | une ligne canonique conservée, avertissement |

Les 217 identifiants à attribut contradictoire représentent **0,102 %** des lignes lues et se
répartissent sur **82 des 332 communes**. Aucun ne diverge sur l'identité de l'adresse : la
divergence porte sur la position (216 cas) ou la relation parcellaire. Détail identifiant par
identifiant dans [`ban-conflicting-identifiers-35.csv`](./ban-conflicting-identifiers-35.csv),
décision et limites dans [`ban-attribute-quarantine-35.md`](./ban-attribute-quarantine-35.md).

Conservation des lignes, vérifiée par le décompte et attendue de l'import :

```text
437 679 lues = 437 441 normalisées + 0 en quarantaine + 238 en excès dédupliquées
        238  =   8 répétitions à l'identique
             + 230 variantes devenues identiques après retrait de l'attribut contradictoire
```

Ces 230 lignes **ne sont pas des doublons de la source** : elles le deviennent parce que la
divergence qui les distinguait a été retirée avec un motif. Le contrôle `exact_duplicate_ban_record`
n'observe donc que les 8 premières ; les 230 autres sont publiées dans le détail de
`ambiguous_ban_attribute`. Confondre les deux ferait passer pour un défaut de la BAN une
conséquence de notre propre décision.

Contrôles d'appariement :

- chaque relation parcellaire est contrôlée contre la géométrie Cadastre active ;
- `covered = true` donne une confiance de 0,99 ; `within_ten_meters = true` donne 0,95 ; au-delà,
  la relation reste ambiguë à 0,80 et bloque la publication. Ces paliers ne sont **pas encore
  justifiés par la distribution observée** — leur mesure ou leur recalibrage relève de
  [B1](../backlog/B1-audit-ban-ds05.md) ;
- les clés BAN exactes observées dans le RNB créent des relations bâtiment–adresse certaines ;
- une adresse dont la position a été retirée ne fonde aucune relation spatiale, mais conserve sa
  relation RNB, qui repose sur l'identité et non sur la géométrie.

Les compteurs ci-dessus sont ceux que l'import **doit** produire ; ils n'ont pas encore été
confrontés à ceux réellement persistés dans `meta.import_run`, aucun import complet n'ayant été
exécuté sous le modèle de quarantaine par attribut. Ce rapprochement, la distribution
`certain / ambiguous / rejected / unmatched` et le verdict d'acceptation relèvent de B1. La
release reste inactive d'ici là : l'API ne peut pas exposer ces adresses par accident.

## Features et valeurs manquantes

Le catalogue `morphology-v1` définit `LAND-001` à `LAND-010` et `BLD-001` à `BLD-003` avec source,
formule, transformation, unité, plage et règle de valeur manquante. Le moteur pur est couvert par
les tests unitaires, y compris les contradictions et l'exclusion des prédictions.

DS-03 et DS-04 ne disposant pas encore de release réelle acceptée, les features qui exigent leurs
attributs restent absentes avec un motif. Elles ne sont ni imputées ni remplacées par zéro. Les
identifiants BDNB et BD TOPO transportés par DS-02 ne valent pas observation de ces sources.

## Validation restante

- exécuter l'import BAN complet et confronter ses compteurs au décompte de l'archive ;
- importer des releases réelles et checksumées DS-03 et DS-04 ;
- produire la distribution finale `certain / ambiguous / rejected / unmatched` ;
- revoir manuellement un échantillon stratifié urbain, périurbain, rural et cas frontières ;
- accepter puis activer séparément chaque release ayant satisfait ses contrôles bloquants.
