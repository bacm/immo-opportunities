# A4 — Les décisions sortent d'ARCHITECTURE.md, qui reste un document de référence

**Version :** transverse · **Taille :** S · **État :** À faire
**Nature :** implémentation
**Touche :** ARCHITECTURE.md, docs/decisions/, scripts/check-doc-budget, scripts/tests/, Makefile, CLAUDE.md
**Dépend de :** — · **Bloque :** —
**DoD :** preuve sans objet — la sortie du ticket est `docs/decisions/` lui-même, hors `docs/data/`
**Demandé par :** conversation du 15 septembre 2026

## Contexte à charger

- `ARCHITECTURE.md` §22 et §23 seulement
- `scripts/check-diff-invariants` (modèle de contrôle et d'échappatoire)
- `Makefile`, cible `check`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

`ARCHITECTURE.md` fait **1 278 lignes**. `CLAUDE.md` l'annonce déjà comme trop lourd pour être
chargé par défaut, et demande de n'en lire que la section concernée.

Deux sections y portent les décisions, dans un format tabulaire qui coûte **une ligne par
décision** :

| Section | Lignes | Contenu |
|---|---|---|
| §22 Choix écartés | 21 | 14 alternatives, chacune avec son motif |
| §23 Décisions ADR | 72 | 15 décisions acceptées **+ la note ADR-015** |

La note `ADR-015`, ajoutée le 15 septembre 2026, fait **50 lignes** — 70 % de §23 pour une
décision sur quinze. C'est le format que §23 réclame lui-même de toute révision d'une décision
acceptée : « une note ADR datée indiquant le contexte, les alternatives, la décision et les
conséquences ».

Les deux exigences sont incompatibles là où elles sont posées. Quinze notes de cette longueur
ajouteraient **750 lignes, +59 %**, et le document cesserait d'être consultable.

## Le partage à faire est par durée de vie, pas par sujet

- `ARCHITECTURE.md` décrit **ce qui est vrai maintenant**. Il se lit en entier, sa taille est
  bornée, et le motif d'une décision y tient dans une cellule de tableau.
- `docs/decisions/` porte **le pourquoi, daté, et contre quoi**. Un fichier par décision, jamais
  lu en entier, consulté quand on rouvre une décision. Il croît sans contrainte puisque personne
  ne le charge.

`ARCHITECTURE.md` cesse alors de croître avec l'historique : il ne croît plus qu'avec le système.

## Périmètre

1. Créer `docs/decisions/` et y déplacer la note `ADR-015` — `ADR-015-boucle-autonome.md`, telle
   quelle, sans réécriture. `ARCHITECTURE.md` repasse à **1 228 lignes**, §23 à 22.
2. Ajouter une colonne `Note` au tableau §23 : le lien vers le fichier quand il existe, `—` sinon.
   Coût constant, aucune ligne ajoutée.
3. Écrire la règle dans §23, sous le tableau : le motif d'une décision tient dans une cellule ;
   au-delà, il va dans `docs/decisions/`. Ce qui manque alors à §22 et §23 se réduit à deux
   champs — la **date** d'une décision, et le **lien entre un choix écarté et l'ADR auquel il se
   rattache**. Pas le raisonnement, qui est déjà là.
4. `scripts/check-doc-budget` — `make check` échoue si `ARCHITECTURE.md` dépasse un plafond
   déclaré. Même échappatoire explicite que `check-diff-invariants` : relever le plafond est un
   geste visible dans le diff, pas un dépassement silencieux.
5. `CLAUDE.md`, carte du contexte : la ligne « Choix technique, ADR, interdits » pointe désormais
   sur `docs/decisions/` pour le pourquoi, `ARCHITECTURE.md` pour l'état courant.

## Le plafond

Proposition : **1 300 lignes**, soit 72 de marge sur les 1 228 attendues après le point 1.

Ce n'est pas un seuil observé, c'est un budget déclaré — la marge doit suffire à une section
nouvelle sans être assez large pour absorber une note ADR. Si le plafond est atteint, la question
posée est « qu'est-ce qui, dans ce document, décrit l'historique plutôt que l'état courant », et
non « de combien le relever ».

## Critères d'acceptation

- `ARCHITECTURE.md` ne contient plus aucune note ADR en prose ; §23 est un tableau et une règle ;
- la note `ADR-015` est intégralement retrouvable dans `docs/decisions/`, contenu inchangé ;
- `make check` échoue si `ARCHITECTURE.md` franchit le plafond, et le dit avec le nombre de lignes
  constaté ;
- le script est couvert par un test exécuté par `make check`.

## Ce qui n'est pas dans le périmètre

- **Rétro-remplir ADR-001 à ADR-014.** Reconstituer aujourd'hui le contexte et les conséquences de
  choix faits il y a six mois produirait une justification fabriquée après coup, présentée comme
  une trace. C'est le mode d'échec que décrit ADR-015 lui-même. Les motifs existent déjà en §22 ;
  ce qui manque est la date, et elle n'est pas reconstituable honnêtement.
- **§10 Pipelines, 189 lignes, la section la plus lourde du document.** Elle mêle la règle et son
  raisonnement, et relève du même traitement. C'est un arbitrage distinct, à ouvrir séparément si
  le plafond devient contraignant.
- L'obligation d'ouvrir un ticket pour toute demande touchant code, schéma, infra ou comportement.
  Manque réel, constaté dans la même conversation, mais indépendant de celui-ci.
