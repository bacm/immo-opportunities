# E9 — Confronter la liste à deux professionnels, et mesurer H1, H2 et H5

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Nature :** revue humaine · **Preuve :** docs/data/field-test-results-35.md
**Dépend de :** E8 · **Bloque :** —
**Demandé par :** revue de but du 15 septembre 2026

## Contexte à charger

- `docs/backlog/E8-liste-exploratoire-terrain.md`
- `docs/backlog/G8-pilote-trois-professionnels.md` (protocole de référence)
- `SPEC.md` §5 (hypothèses) et §22 (monétisation) — ces sections seulement

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket décide

**Si le produit a un objet.** Il n'y a pas de verdict technique à cette question : aucun test, aucun
backtest et aucune revue interne ne remplacent un professionnel qui regarde une liste et dit si
elle lui sert. C'est le verrou dont dépend l'intérêt de tout le reste du backlog.

Il est volontairement plus petit que [G8](./G8-pilote-trois-professionnels.md) : deux professionnels,
une commune, une liste, aucune application à installer. G8 reste la validation complète et garde
ses exigences ; celui-ci sert à ne pas y arriver avec une promesse fausse.

## Prérequis

Un seul : la liste de [E8](./E8-liste-exploratoire-terrain.md). Ni E1, ni E3, ni F1, ni
l'extension régionale.

Le recrutement de deux à trois marchands de biens ou investisseurs-rénovateurs bretons est la
première tâche, et elle conditionne la commune retenue par E8.

## Hypothèses mesurées, et celles qui ne le sont pas

| # | Hypothèse | Mesurable ici | Comment |
|---|---|---|---|
| H1 | Le classement bat un tri cadastral simple | **oui** | verdict en aveugle, candidat par candidat, sur les deux listes mélangées |
| H2 | Le produit révèle des biens inconnus de lui | **oui** | part des candidats qu'il déclare ne pas connaître |
| H3 | Les preuves sont comprises sans accompagnement | partiellement | lui faire expliquer un candidat **avec ses mots** |
| H4 | Le produit réduit le temps de qualification | **non** | demande un avant/après instrumenté — reste à G8 |
| H5 | Le résultat justifie un abonnement | **oui** | question de prix explicite, chiffrée |

H5 est la seule mesure résistante au biais de complaisance, et c'est la raison de la poser même à
deux personnes : un professionnel dira volontiers qu'un outil est intéressant, beaucoup moins
volontiers qu'il le paierait 79 € par mois.

## Protocole

1. Relever la **méthode actuelle** du professionnel avant de montrer quoi que ce soit : sans point
   de comparaison, H1 et H2 ne veulent rien dire.
2. Présenter la liste mélangée, sans dire qu'elle contient deux origines.
3. Verdict par candidat : pertinent / non pertinent / indécidable, **avec le motif en clair**.
4. Ne rien corriger ni justifier pendant la session. Les objections sont la donnée.
5. Poser H5 en fin de session, avec un prix, et enregistrer la réponse telle quelle.
6. Conserver les verdicts négatifs, les hésitations et les abandons.

## Ce qu'il faut spécifiquement écouter

- **« Ce n'est pas un bien »** — la limite de [BUG-11](./BUG-11-unite-fonciere-degeneree.md).
  Si elle revient spontanément et rend la liste inutilisable, elle cesse d'être un bug de
  résolution d'entités et devient une question de périmètre produit.
- **Quel signal manque** — le motif de rejet le plus fréquent désigne la donnée à chercher ensuite,
  et vaut mieux qu'un profiling sur des features que personne ne regarde.
- **Quelle stratégie l'intéresse** — `SPEC.md` §25 pose encore la question. La donnée soutient
  aujourd'hui bien mieux le gisement foncier divisible que la rénovation-revente, dont dépend
  l'état du bâti (DPE rattaché à 59 %, familles REN et BLD non matérialisées).

## Critères d'acceptation

- deux professionnels au minimum, méthode actuelle relevée avant session ;
- verdict par candidat sur les deux listes, en aveugle, motifs conservés ;
- H1, H2 et H5 documentées, **y compris défavorablement** ;
- verbatims conservés, y compris ceux qui contredisent le produit ;
- limite méthodologique énoncée : deux personnes n'autorisent aucun pourcentage ni aucune
  inférence statistique ;
- une conclusion explicite parmi : *poursuivre le plan*, *recadrer le périmètre*, *arrêter* — et
  cette conclusion alimente [G9](./G9-decision-finale.md).

## Preuve à produire

`docs/data/field-test-results-35.md` : profils, méthode actuelle de chacun, déroulé, verdicts par
candidat, résultats H1/H2/H3/H5, verbatims, objections non résolues, conclusion et sa date.
