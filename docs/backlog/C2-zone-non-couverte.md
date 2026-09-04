# C2 — Distinguer zone non couverte et zone sans résultat

**Version :** v0.4 · **Taille :** S · **État :** À faire
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
