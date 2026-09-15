# A5 — Toute modification du code passe par un ticket

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation
**Touche :** CLAUDE.md, scripts/check-commit-ticket, scripts/tests/, Makefile, .github/workflows/ci.yml
**Dépend de :** — · **Bloque :** —
**DoD :** preuve sans objet — outillage : la preuve est la suite `scripts/tests/`
**Demandé par :** conversation du 15 septembre 2026

## Contexte à charger

- `scripts/check-diff-invariants` (forme du contrôle, résolution de la base, échappatoire)
- `scripts/check-ticket-dod`, fonction `subject_matches` (la convention à faire respecter)
- `.github/workflows/ci.yml`, étape « Check diff invariants »

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

`CLAUDE.md` décrit comment **implémenter un ticket**, comment le clore, comment ses chemins sont
réservés. Il ne dit nulle part qu'une modification doit en avoir un. Une demande directe — « ajoute
une barre de progression », « ce fond de carte masque les géométries » — n'a donc aucune porte
d'entrée : elle est implémentée et committée, et les choix qu'elle contient n'existent que dans le
message de commit.

Ce n'est pas théorique. **Onze commits sur cent deux** ont modifié autre chose que `docs/` sans
porter d'identifiant de ticket, dont :

| Commit | Ce qu'il a changé |
|---|---|
| `ca5f418` | 6 fichiers, dont l'annonce d'avancement de quatre scripts de lot |
| `ad581e2`, `10b02a3` | ordre des couches et fond de carte de l'Explorer, plus un test |
| `849c05c` | `scripts/backlog-status` |
| `30f7af7` | 24 fichiers : les trois sources spatiales du 35 |

Les cinq autres sont l'amorçage du dépôt, un reformatage `ruff`, et des retouches de `CLAUDE.md` et
`ARCHITECTURE.md`.

Trois conséquences, dans l'ordre de gravité :

1. **La décision n'est retrouvable que par qui sait déjà où chercher.** `ca5f418` porte un
   raisonnement de vingt lignes dans son message de commit — le total annoncé est celui du travail
   restant et non du catalogue, l'écart entre estimation et réel est lui-même une information. Rien
   n'y renvoie depuis le backlog ni depuis `ARCHITECTURE.md`.
2. **Le changement échappe à la DoD.** `check-ticket-dod` reconstitue le diff d'un ticket depuis le
   sujet des commits qui portent son identifiant. Un commit sans identifiant n'est pas *signalé*,
   il est **invisible** : aucun des sept points ne s'applique à lui.
3. **Il n'occupe aucun chemin.** `**Touche :**` est ce qui empêche deux travaux parallèles d'écrire
   au même endroit. Un changement hors ticket ne réserve rien.

## Périmètre

1. **La règle, dans `CLAUDE.md`.** Une demande touchant le code, un schéma, l'infrastructure ou le
   comportement de l'application s'ouvre en ticket avant la première ligne modifiée. Le ticket peut
   être minimal ; ce qu'il doit porter, c'est la demande et les choix retenus.
2. **`scripts/check-commit-ticket`.** Pour chaque commit d'une plage, si le commit touche autre
   chose que `docs/`, son sujet porte au moins un identifiant existant dans `docs/backlog/`, selon
   la convention que `check-ticket-dod` utilise déjà — l'identifiant avant le tiret cadratin,
   `D5 — …`, `D1, D6a — …`. Échappatoire explicite `ticket-ok: <raison>` dans le corps du message.
3. **`make ticket-check`**, et un test ancré qui applique la règle à l'historique réel depuis
   `96f12f4`, le commit qui précède son écriture.

## Pourquoi `docs/` seul est dispensé

Le backlog, les preuves, les versions et les décisions sont la **sortie** du processus, pas son
objet. Ouvrir un ticket ne peut pas demander un ticket, sous peine de récursion.

