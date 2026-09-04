# G9 — Décision documentée : poursuivre / pivoter / arrêter

**Version :** v0.8 · **Taille :** S · **État :** À faire
**Dépend de :** G8 · **Bloque :** clôture du MVP

## Contexte à charger

- `docs/data/mvp-dod-traceability.md`
- `SPEC.md` (§26 uniquement)
- `ARCHITECTURE.md` (§25 uniquement)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Dernier point de la DoD MVP. État actuel : « no-go technique provisoire — décision finale bloquée ».

Ce ticket ne produit pas de logiciel. Il produit une **décision argumentée**, appuyée sur les
mesures accumulées, et l'inscrit dans le dépôt.

## Éléments d'entrée

| Source | Apporte |
|---|---|
| [E4](./E4-backtest-baseline.md) | le score bat-il la baseline ? |
| [E5](./E5-resultats-par-segment.md) | sur quels segments ? |
| [G2](./G2-matrice-acceptation.md), [G4](./G4-couverture-documentee.md) | quelle part du territoire est réellement couverte ? |
| [G8](./G8-pilote-trois-professionnels.md) | H1–H5 : lift, nouveauté, compréhension, temps, intention de payer |
| [G6](./G6-exploitation-restauration.md) | le système est-il exploitable ? |

## Forme de la décision

Trois issues possibles, chacune légitime :

| Issue | Ce qu'elle implique |
|---|---|
| **Poursuivre** | les hypothèses sont validées ; définir le périmètre de la suite et les investissements |
| **Pivoter** | le besoin existe mais la réponse actuelle n'est pas la bonne ; énoncer ce qui change |
| **Arrêter** | les hypothèses ne sont pas validées ; documenter pourquoi, pour que le travail reste réutilisable |

La décision doit énoncer :

1. quelles hypothèses sont validées, lesquelles ne le sont pas, avec les chiffres ;
2. ce qui a été appris et qui n'était pas su au départ ;
3. les limites méthodologiques — trois professionnels ne font pas une étude de marché ;
4. si « poursuivre » : les conditions et le périmètre, pas une intention générale ;
5. si « pivoter » ou « arrêter » : ce qui reste réutilisable et ce qui est abandonné.

## Points de vigilance

- **L'issue « arrêter » doit rester réellement ouverte.** Un dispositif de validation dont l'issue
  est acquise d'avance ne valide rien, et l'effort de rigueur des sections B à G aurait été vain.
- Ne pas confondre « le logiciel fonctionne » et « le produit a de la valeur ». Le premier est
  établi depuis longtemps ; c'est le second qui est en question.
- Une intention de payer déclarée sans prix ni modalité n'est pas une validation commerciale.
- La décision doit être datée et non révisée en place : une décision ultérieure crée une nouvelle
  entrée.

## Critères d'acceptation

- décision publiée, datée, argumentée par les mesures ;
- hypothèses H1 à H5 reprises une par une avec leur verdict ;
- limites méthodologiques énoncées ;
- conditions de la suite explicitées si l'issue est « poursuivre » ;
- DoD MVP `SPEC.md` §26 entièrement tracée dans
  [`mvp-dod-traceability.md`](../data/mvp-dod-traceability.md).

## Preuve à produire

`docs/data/mvp-decision.md`, et mise à jour finale de la traçabilité et de
[`docs/versions/README.md`](../versions/README.md).
