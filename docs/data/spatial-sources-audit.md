# Audit des sources du référentiel spatial

**Périmètre :** département 35  
**Date de l'audit :** 5 août 2026  
**Statut :** en cours — DS-02 et DS-05 sont épinglées ; DS-03 et DS-04 ne sont pas encore
acceptables faute de manifeste réel importé et contrôlé.

## Décision par source

| Source | Release retenue | Archive immuable | Import réel | Décision |
|---|---|---:|---:|---|
| DS-02 RNB | `2026-08-01`, département 35 | oui | oui | contrôles automatiques produits, revue manuelle requise |
| DS-03 BDNB Open | à sélectionner | non | non | contrat seulement, non publiable |
| DS-04 BD TOPO | à sélectionner | non | non | contrat seulement, non publiable |
| DS-05 BAN | `2026-06-17`, département 35 | oui | oui | **`display_only`** — adresses exploitables, relations parcellaires non calibrées |

Une URL `latest` ne constitue jamais une release. Le manifeste versionné doit contenir l'URL
résolue, la taille et le SHA-256 avant qu'un import puisse être accepté.

## DS-02 — Référentiel National des Bâtiments

- catalogue officiel : <https://www.data.gouv.fr/datasets/referentiel-national-des-batiments> ;
- licence déclarée : Licence Ouverte 2.0 ;
- archive retenue : export départemental du 1er août 2026 ;
- format observé : ZIP contenant un CSV séparé par `;` ;
- colonnes observées : `rnb_id`, `point`, `shape`, `status`, `ext_ids`, `addresses`, `plots`,
  `validated_by` ;
- taille : 190 932 054 octets ;
- SHA-256 : `b40a4d474d6cbc4cfec2aa8460714675f33349b3cd1e97b3dad4e7b7883d0751`.

Le RNB fournit l'identité bâtiment préférée. Une géométrie ponctuelle crée une identité stable mais
ne devient jamais une emprise inventée. Les identifiants BDNB et BD TOPO présents dans `ext_ids`
sont conservés comme identifiants externes observés via DS-02 ; ils ne valent pas import ni
acceptation de DS-03 ou DS-04. Les relations `plots` conservent leur taux de couverture et leur
provenance.

## DS-03 — BDNB Open

- catalogue officiel : <https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments> ;
- documentation du modèle : <https://bdnb.io/documentation/modele_donnees/> ;
- archive départementale historique identifiée pour le millésime `2024-10-a` :
  <https://bdnb.io/archives_data/bdnb_millesime_2024_10_a/> ;
- le millésime courant repéré pendant l'audit est distribué en export national volumineux ; il
  n'est pas épinglé tant que son découpage et son checksum ne sont pas reproductibles localement.

Le contrat distingue explicitement un groupe BDNB d'un bâtiment physique. Seules les valeurs
Open observées, accompagnées de leur producteur et de leur champ source, sont admises. Les champs
Expert, simulés ou prédits restent exclus. Une copie BDNB d'une valeur issue d'une source primaire
ne doit pas être comptée deux fois.

## DS-04 — BD TOPO

- catalogue officiel : <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-TOPO> ;
- licence déclarée : Licence Ouverte 2.0 ;
- couches attendues : `BATIMENT` et `TRONCON_DE_ROUTE` ;
- aucun export départemental daté et checksumé n'est encore inscrit dans le dépôt.

Le téléchargement dynamique ou le WFS peuvent servir à découvrir la donnée, mais ne satisfont
pas seuls la reproductibilité. La release restera inactive jusqu'à archivage d'un export exact.
Les bâtiments légers et la voirie restent donc des valeurs manquantes, jamais des zéros.

## DS-05 — Base Adresse Nationale

- documentation officielle :
  <https://doc.adresse.data.gouv.fr/docs/documentation-generale/utiliser-la-base-adresse-nationale/les-fichiers-de-la-base-adresse-nationale> ;
- archive retenue : CSV départemental archivé du 17 juin 2026 ;
- taille : 17 098 791 octets ;
- SHA-256 : `22160b6d570c1ca557fd5eb60e99f4d83a80be715422fce5a828f3d847ccc3d0` ;
- `cad_parcelles` est traité comme une relation source expérimentale et vérifié contre la géométrie
  de la parcelle Cadastre active.

