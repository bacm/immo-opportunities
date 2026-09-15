# E8g — Porter dans la liste des biens en vente ce que la courbe de conversion, l'étiquette et la commune disent déjà

**Version :** v0.6 · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/market_listing_candidates.py, pipelines/tests/test_market_listing_candidates.py, docs/data/biens-en-vente/, docs/data/biens-en-vente-35051.md, docs/data/listing-candidates/, docs/data/listing-candidates-35051.md, docs/data/dpe-signal-vente-35.md, docs/backlog/E8f-liste-biens-en-vente.md, Makefile
**Dépend de :** E8f · **Bloque :** E9
**Demandé par :** exploration du 15 septembre 2026 — [`pistes-analyse-marche-35.md`](../data/pistes-analyse-marche-35.md) §5

## Contexte à charger

- `docs/data/pistes-analyse-marche-35.md` — section 5 seulement
- `pipelines/scripts/market_listing_candidates.py`
- `docs/data/dpe-signal-vente-35.md`

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi

La liste de E8f dit « un DPE a été déposé à cette date » et porte un seul taux, départemental, à
douze mois. Les sondages du 15 septembre montrent que trois choses de plus sont **observées**, pas
modélisées, et changent la lecture d'un candidat :

- la conversion est en S — presque rien avant trois mois, la moitié entre trois et six ; un DPE de
  six mois invendu n'a pas la même chance qu'un DPE de trois semaines ;
- les étiquettes F et G convertissent 40 % de plus que C et D ;
- le taux varie de 30 % à 52 % selon la commune, quand le support existe.

Un relecteur qui voit la date sans la courbe, l'étiquette sans son taux, et un chiffre
départemental pour une commune qui en est loin, juge la liste sur une information que nous avons
et ne lui donnons pas.

## Choix retenus

- **Trois colonnes, aucun seuil.** L'âge du dépôt à la date d'extrait, la chance de vente sur
  l'horizon suivant lue sur la courbe observée, le taux à douze mois de l'étiquette. Le taux de la
  commune va dans l'en-tête avec son effectif, **jamais masqué sous un minimum** : le relecteur
  voit `33,2 % (n = 271)` et juge lui-même.
- **La cohorte de référence est dérivée**, pas choisie : la dernière année civile dont les douze
  mois de suivi sont couverts par DVF. Elle avance seule quand un millésime arrive.
- **Population de mesure : les DPE de maison**, comme la liste. Les DPE d'appartement générés
  depuis un DPE d'immeuble convertissent à 0,6 % et pollueraient tout taux départemental.
- **L'horizon de la chance résiduelle est un paramètre déclaré arbitraire**, comme les fenêtres de
  fraîcheur — six mois par défaut, publié dans le rapport.
- **Les colonnes sont indépendantes.** Âge et étiquette ne se combinent pas : les combiner serait
  un modèle, et rien n'établit leur indépendance.
- **Les taux sont calculés par le script**, au moment de la génération, depuis la base. Le rapport
  cite ce qu'il a mesuré, pas un chiffre recopié d'un autre document.
- **La sortie s'appelle `biens-en-vente-<commune>.md`**, plus `listing-candidates-<commune>.md` :
  le nom disait « candidats » et se lisait comme la liste de divisibilité de E8. Demandé le
  15 septembre 2026 après une confusion réelle entre les deux listes. La cible Makefile suit.
- **À date égale, le premier DPE par numéro est retenu.** Le recompte indépendant a confirmé les
  quatre familles de chiffres mais montré que 79 parcelles portent deux DPE de maison le même jour
  avec des étiquettes différentes : sans départage déclaré, les effectifs par étiquette ne se
  reproduisent pas à l'unité.

## Travail à réaliser

1. Mesurer dans le script, sur le département de la commune : la courbe mensuelle de conversion
   de la cohorte de référence, le taux par étiquette, le taux de la commune avec son effectif.
2. Calculer par candidat l'âge du dépôt et la chance résiduelle, ou dire pourquoi elle manque.
3. Rendre les trois colonnes et l'en-tête, régénérer 35051.
4. Instruire l'écart de comptage de la cohorte 2024 — 9 754 avec relation `certain`, 14 532 dans
   `dpe-signal-vente-35.md` — et écrire dans ce rapport le filtre qu'il applique.

## Tests obligatoires

- la chance résiduelle se lit sur la courbe et vaut « non mesurée » au-delà de sa portée ;
- la cohorte de référence dérive de la date de fin de DVF ;
- une étiquette absente donne un taux absent, jamais zéro ;
- âge et étiquette ne sont jamais combinés en un score ;
- la mesure ne retient que les DPE de maison et les relations certaines.

## Critères d'acceptation

- liste 35051 régénérée, mêmes candidats à graine égale, trois colonnes de plus ;
- les taux du rapport sont ceux mesurés à la génération, cohorte et population nommées ;
- l'écart de comptage est expliqué ou consigné comme non expliqué.

## Preuve à produire

`docs/data/biens-en-vente-35051.md` régénéré ; recompte des taux par `recompte-preuve`.