Tout le reste en demande un, y compris `SPEC.md`, `ARCHITECTURE.md` et `CLAUDE.md` : ce sont les
sources de vérité, et les modifier est précisément ce qu'on veut voir passer par une décision
écrite. Une correction de typographie s'en sort par `ticket-ok:`, une ligne visible dans le diff.

## Pourquoi le critère porte sur les chemins, et non sur la nature du changement

La variante souple — « ticket obligatoire dès que le changement touche un comportement observable,
les corrections purement internes restent au commit » — a été écartée. Elle demande à l'agent qui
produit le changement de juger, en cours de route et sous pression d'achèvement, si son changement
est « purement interne ». C'est exactement le mode d'échec que nomme
[ADR-015](../decisions/ADR-015-boucle-autonome.md) : un verrou ne peut pas être une appréciation
portée par celui qu'il verrouille. Le critère doit être topologique. Les chemins touchés le sont ;
la nature du changement ne l'est pas.

## Pas d'étape CI dédiée, contrairement aux invariants

`check-diff-invariants` a la sienne parce que `make check` lit le **travail en cours** : sur l'arbre
propre d'un runner, il n'a rien à lire, et le contrôle doit être relancé sur le diff poussé.

Ce contrôle-ci n'a pas ce défaut : il lit une plage de commits, pas l'arbre. Le test ancré
`test_l_historique_depuis_la_regle_est_rattache` juge donc la même chose en CI qu'en local, et il
la juge sur une plage plus large que celle d'une pull request — tout l'historique depuis la règle.
Une étape séparée n'ajouterait rien. Le test refuse en revanche de passer s'il n'a lu aucun commit :
un clone superficiel produirait sinon un vert qui n'a rien contrôlé.

## Critères d'acceptation

- un commit touchant hors `docs/` sans identifiant connu fait échouer `make ticket-check` ;
- l'échappatoire `ticket-ok:` est reconnue, et seulement dans le corps du message ;
- un identifiant syntaxiquement valide mais absent de `docs/backlog/` est refusé — sans quoi
  `X9 — …` suffirait à passer ;
- le contrôle tourne en CI sur `push` comme sur `pull_request` ;
- le script est couvert par des tests exécutés par `make check`.

## Ce qui n'est pas dans le périmètre

- **Régulariser les onze commits de l'historique.** Le contrôle juge une plage ; en CI, cette plage
  est le travail poussé. L'historique n'est pas rejugé, et lui inventer des tickets a posteriori
  produirait des tickets vides.
- **Contrôler le travail en cours plutôt que les commits.** Faire échouer `make check` quand
  l'arbre de travail touche du code sans qu'aucun ticket ne soit `En cours` attraperait la faute
  plus tôt, mais signalerait aussi toute exploration. Un contrôle bruyant est un contrôle
  désactivé ; celui-ci porte là où le geste est définitif.
- **Le contenu du ticket.** Qu'il porte réellement les choix retenus n'est pas mécanisable. C'est
  la règle de `CLAUDE.md` qui le demande, pas le script qui le vérifie.

## Résultat

`scripts/check-commit-ticket`, 64 tests verts dans `scripts/tests` dont 9 nouveaux.

Calibration sur l'historique — `--base ac0a57a`, soit tout le dépôt sauf son premier commit :

| | |
|---|---|
| Commits contrôlés | tout le dépôt sauf son premier commit |
| Signalés | **10** |
| dont code applicatif | `ca5f418` (6 chemins), `ad581e2`, `10b02a3` |
| dont outillage et sources de vérité | `849c05c`, `4669f0f`, `b96db5b`, `b5e8d2b`, `30f7af7` |
| dont amorçage et reformatage | `7f1687a`, `ee5c498` |

Ces dix ne sont pas régularisés : le test est ancré sur `96f12f4`, et ne juge que ce qui vient
après. Les citer ici suffit à ce que le chiffre ne soit pas perdu.

Sur la plage écrite depuis : rien à signaler.
