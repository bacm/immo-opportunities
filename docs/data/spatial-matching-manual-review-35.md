# Revue manuelle stratifiée des appariements — département 35

**Date du tirage :** 8 septembre 2026
**Échantillon :** `b4-2026-09-08` · **graine :** `0.35`
**État :** tiré et outillé, **revue non commencée** — 0 verdict sur 180 cas.

Ce document fixe le protocole **avant** que le premier verdict soit rendu. Les résultats y seront
ajoutés à la clôture, sans que rien de ce qui précède soit réécrit.

## Pourquoi cette étape ne peut pas être automatisée

Les contrôles de [B3](../backlog/B3-rapport-appariements.md) vérifient la **cohérence interne**
des appariements : que les quatre classes somment au total, que les motifs sont présents, que les
métriques se recalculent. Aucun ne dit si un appariement est **juste dans le monde réel**.

Trois releases attendent cette réponse : DS-02, DS-03 et DS-04 sont toutes bloquées faute de
seuils calibrés ou de support d'identité accepté.

## Taille de l'échantillon, fixée avant le tirage

**60 cas par strate d'appariement à enjeu, soit 180 au total.**

La justification tient dans la règle de trois : si l'on relit *n* cas et qu'aucun n'est faux, le
taux d'erreur réel est inférieur à *3/n* avec 95 % de confiance.

| n par strate | Taux d'erreur affirmable si zéro erreur |
|---:|---|
| 30 | < 10,0 % |
| **60** | **< 5,0 %** |
| 95 | < 3,2 % |

60 a été retenu parce que le scoring aval ne distingue pas 3 % de 5 % d'erreur d'appariement :
au-delà, la précision supplémentaire coûte des heures sans rien changer à la décision. En deçà,
10 % est trop lâche pour fonder une feature entrant dans un score.

Cette justification est **persistée avec le tirage**, dans
`meta.matching_review_sample.size_rationale`, avec une contrainte de longueur minimale : une
taille justifiée après coup décrit le résultat, elle ne le valide pas.

## Stratification

Trois strates d'appariement — celles qui décident de ce qui peut fonder une feature — croisées
avec quatre territoires. **12 cellules de 15 cas**, parfaitement équilibrées.

| Strate d'appariement | Source | littoral | périurbain | rural | urbain |
|---|---|---:|---:|---:|---:|
| `certain_official_identifier` | `entity_observation_link` | 15 | 15 | 15 | 15 |
| `certain_source_relation` | `entity_match` | 15 | 15 | 15 | 15 |
| `ambiguous` | `entity_match` | 15 | 15 | 15 | 15 |

L'équilibre territorial est délibéré : le rural est très majoritaire en volume dans le 35, et un
échantillon proportionnel y noierait le littoral et l'urbain. Un taux d'erreur mesuré sur un
échantillon non stratifié serait ininterprétable pour chacun d'eux.

### Aucun seuil territorial n'est inventé

`scoring.segment_definition` est en `draft` avec `thresholds: profiling_required` : les segments
produit n'existent pas encore, et les fabriquer ici les figerait avant le profiling de
[E1](../backlog/E1-profiling-distributions.md).

Les strates ci-dessous sont donc des **strates d'échantillonnage**, pas des segments produit.
Elles ne nourrissent aucun score et ne sont persistées nulle part comme une classification du
territoire.

- **`littoral`** : les 24 communes dont la géométrie intersecte la table `limite_terre_mer` de
  `BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15`. C'est une observation de la source, pas un
  jugement — et le littoral prime sur la densité, parce qu'un marché littoral ne se comporte pas
  comme un rural de même densité.
- **`urbain` / `periurbain` / `rural`** : terciles de la distribution **observée** du nombre de
  parcelles par commune. Un tercile décrit une distribution ; il ne prétend rien sur ce qu'est
  une ville.

### Une strate composite, et comment elle sera lue

`certain_source_relation` mélange deux algorithmes : `rnb-plot-relation` (1 240 355 relations
bâtiment ↔ parcelle) et `ban-cad-parcelles` (272 695 relations adresse ↔ parcelle certaines). Le
premier représente 82 % de la strate et dominera donc le taux mesuré.

Ce n'est pas un défaut de validité — le tirage est aléatoire dans la strate, donc le taux estime
correctement celui de la population « appariements certains par relation source ». C'est une
limite d'attribution : sans ventilation, une erreur ne peut pas être imputée à l'un des deux.

**Le dépouillement ventilera donc par algorithme**, ce qui ne demande aucun nouveau tirage.

## Protocole de revue

1. **Tirage reproductible.** `setseed(0.35)`, graine persistée. Rejouer
   `pipelines/scripts/draw_review_sample.py` avec la même graine redonne exactement les mêmes cas.
2. **Revue à l'aveugle.** Le relecteur ne voit ni la décision du moteur, ni sa confiance, ni sa
   justification — l'API ne les envoie pas. Ce n'est pas un masquage à l'écran, qu'une inspection
   du réseau contournerait : c'est une absence à la source, vérifiée par un test end-to-end qui
   inspecte la charge réseau.
