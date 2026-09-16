# H2 — Mettre en forme le baromètre : un document publiable par EPCI, hors plateforme

**Version :** V5 · baromètre · **Taille :** M · **État :** À faire
**Nature :** implémentation · **Touche :** pipelines/scripts/market_barometer_kit.py, pipelines/tests/test_market_barometer_kit.py, Makefile, docs/data/barometre-marche-35/
**Dépend de :** H1 · **Bloque :** H3
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)

## Contexte à charger

- `docs/backlog/H1-barometre-marche-35-mesures.md`
- `pipelines/scripts/field_test_kit.py` (génération HTML autonome, modèle à reprendre)
- `docs/data/barometre-marche-35.md` (sortie de H1)

Ne rien charger d'autre sans nécessité démontrée.

## Ce que H1 a livré, et ce qu'il laisse à trancher

Les CSV de `docs/data/barometre-marche-35/` portent tous les mêmes deux premières colonnes,
`scope_type` et `scope_code` — `departement`, `epci` ou `commune` — puis l'effectif, la valeur et
le motif d'absence. Une page EPCI se construit en filtrant sur `scope_type = epci`. Un fichier par
mesure : `bar-001-002-volumes-prix.csv`, `bar-003-plus-value-prix-entree.csv`,
`bar-004-etiquette.csv`, `bar-005-delai-dpe-acte.csv`, `bar-006-taux-mutation-12-mois.csv`,
`bar-007-courbe-conversion.csv`, `bar-008-extension-surface.csv`, `bar-009-couverture.csv`, plus
`epci-communes.csv` pour le rattachement.

**Les EPCI n'ont pas de nom.** Le rattachement commune → EPCI vient de l'attribut
`code_epci_insee` de DS-03 BDNB, qui ne porte que le SIREN. Une page titrée « EPCI 243500139 » ne
tient pas devant un professionnel. Trois issues, à trancher dans ce ticket : titrer par la commune
la plus peuplée de l'EPCI et lister les autres ; importer un référentiel de noms, ce qui demande
un contrat de source et donc un ticket à part ; ou publier le SIREN tel quel. Aucune n'est
choisie ici.

## Ce que ce ticket produit

`make market-barometer-kit DEPARTMENT=35` génère, depuis les CSV de H1, un document HTML autonome
imprimable en PDF : une page pour le département, une page par EPCI avec support, chacune portant
les mêmes rubriques dans le même ordre. C'est ce document que H3 met entre les mains des
professionnels, et c'est le premier artefact public du projet.

## Forme

- Une page = un EPCI. Quatre rubriques : le marché (volumes, prix), la marge (plus-value par prix
  d'entrée), l'énergie (décote par étiquette, réserve réforme 2026), le tempo (délai DPE → acte,
  taux de mutation à 12 mois, courbe).
- Chaque chiffre porte son effectif et sa période. Une rubrique sans support affiche « support
  insuffisant : n » plutôt qu'une valeur.
- Graphiques en SVG inline, sans dépendance réseau, palette neutre ; la compétence `dataviz` est
  chargée avant le premier graphique.
- Mentions obligatoires en pied de page : sources (DVF Etalab, DPE ADEME, cadastre), millésimes,
  date de génération, attribution Licence Ouverte 2.0, et la phrase « aucune parcelle ni adresse
  n'est identifiable dans ce document ».
- Pas de front React, pas d'API, pas d'authentification : un fichier par EPCI dans
  `docs/data/barometre-marche-35/`.

## Critères d'acceptation

- le document se régénère à l'identique depuis les CSV de H1 ;
- test : une page EPCI sans support pour une rubrique affiche l'effectif et non une valeur ;
- test : aucune chaîne de type identifiant cadastral (`\d{5}\d{3}[A-Z]{2}\d{4}`) ni adresse
  n'apparaît dans la sortie ;
- relecture visuelle du PDF sur une page A4, chiffres lisibles à taille d'impression ;
- `make check` vert.
