# B3 — Rapport de distribution et métriques d'appariement par commune

**Version :** v0.3 · **Taille :** M · **État :** Terminé
**Dépend de :** B1, B2a, B2b · **Bloque :** B4

## Contexte à charger

- `pipelines/src/immo_pipelines/spatial/resolution.py`
- `pipelines/src/immo_pipelines/spatial/importer.py` (`refresh_match_metrics`)
- `docs/data/spatial-reference-35-report.md`
- `contracts/features/morphology-v1.json`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.3 exige que « le taux d'appariements certains et ambigus soit mesuré par commune ». Les métriques
existent pour le couple RNB ↔ Cadastre — persistées pour les 332 communes — mais pas pour les
relations impliquant BAN, BDNB et BD TOPO, dont les releases ne sont pas encore acceptées.

La DoD de la version reste ouverte sur ce point :

```text
- [ ] Métriques et échantillon de validation produits.
```

## Contenu attendu du rapport

Pour **chaque** relation, la distribution complète en quatre classes, jamais trois :

| Relation | certain | ambigu | rejeté | non apparié |
|---|---|---|---|---|
| Bâtiment ↔ Parcelle | | | | |
| Adresse ↔ Parcelle | | | | |
| Adresse ↔ Bâtiment | | | | |
| Bâtiment BD TOPO ↔ Bâtiment RNB | | | | |
| Groupe BDNB ↔ Bâtiment RNB | | | | |

Et pour chacune :

1. la **méthode** ayant produit l'appariement, selon l'ordre de préférence de v0.3 : identifiant
   officiel, relation source explicite, intersection spatiale, proximité, adresse normalisée,
   cohérence temporelle — avec le volume par méthode ;
2. la ventilation **par commune**, persistée en base et non seulement écrite dans un document ;
3. la distribution des scores de confiance, pas seulement leur moyenne ;
4. les cas non appariés avec leur motif, distingués des cas rejetés.

## Résultat au 8 septembre 2026

Rapport livré : [`spatial-matching-distribution-35.md`](../data/spatial-matching-distribution-35.md),
**généré** et non saisi. Régénération :

```bash
make matching-report DEPARTMENT=35
```

La cible recalcule les métriques avant de rendre — le document ne peut donc pas décrire un état
périmé.

| Relation | certain | ambigu | rejeté | non apparié | total |
|---|---:|---:|---:|---:|---:|
| Bâtiment ↔ Parcelle | 737 353 | 0 | 0 | 4 010 | 741 363 |
| Adresse ↔ Parcelle | 248 209 | 1 759 | 2 685 | 184 788 | 437 441 |
| Adresse ↔ Bâtiment | 393 355 | 0 | 0 | 44 086 | 437 441 |
| Bâtiment BD TOPO ↔ Bâtiment RNB | 692 621 | 90 841 | 0 | 17 711 | 801 173 |
| Groupe BDNB ↔ Bâtiment RNB | 422 194 | 104 823 | 0 | 19 284 | 546 301 |

Le rapport porte aussi le volume par méthode, la distribution des confiances, la cardinalité
réelle — maximum de 37 parcelles pour un bâtiment, 80 bâtiments pour un groupe BDNB — et les
communes extrêmes de chaque relation, toujours avec leur volume à côté du taux.

## Deux défauts trouvés en produisant le rapport

**La relation adresse ↔ bâtiment était structurellement vide.** Elle était calculée dans
`_publish_stage` de l'importeur BAN, donc **au moment de l'import et contre les seules données RNB
présentes à cet instant**. Le RNB ayant été importé après la BAN, la jointure ne produisait aucune
ligne — sans échouer. Elle est désormais recalculable indépendamment de l'ordre d'import :
566 248 relations, 393 355 adresses rattachées de façon certaine, 89,9 %.

**Les statistiques comptaient plus que le réglage de [BUG-06](./BUG-06-reglage-postgresql.md).**
Après insertion de ces 566 248 relations, la métrique qui les lit a tourné **4 h 44 sans
aboutir** ; statistiques rafraîchies, **2,2 s**. Le planificateur estimait 5 000 lignes là où il y
en avait 437 441. `ANALYZE` exigeant d'être propriétaire de la table, `pipeline_rw` se contentait
d'un avertissement et sautait la table. Détail et portée dans
[`postgresql-tuning.md`](../operations/postgresql-tuning.md).

## Ce qui reste ouvert

- Les trois autres importeurs n'analysent pas après leur import et sont exposés au même défaut.
  À rattacher à [BUG-02](./BUG-02-scripts-import-hors-dagster.md), dont le passage à Dagster est
  l'occasion d'y placer un `ANALYZE` de fin d'asset.
- Aucune des 332 communes n'est « non couverte » : le mécanisme qui distingue ce cas d'un taux nul
  existe et est testé, mais aucune donnée réelle ne le déclenche aujourd'hui.

## Points de vigilance

- « Non apparié » et « rejeté » ne sont pas la même chose et ne doivent jamais être additionnés :
  le premier est une absence, le second une décision.
- Un taux d'appariement élevé sur une commune à faible volume n'a pas la même valeur qu'un taux
  identique sur Rennes. Le rapport doit exposer le volume à côté du taux.
- La cardinalité réelle doit rester visible : le maximum observé est de 37 parcelles pour un
  bâtiment, et cette cardinalité est modélisée nativement. Un rapport qui n'exposerait qu'un ratio
  moyen masquerait cette réalité.
- Les communes où une relation est structurellement impossible (source absente sur ce territoire)
  doivent être marquées comme telles, pas comptées à zéro.

## Tests obligatoires

- les métriques par commune sont recalculables et stables après réimport ;
- la somme des quatre classes égale le volume total de la relation, pour chaque commune ;
- une commune sans donnée source produit un état « non couvert » distinct d'un taux nul ;
- le rapport se régénère par une commande, sans saisie manuelle.

## Critères d'acceptation

- distribution en quatre classes disponible pour chaque relation et chaque commune ;
- volume par méthode d'appariement documenté ;
- aucun taux publié sans son volume ;
- les métriques sont persistées et exposées à l'administration (FR-012).

## Preuves à produire

- rapport `docs/data/spatial-matching-distribution-35.md` ;
- mise à jour de [`spatial-reference-35-report.md`](../data/spatial-reference-35-report.md) ;
- requête ou commande de régénération référencée dans le rapport.
