---
name: recompte-preuve
description: Recalculer, depuis les sources, les chiffres d'un rapport de docs/data/ ou d'un contrat. À lancer après toute étape qui publie une volumétrie, un taux de couverture ou un taux d'appariement — avant de considérer le ticket terminé. Ne pas utiliser pour relire du code : c'est un recomptage, pas une revue.
---

# Recompte d'une preuve

## Ce que ce contrôle attrape, et ce qu'il n'attrape pas

BUG-12 était un comptage faux de 44 %, publié dans un rapport, cohérent avec le code qui l'avait
produit. Les tests passaient. Une relecture du diff l'aurait raté, parce qu'elle aurait vérifié que
le code fait ce qu'il dit — ce qu'il faisait.

Ce qui l'attrape est un **recomptage indépendant** : la même question posée aux sources par un autre
chemin. C'est la seule forme de validation par agent qui ajoute quelque chose à `make check`.

Ce contrôle ne dit rien de la **pertinence** d'un résultat — qu'un comparable soit défendable, qu'un
zonage corresponde au document opposable. Cela reste un verrou humain : B4, D6.

## Règle d'isolement

**Ne pas lire le code qui a produit le chiffre.** Ni le script d'import, ni le module de features,
ni le diff du ticket. Les lire, c'est refaire le raisonnement du producteur et retrouver son erreur.

À lire : le ticket (ce qui était demandé), le rapport (ce qui est affirmé), les contrats de dataset
(ce que la release contient), et les sources — base, archive pincée, catalogue amont.

## Marche à suivre

1. **Extraire les affirmations chiffrées** du rapport : volumétries, taux de couverture, taux
   d'appariement, comptes de quarantaine, nombres de communes. Chacune est une assertion à
   éprouver, y compris celles qui paraissent anodines.
2. **Écrire sa propre requête** pour chacune, sans copier celle du rapport. Quand deux formulations
   sont possibles — compter des enregistrements ou compter des objets, joindre à gauche ou
   filtrer — les écrire toutes les deux : l'écart entre elles *est* le défaut recherché.
3. **Vérifier l'unité avant la valeur.** « 514 859 bâtiments » et « 514 859 enregistrements » ne
   sont pas la même affirmation. La plupart des erreurs de cette famille sont des erreurs d'unité,
   pas d'arithmétique.
4. **Vérifier le périmètre** : département, release, version de transformation. Un chiffre juste sur
   la mauvaise release est un chiffre faux.
5. **Chercher les totaux qui ne bouclent pas.** Apparié + non apparié + quarantaine doit valoir le
   total déclaré. Un écart, même de quelques unités, est un fil à tirer.
6. **Vérifier que les absences portent un motif** et ne sont pas devenues des zéros.

## Ce qu'il faut rendre

Un verdict par chiffre : `confirmé`, `diverge` (avec les deux valeurs et la requête utilisée), ou
`invérifiable` (avec ce qui manquait). `invérifiable` est un résultat valide et ne doit pas être
forcé en `confirmé`.

Ne rien corriger. Le recompte constate ; la correction revient au ticket, qui décidera si l'écart
est une erreur de calcul ou une erreur de formulation du rapport.
