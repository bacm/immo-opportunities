# B3 — Rapport de distribution et métriques d'appariement par commune

**Version :** v0.3 · **Taille :** M · **État :** À faire
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
