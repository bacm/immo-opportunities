# E8h — Rendre les deux listes présentables : localiser chaque bien, et donner de quoi saisir les verdicts

**Version :** v0.6 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/src/immo_pipelines/market_data/exploratory.py, pipelines/scripts/exploratory_candidates.py, pipelines/scripts/market_listing_candidates.py, pipelines/scripts/field_test_kit.py, pipelines/tests/test_exploratory_candidates.py, pipelines/tests/test_market_listing_candidates.py, pipelines/tests/test_field_test_kit.py, docs/data/exploratory-candidates/, docs/data/exploratory-candidates-35051.md, docs/data/biens-en-vente/, docs/data/biens-en-vente-35051.md, docs/data/field-test-35/, Makefile
**Dépend de :** E8g · **Bloque :** E9
**Demandé par :** revue du 15 septembre 2026 — « il manque quoi pour la présentation ? »

## Contexte à charger

- `docs/backlog/E9-test-terrain-deux-professionnels.md` — section « Protocole »
- `pipelines/src/immo_pipelines/market_data/exploratory.py`
- `docs/data/biens-en-vente/35051/liste-aveugle.csv` et `docs/data/exploratory-candidates/35051/liste-aveugle.csv`

Ne rien charger d'autre sans nécessité démontrée.

## Ce qui manquait

Trois choses, constatées le 15 septembre 2026 en relisant les deux listes avec l'œil d'un marchand :

1. **On ne peut pas trouver les biens.** Aucune liste ne porte d'adresse ni de position. Un
   identifiant cadastral ne se juge pas.
2. **Rien pour saisir les verdicts.** Le protocole E9 demande, par candidat, pertinent / non
   pertinent / indécidable avec le motif, et « connu ou inconnu » pour H2. Aucune grille n'existe.
3. **Le format n'est pas présentable.** Douze et dix-sept colonnes en Markdown, illisibles
   imprimées ou projetées.

## Choix retenus

- **Deux localisations de nature différente, nommées comme telles.** Pour les biens en vente,
  l'adresse est celle **déclarée sur le DPE** : elle vient du diagnostic, pas d'un appariement.
  Pour les deux listes, le centroïde de la parcelle en WGS84 et un lien vers le Géoportail, couche
  parcellaire sur orthophoto. Aucun lien adresse ↔ parcelle n'est calculé : v0.3 a établi que
  cette relation n'est vérifiable par aucune règle, et ce ticket ne la réinvente pas.
- **Le kit lit les listes aveugles, jamais la correspondance.** Il ne peut donc pas trahir
  l'origine. Il ne touche pas à la base : un consommateur de fichiers, testable sans PostgreSQL.
- **Une fiche par candidat, imprimable**, avec ses preuves en clair et un cadre de verdict à la
  main ; **une grille CSV par liste** pour la saisie ; **un gabarit de compte rendu** qui suit le
  protocole E9 — méthode actuelle, verdicts, H1, H2, H3, H5, verbatims, conclusion. Le gabarit
  n'est pas `field-test-results-35.md` : ce fichier est la preuve de E9, un verrou humain, et il
  n'existera que rempli.
- **Le nombre de candidats n'est pas changé ici.** Les deux listes gardent leurs 35 et 38 cas ;
  réduire à 20 par liste est un paramètre existant (`SIZE`), à décider avec la commune retenue.

## Ce que ce ticket ne fait pas

- Fixer le prix de H5, ni recruter : décisions humaines, préalables à la génération finale.
- Publier quoi que ce soit, ni passer par l'Explorer.
- Rattacher une adresse à une parcelle divisible par géométrie.

## Tests obligatoires

- la grille de saisie ne porte aucune colonne d'origine, et le kit ne lit pas `correspondance.csv` ;
- une adresse ou une position absente s'affiche absente, avec son motif, jamais vide ;
- le lien de carte se construit depuis le centroïde et n'est jamais émis sans lui ;
- chaque référence de la liste aveugle a sa fiche ;
- les deux listes restent identiques à graine égale — mêmes candidats, colonnes en plus.

## Critères d'acceptation

- `make field-test-kit COMMUNE=35051` produit fiches, grilles et gabarit sous
  `docs/data/field-test-35/35051/` depuis les deux listes régénérées ;
- la liste des biens en vente porte l'adresse du DPE ; les deux listes portent le centroïde et
  le lien de carte ;
- le gabarit reprend les six étapes du protocole E9 et ses cinq hypothèses telles quelles.

## Preuve à produire

`docs/data/field-test-35/35051/` : deux fiches HTML, deux grilles CSV ; `docs/data/field-test-35/gabarit-compte-rendu.md`.
