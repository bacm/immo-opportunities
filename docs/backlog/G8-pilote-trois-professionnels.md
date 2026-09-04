# G8 — Trois professionnels sur cas réels, dataset `CandidateReview`, H1–H5

**Version :** v0.8 · **Taille :** XL · **État :** À faire
**Dépend de :** G3, G4 · **Bloque :** G9

> **C'est la validation décisive du produit.** Tout le reste est de l'instrumentation. Aucun test
> automatique, aucun backtest et aucune revue interne ne remplace le jugement de trois
> professionnels sur des cas réels.

## Contexte à charger

- `docs/data/brittany-pilot-v0.8-report.md`
- `scripts/export-pilot-metrics`
- `backend/src/immo/brittany_pilot.py`
- `SPEC.md` (§21 plan de validation uniquement)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

État actuel : « 3 professionnels sur cas réels — **aucun résultat enregistré** — bloqué ».

Le produit s'adresse à un marchand de biens ou un investisseur-rénovateur qui veut classer des
actifs à approfondir selon deux stratégies : division/extension et rénovation-revente. La seule
question qui compte est : **cela leur fait-il gagner du temps et leur montre-t-il des biens qu'ils
n'auraient pas trouvés seuls ?**

## Prérequis

| Prérequis | Ticket |
|---|---|
| Candidats réels publiés | [E3](./E3-publier-snapshots.md) |
| Parcours vérifié sans fixture | [F1](./F1-parcours-reel-sans-fixture.md), [F2](./F2-verification-fr-001-012.md) |
| Isolation des organisations en conditions production | [F3](./F3-isolation-organisations.md) |
| Couverture territoriale documentée | [G4](./G4-couverture-documentee.md) |
| Exploitation et rollback éprouvés | [G5](./G5-administration-bundle.md), [G6](./G6-exploitation-restauration.md) |

Ne pas lancer le pilote avant : un professionnel qui rencontre une donnée manifestement fausse lors
de sa première session ne reviendra pas, et la mesure sera perdue.

## Hypothèses à mesurer

| # | Hypothèse | Mesure |
|---|---|---|
| H1 | **Lift** : le classement bat un tri cadastral simple | comparaison aveugle top-N produit vs baseline |
| H2 | **Nouveauté** : le produit révèle des biens que le professionnel n'aurait pas identifiés | part de candidats jugés inconnus de lui |
| H3 | **Compréhension** : les preuves de score sont comprises sans accompagnement | capacité à expliquer pourquoi un bien est classé haut |
| H4 | **Temps** : le produit réduit le temps de qualification | durée mesurée avec et sans l'outil |
| H5 | **Intention de payer** | déclaration explicite, prix et modalité |

## Protocole

1. Recruter trois professionnels sur des territoires distincts et des profils contrastés.
2. Faire précéder chaque session d'un relevé de la méthode actuelle du professionnel : sans point
   de comparaison, H1 et H4 ne sont pas mesurables.
3. Chaque professionnel qualifie un ensemble de candidats réels et remplit le dataset
   `CandidateReview` : pertinence, intérêt, motif de rejet, action envisagée.
4. Conduire H1 en aveugle : le professionnel ne doit pas savoir quels candidats viennent du score
   et lesquels de la baseline.
5. Conserver les verdicts négatifs et les abandons de session : ce sont les données les plus
   informatives.
6. Ne pas corriger le produit en cours de pilote sans le noter — sinon les mesures ne sont pas
   comparables entre professionnels.

## Points de vigilance

- **Le biais de complaisance est le principal risque.** Un professionnel invité à tester un outil
  dira volontiers qu'il est intéressant. H5 (intention de payer, avec un prix) est la seule mesure
  résistante à ce biais.
- Trois participants ne permettent aucune inférence statistique. Les résultats sont qualitatifs et
  doivent être présentés comme tels — un pourcentage sur trois personnes serait trompeur.
- H3 se mesure en écoutant le professionnel expliquer un score **avec ses mots**, pas en lui
  demandant s'il a compris.
- Le dataset `CandidateReview` a une valeur au-delà du pilote : c'est la première donnée de
  validation terrain du projet. Sa qualité de saisie compte autant que les conclusions.

## Critères d'acceptation

- trois professionnels ont conduit des sessions réelles sur des candidats publiés ;
- dataset `CandidateReview` constitué et exploitable ;
- H1 à H5 mesurées et documentées, y compris défavorablement ;
- méthode de référence de chaque professionnel relevée avant les sessions ;
- limites méthodologiques explicitement énoncées.

## Preuve à produire

Rapport `docs/data/field-pilot-results.md` : protocole, profils, déroulé, résultats par hypothèse,
verbatims, limites, dataset `CandidateReview` exporté.
