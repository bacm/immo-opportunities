# H7 — Rendre un prix aux ventes bâties sur plusieurs parcelles, si le profil le justifie

**Version :** V5 · baromètre · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/src/immo_pipelines/market_data/dvf.py, pipelines/scripts/import_dvf_release.py, pipelines/tests/test_dvf_allocation.py, docs/data/dvf-multi-parcelles-35.md, docs/data/dvf-quality-35.md, docs/data/barometre-marche-35.md, docs/data/barometre-marche-35/, pipelines/scripts/dvf_multi_parcel_profile.py, Makefile, SPEC.md, apps/web/src/sheets/ParcelSales.tsx
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

## Résultat — 16 septembre 2026

**Preuve :** [`dvf-multi-parcelles-35.md`](../data/dvf-multi-parcelles-35.md), les sections
modifiées de [`dvf-quality-35.md`](../data/dvf-quality-35.md) et le baromètre régénéré, recomptés en
trois passes en isolement du code : aucune divergence de valeur. Attestation de l'empreinte
`9faf338138a6758e` ajoutée à `barometre-marche-35/recompte.csv`.

**Le critère, écrit avant le code.** Les ventes à un seul lot bâti sur plusieurs parcelles portent
deux fois plus de terrain et un prix au m² brut inférieur de 18 %, mais à commune et année égales
leur ratio médian au prix de la commune vaut 0,97 et 0,98 contre 1,00. L'écart vient du lieu. Elles
sont admises sans seuil de terrain, comme une vente sur une parcelle. **Limite écrite** : ce
contrôle ne couvre que la moitié des candidates, celles des communes qui ont déjà du support.

**Transformation version 5, réimport du 35 :**

| | Version 4 | Version 5 |
|---|---:|---:|
| Allouables 2021-2025 | 49 820 | **59 869** |
| Allouables 2014-2020 | 84 747 | **103 747** |
| `multiple_parcels` 2021-2025 | 33 973 | 39 |
| Mutations sans prix allouable, 2021-2025 | 62,6 % | **55,0 %** |
| Baromètre : ventes exploitables | 75 178 | **101 358** |
| Baromètre : paires de reventes retenues | 1 505 | **2 410** |
| Communes à 30 ventes de maison sur 5 / 12 ans | 185 / 282 | **249 / 315** |

Le prix médian maison départemental baisse d'environ 120 €/m² par année : effet de composition,
ces ventes étant plus rurales. BAR-005 à BAR-007 (DPE → acte) sont inchangés octet pour octet.

**Ce que les recomptes ont fait corriger :**

- deux chiffres de prose du baromètre écrits à la main depuis H1 (« cent cinq » couples du même
  jour, « 10 100 » combinaisons) : désormais calculés, 142 et 13 219 ;
- le document arrondissait la part « au-delà de +20 % » à l'entier, au pair (76 % pour 76,5) : il
  l'imprime désormais telle que le CSV la porte ; « requis » accordé ;
- `dvf-quality-35.md` publiait des chiffres d'avant la version 4 (45 947 allouables, 2 586 € de
  médiane, 287 dépendances) sous un en-tête de version 4 : corrigés, avec la trace ;
- le rapport du baromètre écrit maintenant la commune d'une vente (celle de la mutation DVF), la
  recette de l'empreinte, la borne « le jour même compris » de BAR-004 et la version de
  transformation DVF.

**Non repris :** la clé de déduplication des lots de terrain d'un acte sans bâti (une ligne par
parcelle, quelle que soit la culture) n'est pas changée ; le recompte la signale comme un choix non
écrit, qui rend allouable une parcelle vendue seule avec deux cultures (1 228 ventes en version 5).

**H3 n'a pas commencé** : les dix-neuf documents sont régénérés avant la première session, comme
le ticket le prévoyait. Chacun tient sur deux pages A4.
