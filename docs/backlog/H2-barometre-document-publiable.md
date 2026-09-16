# H2 — Mettre en forme le baromètre : un document publiable par EPCI, hors plateforme

**Version :** V5 · baromètre · **Taille :** M · **État :** Terminé
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
un contrat de source et donc un ticket à part ; ou publier le SIREN tel quel.

**Tranché le 16 septembre 2026 par le porteur du projet : SIREN et liste des communes.** Aucune
source nouvelle avant H3 ; le professionnel reconnaît son territoire à ses communes. Titrer par
une commune aurait demandé une règle de choix, et la population est une source réservée (DS-10).
Les noms de communes restent ceux du cadastre, en capitales sans accents et parfois tronqués
(« CHATEAUNEUF-D ILLE-ET-VILAI ») : c'est la source, pas une transformation. Un référentiel de
noms — le Code officiel géographique — ne s'ouvre que si H3 garde le document.

Le porteur a aussi écarté une reprise visuelle dans Claude Design avant H3 : les entretiens
diront si le document plaît avant qu'on le peaufine.

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

## Ce qui a été produit

`make market-barometer-kit DEPARTMENT=35` écrit, depuis les seuls CSV de H1, dix-neuf documents
dans `docs/data/barometre-marche-35/` : `document-departement-35.html` et un
`document-epci-<SIREN>.html` par EPCI ayant au moins une mesure publiable — les dix-huit en ont.
Aucune base, aucune bibliothèque, aucune ressource réseau ; les graphiques sont du SVG écrit à
la main. La date imprimée est celle des mesures, lue dans `metadonnees.csv` : la sortie est une
fonction pure des CSV.

Choix retenus :

- **Une feuille A4, deux faces.** Le recto porte les quatre rubriques de `SPEC.md` §7.1, un
  chiffre et un graphique chacune. Le verso porte les mêmes chiffres en tableaux, avec
  effectifs, motifs d'absence et filtres : c'est la vue tableau que la compétence `dataviz`
  exige de tout graphique, et c'est lui qui rend chaque nombre du recto vérifiable. « Une page =
  un EPCI » est tenu au sens d'une feuille ; le recto se lit seul.
- **Une rubrique sans support ne montre ni valeur ni graphique vide** : un bloc « support
  insuffisant » avec l'effectif, puis la ligne des effectifs par tranche ou par étiquette.
  Jamais la valeur du département à la place — dix-sept EPCI sur dix-huit n'ont pas de marge
  publiable, et c'est ce que leur page dit.
- **Palette** : bleu et orange pour maisons et appartements, rampe ordinale bleue pour les
  tranches de prix d'entrée, validées par le script de `dataviz` en clair et en sombre. Le
  sombre ne sert qu'à l'écran ; l'impression force le clair.
- **La mention de recompte suit l'attestation de H1** : « Chiffres recomptés le … » si
  l'empreinte des mesures est attestée, sinon « Non recompté — document de travail, ne pas
  diffuser ».
- **Relecture visuelle** faite sur l'impression PDF de Chrome : chaque document tient sur deux
  pages A4 exactement, chiffres à 7,2 pt au moins. Elle a corrigé la légende des prix, la
  formulation des tranches, l'axe asymétrique de l'énergie, l'année portée par une étiquette de
  fin de série, et les motifs du verso.

## Ce que le recompte des documents a attrapé

Les trois recomptes de H1 portaient sur les CSV. Les documents publient aussi ce qu'ils
calculent, et une passe de `recompte-preuve` en isolement du code l'a éprouvé sur les dix-neuf
pages. La transcription est fidèle — effectifs, médianes, quartiles, taux, délais, absences,
aucune valeur départementale substituée. Mais **quatre chiffres dérivés étaient faux d'un
point** : la variation « sur un an » de trois EPCI et l'écart F / D d'un quatrième. Tous
venaient du même défaut, **un calcul fait sur des médianes déjà arrondies**.

Le correctif n'arrondit pas mieux : **le document ne calcule plus aucun chiffre**. La variation
sur un an est retirée, la courbe montre la tendance. L'écart F / D, différence de deux médianes
lue à tort comme un écart relatif, est remplacé par l'écart médian de l'étiquette F elle-même, lu
tel quel dans le CSV — la médiane d'un écart est exacte par translation. Un test garde la règle.

Cinq libellés corrigés au passage : « de toute nature » pour un événement qui exclut l'échange ;
« au-delà de 15 ventes » pour un seuil inclusif ; « ventes » pour des parcelles vendues ; « moins
de trois ans » sans la borne des six mois ; « plus-value nette », lisible comme nette de frais,
devenu « gain au-delà du marché ». Les cellules sans vente affichent un tiret, conformément à la
convention de H1, et plus un zéro.

**La relecture visuelle a aussi attrapé un défaut que les tests ne voyaient pas** : la hauteur
fixe du recto masquait un débordement, et le pied du recto se superposait au verso. La hauteur
fixe est retirée ; un débordement produit désormais une page de plus, ce qui se compte. Les
dix-neuf documents imprimés tiennent sur deux pages exactement.

## Critères d'acceptation

- le document se régénère à l'identique depuis les CSV de H1 ;
- test : une page EPCI sans support pour une rubrique affiche l'effectif et non une valeur ;
- test : aucune chaîne de type identifiant cadastral (`\d{5}\d{3}[A-Z]{2}\d{4}`) ni adresse
  n'apparaît dans la sortie ;
- relecture visuelle du PDF sur une page A4, chiffres lisibles à taille d'impression ;
- `make check` vert.

## Correction consignée — 16 septembre 2026

« Dix-sept EPCI sur dix-huit n'ont pas de marge publiable » ne valait que pour la marge
**complète**, les quatre tranches de prix d'entrée. Au CSV de ce ticket, 1 EPCI les publiait
toutes, 6 au moins une, 12 aucune. Depuis [H7](./H7-mutations-multi-parcelles.md) : 2, 13 et 5.
La règle qui suit la phrase — jamais la valeur du département à la place — n'en dépend pas.

