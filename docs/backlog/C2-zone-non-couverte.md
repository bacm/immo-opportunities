# C2 — Distinguer zone non couverte et zone sans résultat

**Version :** v0.4 · **Taille :** S · **État :** Terminé
**Dépend de :** C1 · **Bloque :** C3

## Contexte à charger

- `apps/web/src/RealMap.tsx`
- `backend/src/immo/api/routes/explorer.py`
- `backend/src/immo/explorer.py`
- `docs/data/real-map-performance.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

v0.4 déclare avoir implémenté les états obligatoires : « chargement, vide, hors couverture, données
partielles et erreur récupérable ». Ce ticket ne les réimplémente pas — il vérifie qu'ils
**distinguent réellement** deux situations que l'utilisateur ne doit jamais confondre :

| Situation | Sens pour l'utilisateur | Message attendu |
|---|---|---|
| Zone non couverte | aucune donnée importée ici — l'absence de candidat ne veut rien dire | « territoire non couvert » |
| Zone couverte sans résultat | données présentes, aucun bien ne correspond aux critères | « aucun résultat pour ces filtres » |
| Zone couverte partiellement | certaines sources manquent — le classement est incomplet | « données partielles » + sources manquantes |

Confondre les deux premiers cas est une erreur produit grave : elle laisse croire à un marchand de
biens qu'un territoire est vide alors qu'il n'a simplement jamais été importé.

## Enjeu spécifique au 35

Au moment de la rédaction, la couverture est hétérogène **à l'intérieur même du 35** : cadastre sur
332 communes, RNB sur 332, BAN en attente, BDNB et BD TOPO absentes. La distinction ne se joue donc
pas seulement au niveau départemental mais au niveau de la commune et de la **source**.

## Travail à réaliser

1. Exposer la couverture par territoire et par source via l'API, en s'appuyant sur les métriques
   déjà persistées par commune.
2. Afficher l'état correspondant sur la carte et dans la liste, de façon synchronisée (FR-003).
3. Nommer les sources manquantes dans l'état « données partielles » — pas un avertissement générique.
4. Signaler visuellement sur la carte les zones non couvertes, sans les rendre indiscernables des
   zones vides.

## Résultat au 8 septembre 2026

Le ticket disait « ce ticket ne les réimplémente pas — il vérifie qu'ils distinguent réellement ».
La vérification a montré qu'il n'y avait rien à vérifier : **le front ne consommait aucun état de
couverture**. `ViewportResponse` porte bien `coverage` et `partial`, mais `loadViewport` est
exporté dans `api.ts` et **jamais appelé**. Les états déclarés par v0.4 existaient dans le
contrat, pas à l'écran.

Second constat : `partial` ne voulait pas dire ce que ce ticket entend par « données partielles ».
Il vaut `len(rows) > limit`, c'est-à-dire **résultats tronqués** — rien à voir avec des sources
manquantes. Deux sens différents sur le même mot.

### Ce qui est livré

`GET /api/v1/spatial/coverage?commune_code=` rend la couverture d'une commune **source par
source**, construite sur ce qui est déjà persisté : `meta.active_dataset_release` pour le pointeur
actif, `meta.entity_match_metric` pour les volumes par commune.

Une source est couvrante si elle a une release **active** sur le département **et** au moins une
observation dans la commune. Les deux comptent : un pointeur sans donnée locale ne couvre pas, et
des données sans pointeur actif ne sont pas lisibles par l'API.

| État | Sens | Rendu |
|---|---|---|
| `covered` | les cinq sources spatiales actives | « territoire couvert » |
| `partial` | certaines seulement | « données partielles » + **sources nommées** |
| `not_covered` | aucune | « territoire non couvert » |

`CoverageBanner` est placé **au-dessus** de la grille : la carte et la liste le partagent, donc
leur état est synchronisé par construction et non par deux rendus à garder d'accord (FR-003).

### Ce que la mesure réelle révèle

Les trois communes testées — Rennes, Saint-Malo, Acigné — sont toutes en `partial`, et la source
nommée manquante est la même : **DS-02, le RNB**. Il est importé, 741 379 bâtiments en base, mais
sa release est `pending` et n'a donc jamais été publiée : aucun pointeur actif, donc invisible de
l'API. C'est exactement le genre d'écart qu'un avertissement générique aurait masqué.

Il se résoudra à la clôture de [B4](./B4-revue-manuelle-appariements.md).

### Ce qui n'est pas démontrable aujourd'hui

**L'état `not_covered` est inatteignable sur données réelles.** `reference.area` ne contient que
les 332 communes du 35 : une commune du 22 renvoie 404, pas « non couvert ». L'état est implémenté
et couvert par un test end-to-end, mais il ne se vérifiera en conditions réelles qu'à
[G1](./G1-extension-22-29-56.md), quand des communes seront chargées sans que leurs sources le
soient.

C'est une limite honnête : le cas le plus dangereux du ticket — laisser croire qu'un territoire
est vide — est celui qu'aucune donnée actuelle ne permet de provoquer.

### L'enjeu du 35 a changé depuis la rédaction

Le ticket décrivait « BAN en attente, BDNB et BD TOPO absentes ». Les cinq sources spatiales sont
désormais importées sur les 332 communes ; seul le pointeur DS-02 manque. La distinction reste
nécessaire, mais son motif s'est déplacé de l'import vers la publication.

## Tests obligatoires

- une commune sans donnée importée affiche « non couvert », jamais « aucun résultat » ;
- une commune couverte sans candidat correspondant affiche « aucun résultat » ;
- une commune dont une source est manquante affiche « données partielles » et nomme la source ;
- l'état est identique entre la carte et la liste ;
- l'état survit au partage d'URL.

## Critères d'acceptation

- les trois états sont distincts, testés et visibles ;
- aucune zone non couverte n'est présentée comme vide ;
- les sources manquantes sont nommées.

## Preuve à produire

Tests end-to-end et capture des trois états dans [C3](./C3-capture-demo-adresse.md).
