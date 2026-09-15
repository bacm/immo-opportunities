# BUG-15 — Deux fichiers pour un identifiant : un ticket disparaît du tableau sans bruit

**Version :** dette transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation
**Touche :** scripts/backlog-status, scripts/tests/test_backlog_status.py
**DoD :** preuve sans objet — la preuve est le test et le décompte du tableau, pas un rapport de `docs/data/`
**Dépend de :** — · **Bloque :** —
**Constaté le :** 15 septembre 2026

## Contexte à charger

- `scripts/backlog-status` (fonctions `load` et `check_integrity`)
- `scripts/tests/test_backlog_status.py`

Ne rien charger d'autre sans nécessité démontrée.

## Le défaut

`load()` indexe les tickets dans un dictionnaire dont la clé est l'identifiant dérivé du nom de
fichier. Deux fichiers portant le même identifiant ne produisent donc qu'une entrée : la seconde
écrase la première, dans l'ordre alphabétique des noms de fichiers, **sans aucun signalement**.

C'est arrivé le 15 septembre 2026. Deux sessions travaillant en parallèle ont créé chacune un
ticket `A4` — `A4-decisions-hors-architecture.md` et `A4-demo-sous-ensemble-vps.md`. Le tableau
généré annonçait **57 tickets pour 58 fichiers** ; le premier n'y figurait plus du tout, alors qu'il
était `Terminé` et committé. Après renommage en `A6`, 58.

Le tableau étant la seule vue d'ensemble du backlog, un ticket qui en sort n'existe plus pour
personne : ni dans les tickets prêts, ni dans les lots menables de front, ni dans le décompte des
terminés — qui devient faux, comme le comptage de [BUG-12](./BUG-12-deduplication-batiments-physiques.md).

## Pourquoi c'est la mauvaise défaillance

L'outil a rendu un tableau **plausible et faux** plutôt qu'une erreur. C'est exactement ce que la
troisième règle d'[ADR-015](../../ARCHITECTURE.md#23-décisions-adr) refuse : une perte silencieuse
là où un échec bruyant était disponible pour trois lignes.

La collision n'est pas un cas de figure théorique. La parallélisation est une pratique établie de ce
dépôt — `make backlog` en dérive les lots menables de front —, et rien dans la procédure d'ouverture
d'un ticket ne dit à un agent quel identifiant est déjà pris par un fichier que l'autre session n'a
pas encore committé.

## Correctif

`check_integrity` signale les identifiants portés par plus d'un fichier. Le contrôle vit là parce
que `make backlog` et `make backlog-check` y passent tous les deux : la régénération échoue, et la
CI documentaire aussi.

Le contrôle porte sur les **fichiers présents sur disque**, non sur le dictionnaire déjà chargé —
au moment où l'on tient ce dictionnaire, l'information est précisément ce qui a été perdu.

## Critères d'acceptation

- deux fichiers de même identifiant font échouer `scripts/backlog-status` avec les deux noms de
  fichiers dans le message ;
- le décompte des tickets du tableau est égal au nombre de fichiers de tickets ;
- un test couvre le cas ;
- `make check` vert.

## Hors périmètre

Attribuer automatiquement un identifiant libre à l'ouverture d'un ticket. Ce serait confortable,
mais la course entre deux sessions se déplacerait simplement de la collision de fichiers à la
collision d'attribution. Un échec explicite au moment de régénérer suffit à ce que personne ne
travaille sur un tableau faux.

## Résultat — 15 septembre 2026

`duplicate_ids()` ajouté en tête de `check_integrity`. Éprouvé de bout en bout en dupliquant un
fichier de ticket :

```text
Backlog incohérent :
  - BUG-15 : 2 fichiers portent cet identifiant — BUG-15-collision-identifiants-tickets.md,
    BUG-15-doublon-de-test.md
```

Après retrait du doublon : 59 tickets régénérés pour 59 fichiers de tickets. Deux tests couvrent le
cas, dont un qui vérifie que le backlog réel n'a pas de doublon.
