# BUG-07 — L'Explorer ne montre rien : carte vide et recherche d'adresse en erreur

**Version :** v0.4 · **Taille :** M · **État :** Terminé
**Dépend de :** — · **Bloque :** C1, C2, C3, toute démonstration du produit
**Découvert par :** vérification manuelle du parcours utilisateur, 8 septembre 2026

## Contexte à charger

- `pipelines/src/immo_pipelines/cadastre/catalog.py` (`publish`)
- `backend/migrations/versions/20260805_0008_real_map.py` (`tiles.refresh_render_v1`)
- `backend/src/immo/spatial.py` (`search_addresses`)
- `backend/src/immo/connected_mvp.py` (`list_match_metrics`)

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

Trois semaines de travail sur les données, et personne n'avait ouvert l'application. Deux défauts
la rendent inutilisable, tous deux **silencieux** :

1. **La carte est vide.** Martin répond `204 No Content` sur les trois couches, à tous les zooms
   supportés. Aucune erreur, aucun log : une tuile vide est une réponse valide.
2. **La recherche d'adresse renvoie 503.** `GET /api/v1/spatial/addresses?query=...` échoue dès
   que `commune_code` n'est pas fourni — c'est-à-dire dans le cas d'usage principal.

## Cause 1 — les tables de rendu n'ont jamais été peuplées

`tiles.parcel_render_v1` et `tiles.building_render_v1` contenaient **zéro ligne** pour
1 333 327 parcelles et 741 379 bâtiments en base.

La fonction `tiles.refresh_render_v1(department)` existe et fonctionne. Mais son seul appelant
était la migration `20260805_0008_real_map`, qui boucle sur les départements **déjà publiés au
moment où elle s'exécute**. DS-01 ayant été publié après, la boucle n'a rien trouvé et rien
calculé.

**C'est exactement le défaut de [BUG-04](./BUG-04-propagation-referentiel-spatial.md)**, sur un
autre objet : une propagation qui appartient à la publication, mais qui dépend d'un appel
extérieur. BUG-04 avait corrigé la propagation du référentiel canonique et laissé celle du rendu.

## Cause 2 — un paramètre optionnel sans `CAST`

```text
psycopg.errors.AmbiguousParameter: could not determine data type of parameter $2
```

`(:commune_code IS NULL OR commune_code = :commune_code)` : PostgreSQL ne peut pas déduire le type
d'un paramètre qui n'apparaît que comparé à `NULL` et à une colonne. Le motif correct — un `CAST`
explicite — existait déjà dans `scoring.py`, mais deux requêtes l'omettaient : la recherche
d'adresse, et l'endpoint `admin/match-metrics` écrit la veille en [B3](./B3-rapport-appariements.md).

Le `try/except SQLAlchemyError` de la route traduisait cette erreur de programmation en
« Spatial reference is unavailable », ce qui désigne une panne d'infrastructure. Le vrai motif
n'apparaissait nulle part.

## Travail réalisé

1. `catalog.publish()` rafraîchit les tables de rendu **dans la même transaction** que le
   déplacement du pointeur, et rapporte leurs volumes.
2. `CAST` explicite sur les deux requêtes fautives.
3. Vérifié de bout en bout : tables de rendu vidées, puis republication de `DS-01@2026-06-01` —
   1 333 327 parcelles et 865 335 bâtiments recalculés, sans aucune intervention manuelle.

```json
"spatial_reference": {"area_count": 332, "parcel_count": 1333327,
                      "property_unit_count": 1333327,
                      "render_parcel_count": 1333327, "render_building_count": 865335}
```

4. Tuiles vérifiées sur Rennes : 858 Ko de parcelles à z13, 148 Ko de bâtiments à z15, via le
   point d'entrée réel `http://localhost:8080/tiles/v1/...`.
5. Recherche d'adresse vérifiée : `query=rue de la monnaie` sans filtre rend 10 résultats
   pertinents, et la fiche d'adresse expose sa relation parcelle.

## Preuves

| Test | Fichier |
|---|---|
| Publier DS-01 rafraîchit le rendu, dans la transaction | `pipelines/tests/test_release_acceptance_gate.py` |
| Publier une release non cadastrale ne le fait pas | idem |
| Aucun paramètre optionnel comparé à NULL sans `CAST`, sur les quatre modules | `backend/tests/test_optional_sql_parameters.py` |

Le contrôle des paramètres optionnels est **générique** : il balaie `spatial.py`,
`connected_mvp.py`, `scoring.py` et `market_data.py`, donc il attrapera la prochaine occurrence
plutôt que de constater celles-ci.

## Tests obligatoires

- publier une release DS-01 peuple `tiles.parcel_render_v1` et `tiles.building_render_v1` ;
- `search_addresses` sans `commune_code` ne lève pas ;
- `list_match_metrics` sans filtre ne lève pas ;
- une tuile au zoom supporté, sur une zone dense, revient non vide.

## Critères d'acceptation

- ✅ l'Explorer affiche des parcelles et des bâtiments sur le 35 ;
- ✅ la recherche d'adresse fonctionne sans filtre de commune ;
- ✅ aucune propagation ne dépend plus d'un appel extérieur à la publication.

## Ce qui n'a pas été fait

Le point 6 du plan initial — ne plus traduire une erreur de programmation en 503 — n'est pas
traité. `spatial.py` attrape `SQLAlchemyError`, qui couvre aussi bien une panne de connexion
qu'une requête malformée, et les deux méritent des réponses différentes. Le corriger demande de
décider quelles erreurs sont des indisponibilités et lesquelles doivent remonter en 500 : c'est un
choix d'API, pas une correction mécanique, et il dépasse ce bug.

**Le front n'a pas été vérifié dans un navigateur.** Les tuiles arrivent et l'API répond, mais
personne n'a vu la carte s'afficher. C'est ce que [C3](./C3-capture-demo-adresse.md) exige, et il
reste à faire.

## Ce que ce bug dit du processus

Les deux défauts étaient invisibles depuis les tests et depuis `make check`. Le premier parce
qu'une tuile vide est une réponse valide ; le second parce qu'aucun test n'appelait la recherche
sans `commune_code`. La leçon est dans [C3](./C3-capture-demo-adresse.md), qui exige une capture
de démonstration : elle aurait attrapé les deux.
