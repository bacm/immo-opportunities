# ADR-020 — L'unité analysée reste la parcelle, en attendant E1

**Date :** 16 septembre 2026

**Contexte.** `PropertyUnit` devait réunir les parcelles d'un même bien ; en base, chaque
parcelle est sa propre unité (1 333 327, `single_parcel`, non publiables). BUG-11 a mesuré les
signaux autorisés ([`property-unit-35.md`](../data/property-unit-35.md), recompté) : aucun ne
réunit le cas 90 ; le bâti partagé repose entièrement sur la relation secondaire, dont le seuil
revient à E1 ; les actes DVF disent une propriété commune à leur date, sur une archive encore
`pending` ; l'adresse commune est bien corroborée (92,8 %) mais ne couvre que 3,1 % des parcelles.

**Alternatives écartées pour l'instant.**

- *Regrouper par adresse commune.* Le signal le plus sûr, mais trop étroit pour changer le
  produit, et il ne règle pas le motif qui a ouvert le ticket.
- *Adresse et actes DVF de parcelles contiguës.* Plus large, jamais mesuré combiné, fondé sur une
  propriété datée.
- *Bâti partagé.* Impossible sans le seuil qu'E1 doit établir.

**Décision.**

1. **Aucun regroupement.** L'unité analysée est la parcelle cadastrale : `unit_type` reste
   `single_parcel`.
2. **Le garde-fou ne bouge pas.** `publication_eligible` reste `false` avec
   `entity_resolution_incomplete`. Le lever pour publier des parcelles est une décision d'E2, qui
   devra dire « parcelle », jamais « bien ».
3. **L'Explorer le dit** sur chaque fiche parcelle et unité foncière.
4. **À rouvrir après E1**, avec le seuil de la relation secondaire en main : le bâti partagé, puis
   sa combinaison avec l'adresse commune, se mesurent avec le même rapport.

**Conséquences.**

- BUG-11 se clôt sur cette décision ; E1 porte la reprise.
- Le bruit du cas 90 — une dépendance sur parcelle propre — reste dans tout score parcellaire. Il
  est connu et écrit, pas corrigé.