Le fichier comporte 437 679 lignes normalisées pour 437 441 identifiants distincts. L'audit brut a
détecté 8 identifiants répétés à l'identique, soit 8 lignes en excès dédupliquées sans perte de
l'archive, et 217 identifiants réutilisés avec des contenus différents, portés par 447 lignes dont
230 en excès.

Aucun de ces 217 conflits ne porte sur l'identité de l'adresse : `numero`, `rep`, `nom_voie`,
`code_postal`, `code_insee` et `nom_commune` restent stables entre les variantes. 216 divergent par
leur position, avec un écart médian de 47,8 m et un maximum de 3 128,5 m.

Depuis le 4 septembre 2026, ces conflits ne bloquent donc plus la release : l'identité est
conservée et seul l'attribut contradictoire devient manquant avec un motif. Une divergence portant
sur l'identité elle-même reste, elle, bloquante. Voir
[le rapport de quarantaine par attribut](./ban-attribute-quarantine-35.md) et le détail des 217
identifiants dans [`ban-conflicting-identifiers-35.csv`](./ban-conflicting-identifiers-35.csv).

### Verdict du 4 septembre 2026 — `display_only`

Import réel exécuté sur base propre, cadastre `DS-01@2026-06-01` publié comme référentiel actif.
Compteurs persistés : 437 679 lignes lues, 437 441 normalisées, 0 en quarantaine, 238 dédupliquées
— identiques à ceux que [le décompte de l'archive](./ban-census-35.json) prédisait, ce qui lève la
limite laissée ouverte par [BUG-01](../backlog/BUG-01-chiffres-audit-ban.md). Preuves complètes
dans [`ban-import-35.json`](./ban-import-35.json).

**Ce qui est acquis.** L'identité des adresses est vérifiée : aucun identifiant réutilisé avec une
identité contradictoire, contrôle bloquant `conflicting_ban_identity` au vert. Les 216 adresses
sans position n'entrent dans **aucune** relation spatiale. Les relations `cad_parcelles` se
résolvent à 98,8 % contre la géométrie cadastrale active ; les 3 760 restantes (3 302 adresses,
1,15 %) sont conservées en relation `rejected` motivée, jamais écartées en silence.

**Ce qui manque.** Les paliers de confiance 0,99 / 0,95 / 0,80 et la frontière de 10 m qui sépare
`certain` de `ambiguous` ne viennent d'aucune mesure. La distribution observée des distances
point ↔ parcelle déclarée les contredit : la densité **croît** en traversant 10 m et culmine entre
20 et 50 m. Voir [le rapport spatial 35](./spatial-reference-35-report.md#audit-ban).

Une confiance est une probabilité que la relation soit juste. Aucune géométrie ne l'estime sans
vérité terrain : cela relève de [B4](../backlog/B4-revue-manuelle-appariements.md).

D'où le verdict. Les adresses sont saines et peuvent alimenter la recherche et la carte ; les
relations parcellaires ne peuvent pas fonder une feature entrant dans un score. C'est exactement
la portée de `display_only`, désormais opposable techniquement : la release figure dans
`meta.active_dataset_release` et est exclue de `meta.analysis_dataset_release`.

Passage à `accepted` conditionné à B4 : paliers recalibrés depuis la distribution observée, ou
justifiés par une revue manuelle stratifiée.

## Garanties transversales

- les tables sources restent versionnées et append-only ;
- les identités canoniques utilisent des identifiants texte stables et conservent les identifiants
  sources en relation plusieurs-à-plusieurs ;
- les décisions `certain`, `ambiguous` et `rejected` sont persistées avec méthode, version,
  confiance, justification, preuves et releases ;
- une ambiguïté critique bloque la publication mais ne disparaît pas du catalogue d'audit ;
- l'API ne lit que les entités dont la release source est acceptée et activée ;
- les géométries de parcelles ne sont pas recopiées dans chaque `PropertyUnit` : les vues
  canoniques s'appuient sur la release Cadastre active et ses index.

