# ADR-023 — Trois sources communales de l'INSEE entrent pour segmenter les marchés, dans une table d'observations dédiée

**Date :** 16 septembre 2026

**Contexte.** [D7](../backlog/D7-sources-territoriales.md) doit fournir à
[E6](../backlog/E6-segmentation-observee.md) les variables qui séparent les marchés du 35 :
population, logements, équipements, éloignement des pôles. Trois obstacles :

- le ticket nommait ses sources DS-10 et DS-11, que `SPEC.md` §13.1 réserve à Sitadel et à
  MAJIC PM ;
- aucune table ne peut porter une valeur par commune : `feature.feature_value` n'admet qu'une
  unité foncière ou un bâtiment, `market.market_metric` suppose une aire de marché déjà définie ;
- « distance aux pôles » suppose de dire ce qu'est un pôle, et D7 interdit tout seuil.

**Alternatives écartées.**

- *Élargir `feature.feature_value` à un sujet « commune ».* Une population est une observation
  publiée par un producteur, pas une feature calculée ; la migration croiserait celle de BUG-13
  sur la même table.
- *Ne rien importer en base.* Les distributions seraient publiées depuis les archives, mais E6
  devrait relire des fichiers, et la trace d'import (run, couverture, verdict) manquerait.
- *Définir un pôle par un seuil de population.* Un seuil territorial inventé, que D7 et `SPEC.md`
  §13 interdisent.
- *Les points d'intérêt de la BD TOPO pour les équipements.* Pas de nomenclature équivalente à
  celle de la BPE, pas de dénombrement officiel par commune.

**Décision** (le porteur a tranché le stockage et les pôles le 16 septembre 2026).

1. **Trois sources**, contrat et manifeste chacune :
   - **DS-14** — recensement de la population, INSEE : populations de référence 2023 et
     logements 2023 (principaux indicateurs), par commune ;
   - **DS-15** — base permanente des équipements 2025, INSEE : nombre d'équipements par commune,
     par domaine et sous-domaine de la nomenclature ;
   - **DS-16** — zonage en aires d'attraction des villes 2020, INSEE, géographie au 1er janvier
     2025 : aire, catégorie de la commune dans l'aire, tranche de taille de l'aire.

   DS-10 à DS-12 restent réservés comme le dit §13.1.
2. **Rôle : plateforme, segmentation.** Ces variables décrivent une commune ; elles n'entrent dans
   aucune mesure du baromètre ni du radar sans amendement de §13.4. Elles sont `display_only`
   jusqu'au profiling d'E6.
3. **Une table `observation.territorial_indicator`** : une ligne par release × commune ×
   indicateur, valeur numérique ou textuelle, ou motif d'absence du vocabulaire de §13.7 ; unité,
   période de référence, millésime géographique, version de transformation. Elle entre dans la
   purge d'ADR-022.
4. **Un pôle est la commune-centre de l'aire d'attraction** à laquelle appartient la commune,
   telle que l'INSEE la désigne. La distance au pôle se mesure entre centroïdes Lambert-93 des
   communes de `reference.area`, à l'import de DS-16, en citant la release DS-01 lue. Une commune
   hors attraction n'a pas de pôle (`not_applicable`) ; une commune dont la commune-centre est hors
   du référentiel importé n'a pas de distance (`source_value_missing`).
5. **Ce qui n'entre pas.** Les logements vacants du recensement : la vacance est retirée du
   produit (§12). Aucune variable socio-économique individuelle (§13.6) : les trois sources ne
   publient que des agrégats communaux.

**Conséquences.**

- Une commune n'est pas homogène : rattacher une de ces valeurs à une parcelle est une jointure
  administrative, à déclarer comme telle par tout lecteur.
- Un nombre d'équipements à zéro est un dénombrement de la BPE (aucun équipement recensé du
  type), pas une valeur manquante ; le rapport le dit.
- Les URL de l'API de fichiers de l'INSEE (Melodi) ne sont pas datées : chaque release repose sur
  sa copie archivée et son SHA-256.
- `SPEC.md` §13.1 et §13.3, `ARCHITECTURE.md` §10.7 inscrivent les trois sources.
