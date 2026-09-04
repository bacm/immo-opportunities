# G2 — Matrice d'acceptation par territoire

**Version :** v0.8 · **Taille :** M · **État :** À faire
**Dépend de :** G1 · **Bloque :** G4, G5

## Contexte à charger

- `docs/data/brittany-acceptance-matrix.md`
- `pipelines/src/immo_pipelines/cadastre/catalog.py`
- `backend/src/immo/api/routes/meta.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Le fichier [`brittany-acceptance-matrix.md`](../data/brittany-acceptance-matrix.md) existe déjà,
mais sans données réelles à décrire. Ce ticket le remplit et lui donne un effet technique.

**Règle centrale :** aucun département n'est « couvert » sans ses données critiques.

## Contenu attendu

Une ligne par couple dataset × département, avec :

| Colonne | Contenu |
|---|---|
| Dataset | DS-01 à DS-09 |
| Département | 22, 29, 35, 56 |
| Release | identifiant exact, jamais un alias |
| Checksum | SHA-256 de l'archive |
| Verdict | `accepted`, `rejected`, `display_only`, ou absent |
| Date d'audit | |
| Couverture | part des unités renseignées |
| Fraîcheur | date de la donnée la plus récente |
| Conséquence | features activées ou désactivées par ce verdict |

Puis une synthèse par département : **publiable** / **partiellement publiable** / **non publiable**,
avec la liste des sources manquantes pour les deux derniers cas.

## Effet technique attendu

La matrice ne doit pas être un document tenu à la main. Elle doit être **générée** depuis l'état
réel du catalogue (`meta.dataset_release`), sinon elle divergera dès la première release suivante.

Un département déclaré non publiable doit l'être aussi dans le produit : aucun score publié, et un
état « territoire non couvert » côté carte, cohérent avec [C2](./C2-zone-non-couverte.md).

## Critères d'acceptation

- matrice générée automatiquement depuis le catalogue ;
- verdict explicite pour chaque couple dataset × département ;
- synthèse par département avec sources manquantes nommées ;
- cohérence vérifiée entre la matrice et ce que le produit publie réellement ;
- aucun département déclaré couvert sans données critiques.

## Preuve à produire

[`brittany-acceptance-matrix.md`](../data/brittany-acceptance-matrix.md) régénérée, avec la commande
de régénération référencée.
