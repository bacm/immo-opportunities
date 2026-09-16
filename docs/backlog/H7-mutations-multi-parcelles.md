# H7 — Rendre un prix aux ventes bâties sur plusieurs parcelles, si le profil le justifie

**Version :** V5 · baromètre · **Taille :** M · **État :** À faire
**Nature :** implémentation · **Touche :** pipelines/src/immo_pipelines/market_data/dvf.py, pipelines/scripts/import_dvf_release.py, pipelines/tests/test_dvf_allocation.py, docs/data/dvf-multi-parcelles-35.md, docs/data/dvf-quality-35.md, docs/data/barometre-marche-35.md, docs/data/barometre-marche-35/
**Dépend de :** H2 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « voir les mutations même si multi parcelles »

## Contexte à charger

- `SPEC.md` §7.2, §7.3, §13.4 (BAR-001, BAR-002, BAR-009), §13.7, §13.9, §18.4 — ces sections seulement
- `docs/data/dvf-quality-35.md`, section « Mutations complexes »
- `pipelines/src/immo_pipelines/market_data/dvf.py`, classe `Mutation`
- `docs/backlog/H1-barometre-marche-35-mesures.md`, section « Ce qui a été produit »
- `.claude/skills/recompte-preuve/SKILL.md`

Ne rien charger d'autre sans nécessité démontrée.

## Ce que H1 et H2 imposent à la régénération

Admettre des ventes change les CSV du baromètre, donc leur **empreinte** : la mention « Recompté
le … » disparaît du rapport et des dix-neuf documents jusqu'à ce qu'un recompte ait lieu et qu'une
attestation de la nouvelle empreinte soit ajoutée à `docs/data/barometre-marche-35/recompte.csv`.
C'est voulu. Relancer ensuite `make market-barometer-kit` et vérifier que chaque document imprimé
tient toujours sur deux pages.

## Constat

`dvf-quality-35.md` compte **33 973 mutations `multiple_parcels`**, 25,5 % du total, sans prix
allouable. Or `Mutation.complexity()` teste le nombre de parcelles **avant** les lots chiffrables :
une maison cadastrée sur deux parcelles, son jardin sur la seconde, est écartée alors que la règle
d'allocation du même rapport rapporte le prix au seul lot bâti, le terrain venant avec. Le motif
masque aussi `multiple_priced_lots` : la répartition publiée dépend de l'ordre des tests.

Ce que cela coûte : des ventes perdues pour BAR-001 et BAR-002, là où le support de quinze ventes
par an fait déjà défaut hors des pôles.

## Choix retenus

1. **Le profil d'abord, le code ensuite.** `docs/data/dvf-multi-parcelles-35.md` répartit les
   mutations `multiple_parcels` par nombre de lots bâtis distincts, par type de local, par nombre
   de parcelles et par surface de terrain cumulée, avec la nature de culture des lots non bâtis.
   Chaque effectif porte son filtre.
2. **Seul cas candidat** : exactement un lot bâti chiffrable, avec surface. Zéro ou plusieurs lots
   bâtis restent non allouables, comme aujourd'hui.
3. **Le critère d'admission s'écrit dans le rapport avant le code.** Si le profil montre que le
   terrain annexé déforme le prix au m² — terres agricoles, surfaces sans commune mesure avec une
   maison — et qu'aucun critère ne se dégage sans seuil inventé, la boucle s'arrête : c'est une
   décision, pas une implémentation.
4. **Le motif le plus précis gagne** : `multiple_priced_lots` et `no_priced_lot` passent avant
   `multiple_parcels`, qui ne désigne plus que ce que le lot unique ne suffit pas à lever.
5. **Nouvelle version de transformation** de DS-06, dans la clé d'idempotence ; réimport du 35 ;
   `dvf-quality-35.md` et le baromètre de H1 régénérés, avec l'écart avant / après écrit.
6. **Aucune mutation individuelle publiée** : le gain se lit dans les volumes et les prix agrégés,
   jamais dans une liste (SPEC §7.2, §18.4).

## Pourquoi après H2

H2 régénère `docs/data/barometre-marche-35/`, que ce ticket réécrit. Le document de H2 est ce que
H3 montrera ; en changer les chiffres pendant les entretiens les rendrait incomparables. Si H7
aboutit avant H3, le document est régénéré avant la première session, pas pendant.

## Definition of Done

- tests de `Mutation.complexity()` sur les cas : maison et jardin sur deux parcelles, maison et
  garage, terrain seul sur plusieurs parcelles, prix manquant ;
- `docs/data/dvf-multi-parcelles-35.md` recompté par `recompte-preuve`, puis les chiffres changés
  de `dvf-quality-35.md` et `barometre-marche-35.md` ;
- `make check` vert, `make dod ID=H7`.