3. **Consultation des sources.** Le champ « ce que j'ai consulté » est obligatoire. Un verdict
   rendu sur la seule sortie du moteur mesurerait l'accord avec le moteur, pas l'exactitude.
4. **Trois verdicts.** `correct`, `incorrect`, `undecidable`. « Indécidable » est un résultat
   valide et ne doit pas être forcé.
5. **Append-only.** Un verdict rendu ne se réécrit pas ; un désaccord ultérieur s'ajoute avec sa
   propre date et son propre auteur. Vérifié : `UPDATE` et `DELETE` sont refusés par déclencheur,
   et un cas déjà jugé ne peut plus être retiré.

### Où se fait la revue

Dans l'Explorer, bouton **Revue** — ou directement l'API :

```bash
curl "http://127.0.0.1:18000/api/v1/review/samples/b4-2026-09-08/next"
curl "http://127.0.0.1:18000/api/v1/review/samples/b4-2026-09-08/results"
```

## Comment les résultats seront lus

L'exactitude se calcule sur les **seuls cas tranchés**. Un indécidable a sa propre colonne et ne
gonfle aucun taux : un lot majoritairement indécidable doit se lire comme tel, et non comme un
bon score.

**Si le taux d'erreur observé dépasse ce que le scoring peut absorber, la conclusion est de ne pas
publier — pas d'ajuster le seuil de confiance après coup.** C'est écrit ici, avant de connaître
le résultat, précisément pour que cette décision ne se négocie pas ensuite.

## Ce que cet échantillon ne couvre pas

Le ticket impose d'inclure quatre familles de cas :

| Famille | Volume | Statut |
|---|---:|---|
| Bâtiments RNB ponctuels — risque d'emprise inventée | 3 864 | **non tiré** |
| Cardinalités extrêmes — jusqu'à 37 parcelles, 80 bâtiments | — | **non tiré** |
| Identifiants BAN conflictuels ([BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md)) | 217 | **non tiré** |
| Bâtiments sans code commune, résolus par `rnb-commune-spatial@1` | 403 + 33 | **non tiré** |

Ces cas relèvent d'un **inventaire ciblé**, pas d'un échantillon statistique : on ne cherche pas à
estimer un taux sur eux, mais à vérifier qu'aucun ne produit l'erreur qu'il rend possible. Les
mélanger au tirage aléatoire biaiserait les deux.

Ils feront l'objet d'un second lot, `b4-2026-09-08-inventaire`, dont la taille sera le volume
entier des familles peu nombreuses et un tirage pour les autres.

## Ce que la revue a déjà produit, hors de son objet

**Au 47e cas, le relecteur a trouvé un défaut que la revue ne cherchait pas.**

La question posée sur ce cas était « ces deux bâtiments sont-ils le même ? » — et ils le sont à
100 %, même emprise, distance nulle. Mais en regardant la carte, le relecteur a signalé que le
bâtiment n'était pas sur la bonne parcelle.

Mesure : ce bâtiment de 213 m² chevauche quatre parcelles, dont deux à **3 %** — des échardes de
7 m² dues au désalignement entre cadastre et RNB. Les quatre relations sont enregistrées
`certain`.

À l'échelle du département : **400 706 relations sur 1 240 355 — 32 % — ont un recouvrement
inférieur à 10 %**, et 273 123 sont sous 2 %. Toutes déclarées certaines.

Ouvert en [BUG-09](../backlog/BUG-09-recouvrement-batiment-parcelle.md). Ce défaut était
invisible depuis les contrôles automatiques, qui vérifient la cohérence et non l'exactitude :
une relation fausse mais cohérente les traverse sans bruit.

C'est l'argument le plus net en faveur de cette étape : elle a rendu, avant même d'être
terminée, un résultat qu'aucune métrique n'aurait produit.

## Limite connue de la stratification territoriale

Les strates `urbain` / `periurbain` / `rural` reposent sur les terciles du **nombre** de
parcelles par commune. Le nombre n'est pas la densité : Saint-Just, commune rurale de
6 077 parcelles, est classée `urbain` au même titre que Rennes, qui en compte 38 807 sur une
surface comparable — 776 parcelles/km² contre 164 pour Guipry-Messac, dans la même strate.

L'étiquette est donc trompeuse et le rapport ne pourra pas conclure « taux d'erreur en urbain ».
Ces strates mesurent un **volume**, pas une urbanité.

Le plan n'est pas modifié en cours de route : réétiqueter après avoir vu des verdicts
reviendrait à ajuster l'échantillonnage sur ses résultats, ce que le protocole interdit. La
densité — parcelles par kilomètre carré — est le bon axe pour le prochain tirage, et le
dépouillement nommera ces strates par ce qu'elles mesurent.

Les verdicts déjà rendus restent valides : ils jugent des appariements, pas des territoires.

## Résultats

*À compléter à la clôture de la revue. Rien de ce qui précède ne sera modifié.*
