# ADR-024 — Une feature de bâtiment porte sur le bâtiment physique, dans `feature.feature_value`

**Date :** 16 septembre 2026
**Décidé par :** l'agent, sur délégation du porteur du projet (« enchaîne en prenant les
meilleures décisions »), le 16 septembre 2026. Révisable par le porteur.

**Contexte.** [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md) :
`feature.feature_value.building_id` référence `reference.building`, les enregistrements RNB.
BUG-12 a établi que le sujet d'une feature de bâtiment est le **bâtiment physique**
(`reference.physical_building`) : 741 379 enregistrements RNB du 35 en regroupent 514 859
(741 376 au compte de BUG-12). B5 et D4
ont refusé d'écrire `BLD-001..003` et `REN-001..008` sur le mauvais sujet ; rien ne pouvait porter
le bon.

**Alternatives écartées.**

- *Une table `feature.physical_building_feature`.* Deux stockages de features, deux provenances,
  deux lectures pour E1 : la même règle (valeur ou motif, jamais les deux) écrite deux fois.
- *Rediriger `building_id` vers `reference.physical_building`.* Le sens de la colonne changerait
  sous les lignes existantes, et le regroupement cadastral (517 615) partage la même table : la
  colonne ne dirait plus lequel des deux regroupements elle vise sans lire la ligne cible.
- *Ne rien matérialiser tant qu'aucune source n'est acceptée.* La dette resterait inexprimable ;
  E1 et les tickets E8 continueraient de buter sur le schéma plutôt que sur l'acceptation.

**Décision.**

1. `feature.feature_value` gagne une colonne de sujet `physical_building_id`, clé étrangère vers
   `reference.physical_building`, `ON DELETE CASCADE`. L'exclusion reste stricte : exactement une
   colonne de sujet parmi `property_unit_id`, `building_id`, `physical_building_id`.
2. L'identité unique inclut la nouvelle colonne (`NULLS NOT DISTINCT`).
3. Les familles `BLD-*` et `REN-*` ne peuvent plus s'écrire sur `building_id` : une contrainte le
   refuse. Qu'une feature d'unité foncière ne vise pas un bâtiment physique, et l'inverse, relève
   de l'écriture et du contrôle du rapport, pas d'une contrainte : la famille ne suffit pas à dire
   le sujet (`RISK-101` porte sur le bâtiment, `RISK-001..004` sur l'unité). `building_id` reste pour un usage futur explicitement décidé ; aucune ligne ne le porte.
4. Les features de bâtiment portent sur le regroupement **RNB** (`source = 'rnb'`), celui auquel
   les DPE se rattachent par `id_rnb`. Le regroupement cadastral sert `LAND-009`.
5. Tant que BDNB, BD TOPO, BAN et DPE sont `display_only` (`SPEC.md` §13.8), les onze features
   s'écrivent **absentes, `source_not_accepted`**, une ligne par bâtiment physique, en citant les
   releases lues — comme `LAND-008` pour chaque unité foncière. L'écriture refuse de s'exécuter
   si l'une de ces sources compte une release acceptée : le calcul des valeurs demandera alors
   ses chargeurs, sous ticket.

**Conséquences.**

- Environ 5,7 millions de lignes absentes, un peu plus de 2 Gio ; le motif d'absence n'est plus
  « schéma impossible » mais « source non acceptée ».
- Reconstruire `reference.physical_building` supprime ses features en cascade : il faut relancer
  `make building-features` après `make physical-buildings`.
- Les écritures `ON CONFLICT` de `feature_value` nomment les trois colonnes de sujet.
