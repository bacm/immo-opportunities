# E8f — Une seconde liste : les biens probablement en vente, pour que E9 teste deux promesses

**Version :** v0.6 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/src/immo_pipelines/market_data/exploratory.py, pipelines/scripts/market_listing_candidates.py, pipelines/scripts/exploratory_candidates.py, pipelines/tests/, docs/data/listing-candidates/, Makefile
**Dépend de :** E8e · **Bloque :** E9
**Demandé par :** arbitrage du 15 septembre 2026

> Identifiant en `E8f` et non `E10` : la convention n'admet qu'un chiffre et une lettre
> ([BUG-16](./BUG-16-suffixes-de-tickets-limites.md)), et la série E est pleine. Ce ticket reste
> dans la famille « produire une liste exploratoire », ouverte par
> [E8](./E8-liste-exploratoire-terrain.md).

## Contexte à charger

- `docs/data/dpe-signal-vente-35.md`
- `docs/backlog/E8-liste-exploratoire-terrain.md`
- `pipelines/scripts/exploratory_candidates.py`

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi une seconde liste

La liste de E8 répond à « où pourrait-on construire ». Le besoin exprimé est « qui vend ». Ce ne
sont pas deux versions de la même promesse, et rien n'établit que le même professionnel veuille
les deux.

[`dpe-signal-vente-35.md`](../data/dpe-signal-vente-35.md) mesure que le second est atteignable :
sur les parcelles dont le premier DPE a été déposé en 2024, **35,65 % mutent dans les douze mois**,
contre **3,03 %** pour l'ensemble des parcelles bâties — **lift × 11,8**. Et le dépôt précède
l'acte de 169 jours en médiane, soit environ 80 jours avant le compromis : le signal arrive à la
mise en vente, pas après.

`E9` doit donc départager les deux promesses, pas seulement mesurer la précision de l'une.

## Ce qui sépare cette liste de la première

| | E8 | E8f |
|---|---|---|
| Question | où pourrait-on construire | qui est sur le marché |
| Sélection | morphologie et divisibilité | fraîcheur du dépôt de DPE |
| Baseline | tri cadastral par surface | **même population, DPE ancien** |
| Vérité terrain | aucune | 35,65 % contre 3,03 %, mesurés |

La baseline isole exactement la revendication : à population résidentielle identique, la fraîcheur
du dépôt change-t-elle quelque chose ? Un tri par surface n'y répondrait pas.

## La date de référence n'est pas aujourd'hui

Le DPE le plus récent de notre extrait est du **7 septembre 2026**, et 19 096 diagnostics ont été
déposés depuis mars. La fenêtre de fraîcheur se compte depuis cette date d'extrait, jamais depuis
l'horloge : sans quoi la liste se viderait toute seule à mesure que l'extrait vieillit, sans que
rien ne le signale.

## Travail à réaliser

1. Extraire dans `immo_pipelines.market_data.exploratory` ce que les deux listes partagent — mise
   en aveugle, affichage des absences, écriture CSV, prédicats d'usage, rang moyen — et faire
   importer E8 depuis là. Justification : un second consommateur réel, pas une abstraction
   anticipée.
2. Écrire `market_listing_candidates.py` : cohorte à DPE frais, baseline à DPE ancien, même
   population résidentielle individuelle que E8b.
3. Écarter les parcelles dont une mutation est **postérieure** au dépôt : elles ont déjà vendu.
4. Porter les preuves du candidat : date de dépôt, étiquette, surface habitable, année de
   construction, dernière mutation connue, zone, morphologie.
5. Mélanger les deux cohortes sous la même graine, correspondance à part.
6. Écrire dans le rapport les quatre limites de la mesure, dont les deux sérieuses : motif du
   diagnostic non publié, et DVF arrêtée au 31 décembre 2025.

## Ce que ce ticket ne fait pas

- **Annoncer qu'un bien sera vendu.** La liste dit « DPE déposé le … », et le rapport porte le taux
  observé. Deux tiers des parcelles à DPE frais ne mutent pas dans l'année.
- **Distinguer vente et location.** `methode_application_dpe` ne donne pas le motif. La dilution
  est dans le 35,65 %, elle n'est pas corrigée après coup.
- **Publier quoi que ce soit.** Aucun snapshot, aucune unité ne devient publiable, comme E8.

## Tests obligatoires

- une parcelle dont une mutation suit le dépôt du DPE est écartée ;
- la fenêtre de fraîcheur se calcule depuis la date d'extrait, pas depuis l'horloge ;
- cohorte et baseline sortent de la même population résidentielle individuelle ;
- une parcelle sans DPE n'apparaît dans aucune des deux ;
- les helpers extraits restent accessibles depuis le script de E8.

## Critères d'acceptation

- deux listes produites sur une commune réelle, mélangées et traçables ;
- baseline à DPE ancien, tirée de la même population ;
- les quatre limites écrites dans le rapport ;
- la liste de E8 est inchangée — même entonnoir, mêmes candidats à graine égale.

## Preuve à produire

`docs/data/listing-candidates-<commune>.md` : cohortes, fenêtres, entonnoir, preuves par candidat,
limites.
