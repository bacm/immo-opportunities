# E2 — Passer les deux définitions en `publication_eligible`

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Dépend de :** E1 · **Bloque :** E3

## Contexte à charger

- `contracts/scoring/division-extension-v1.json`
- `contracts/scoring/renovation-resale-v1.json`
- `pipelines/src/immo_pipelines/scoring/engine.py`
- `pipelines/tests/test_scoring_engine.py`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

`division-extension-v0.1` et `renovation-resale-v0.1` portent `publication_eligible: false`. Ce
drapeau n'est pas une formalité administrative : il empêche la publication d'un score dont les
paramètres ne sont pas fondés sur des données réelles.

**Ce ticket ne réécrit pas le moteur.** Il vérifie que les conditions du passage sont réunies et,
si elles le sont, bascule le drapeau. Si le profiling ne les justifie pas, la bonne conclusion est
de ne pas basculer et de le documenter.

## Conditions de bascule

Chaque condition doit être vérifiée par un contrôle automatisé, pas par un jugement :

| # | Condition | Vérification |
|---|---|---|
| 1 | Toutes les sources dont dépendent les features `required` sont `accepted` | contrôle sur `meta.dataset_release` |
| 2 | Chaque transformation et chaque seuil est issu du profiling de E1 | contrôle de contrat |
| 3 | Aucune feature interdite n'entre dans le score | registre `scoring-features-v1` |
| 4 | Chaque valeur contribue au plus une fois | vérification de double comptage de E1 |
| 5 | La couverture réelle permet d'évaluer une part significative des unités | mesure publiée |
| 6 | Les revues manuelles B4 et D6 n'ont pas conclu à une limite rédhibitoire | rapports |

## Travail à réaliser

1. Implémenter les contrôles de bascule comme des tests, pas comme une checklist documentaire.
2. Vérifier que le drapeau a un **effet technique réel** : une définition non éligible ne doit
   produire aucun snapshot publiable, et ce comportement doit être testé.
3. Publier une nouvelle version de chaque définition — `v0.2` — plutôt que de modifier `v0.1`.
   Les définitions sont versionnées ; on ne réécrit pas une version existante.
4. Documenter, pour chaque définition, le périmètre sur lequel elle est éligible : si seule une
   partie des communes du 35 satisfait les conditions, l'éligibilité est restreinte à ce périmètre
   et le reste est explicitement non publiable.

## Points de vigilance

- L'éligibilité peut être **partielle**. Il est légitime de publier `division-extension` et pas
  `renovation-resale` si seule la première satisfait ses conditions. Forcer les deux ensemble
  serait un choix de confort.
- Une bascule sans restriction de périmètre alors que la couverture est hétérogène produirait des
  scores sur des unités mal renseignées — exactement le risque déclaré « publier des candidats à
  faible qualité de résolution ».
- **Risque déclaré :** confondre rang synthétique et probabilité. Le score classe des actifs à
  approfondir ; il ne prédit pas une vente.

## Tests obligatoires

- une définition non éligible ne produit aucun snapshot publiable ;
- une définition référençant une source non acceptée échoue à la validation ;
- une définition contenant une feature hors registre échoue ;
- la bascule est refusée si une des six conditions n'est pas satisfaite ;
- le score reste identique à données et définition identiques.

## Critères d'acceptation

- pour chaque définition : bascule effectuée **ou** refus documenté avec sa raison ;
- périmètre d'éligibilité explicite ;
- versionnement respecté, `v0.1` intacte ;
- les six conditions sont vérifiées automatiquement.

## Preuves à produire

- contrats de scoring versionnés ;
- section dédiée dans [`scoring-v0.6-report.md`](../data/scoring-v0.6-report.md) ;
- tests de bascule dans la suite pipelines.
