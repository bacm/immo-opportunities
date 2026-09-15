# A1 — Exécuter le workflow CI sur GitHub et attacher la preuve

**Version :** v0.1 · **Taille :** S · **État :** Terminé
**Dépend de :** — · **Bloque :** clôture de v0.1 uniquement (hors chemin critique données)
**Touche :** .github/workflows/, docs/data/ci-proof.md, docs/versions/, pipelines/src/immo_pipelines/spatial/importer.py
**DoD :** test sans objet — le contrôle est le workflow lui-même, exécuté et attaché

## Contexte à charger

- `.github/workflows/ci.yml`
- `Makefile` (cible `check`)
- `docs/versions/v0.1-foundation.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.1 est la seule version dont tous les critères sont satisfaits sauf un :

```text
- [ ] Workflow CI exécuté sur GitHub.
```

Le workflow existe ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) et les contrôles
passent localement, mais aucune exécution GitHub n'est attachée. La traçabilité l'indique
explicitement : « nouveaux tests locaux ; exécution GitHub absente ».

C'est une preuve manquante, pas un développement.

**État du remote au 15 septembre 2026** — le constat d'origine (« le dépôt n'a qu'un seul commit »)
est périmé. `origin/main` est à `615fd98`, le dernier commit de v0.4, et `main` local est **83
commits devant**. Le remote existe, l'accès fonctionne, des pushes ont eu lieu. Ce qui manque n'est
donc pas un dépôt distant : c'est un push, et un run attaché aux preuves.

## Préparation faite le 15 septembre 2026

Trois correctifs pour qu'un premier run soit une preuve valide, et non un échec ou un vert trompeur.

1. **Le contrôle d'invariants tourne désormais sur `push` autant que sur `pull_request`.** Il était
   conditionné aux pull requests : un run vert sur `main` aurait couvert *moins* que `make check`,
   ce que les critères ci-dessous interdisent. Base repliée sur `HEAD^` quand `github.event.before`
   est nul — branche neuve ou force-push.
2. **Une ligne justifiée sur place.** `coalesce(ranked.cover_ratio, 0)` dans
   `pipelines/src/immo_pipelines/spatial/importer.py` aurait fait échouer ce premier run. En
   contexte, c'est le correctif de [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md), pas sa
   rechute : le `CASE` qui suit traite `NULL` et `0` comme `ambiguous`, avec un motif distinct pour
   chacun. Le zéro y est qualifié, jamais présenté comme un recouvrement observé — d'où un
   `invariant-ok:` sur la ligne plutôt qu'une correction.
3. **`uv` épinglé sur la version qui a produit `uv.lock`** — 0.9.16, au lieu de 0.10.6. Un `uv`
   plus récent peut vouloir bumper la révision du lock, et `uv sync --locked` échoue alors sur un
   dépôt sain. La commande exacte de la CI a été rejouée en local : elle passe.

Vérifié aussi, hors ligne : `uv lock --check` passe, `pnpm@10.33.0` correspond au `packageManager`
de `package.json`, `.env.example` est présent pour `make config`, et `scripts/tests` ne dépend ni de
git ni d'une base — les tests passent sur un clone neuf.

**Deux inconnues ne se lèvent qu'en s'exécutant** : les versions d'actions (`setup-python@v6`,
`setup-uv@v7`, `setup-node@v6`, `pnpm/action-setup@v4`), et le comportement réel de
`uv sync --locked` sur le runner. Si l'une casse, corriger le workflow — sans retirer `--locked` ni
désactiver un contrôle.

## Résultat — 15 septembre 2026

85 commits poussés sur `main`. Le workflow s'est déclenché et **a réussi** :
run [`34928242516`](https://github.com/bacm/immo-opportunities/actions/runs/34928242516), 48 s,
toutes étapes vertes, `Check diff invariants` comprise.

Preuve complète, correspondance cible par cible avec `make check` et limites du run dans
[`docs/data/ci-proof.md`](../data/ci-proof.md). v0.1 est passée à `Terminée`.

**Le diagnostic d'origine était faux deux fois.** Le dépôt n'avait pas « un seul commit » : le
remote était à jour jusqu'au 8 septembre, et le workflow comptait déjà **trois runs verts** — 4 et
8 septembre, puis celui-ci. Ce qui manquait n'était pas l'exécution mais son **rattachement aux
preuves de v0.1**, ce que le titre du ticket disait et que son contexte avait perdu de vue. Le run
du 15 septembre est retenu parce qu'il est le premier à couvrir l'intégralité de `make check`.

Reste ouvert, hors périmètre : `deploy-vps.yml` échoue à chaque push faute de variables `VPS_*`
([G6](./G6-exploitation-restauration.md)). Un workflow rouge en permanence masquera le jour où il
rougit pour une vraie raison.

## Travail à réaliser

1. ~~Vérifier que le dépôt distant existe et que GitHub Actions y est activé.~~ fait
2. ~~Déclencher le workflow sur `main` ou sur une pull request.~~ fait
3. Vérifier que les jobs couvrent bien : lint, typecheck, tests backend, tests pipelines, build
   frontend, et validation du contrat OpenAPI.
4. Si un job échoue pour une raison d'environnement CI et non de code, corriger le workflow — sans
   désactiver de contrôle pour faire passer la CI.
5. Attacher l'URL du run et son résultat dans les preuves de v0.1.

## Points de vigilance

- Un job vert obtenu en réduisant le périmètre des tests n'est pas une preuve. Comparer la liste
  des contrôles exécutés en CI à celle de `make check`.
- Les secrets nécessaires ne doivent pas apparaître en clair ; si la CI a besoin d'un service
  PostgreSQL/PostGIS, il doit être fourni par un service container, pas par un secret externe.
- Le workflow [`deploy-vps.yml`](../../.github/workflows/deploy-vps.yml) n'est pas concerné par ce
  ticket : son exécution réelle relève de [G6](./G6-exploitation-restauration.md).

## Critères d'acceptation

- au moins un run GitHub complet et vert sur `main` ou sur une PR mergée ;
- les contrôles exécutés en CI sont au moins ceux de `make check` ;
- l'URL du run figure dans les preuves de livraison de v0.1 ;
- la ligne « Parcours critiques en CI » de la traçabilité passe de partiel à validé.

## Preuves à produire

- lien du run dans [`docs/versions/v0.1-foundation.md`](../versions/v0.1-foundation.md) ;
- mise à jour de la ligne correspondante dans
  [`docs/data/mvp-dod-traceability.md`](../data/mvp-dod-traceability.md) ;
- passage de v0.1 à `Terminée` dans [`docs/versions/README.md`](../versions/README.md).
