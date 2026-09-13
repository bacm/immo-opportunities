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

### Contrôle de cohérence géométrique des verdicts, ajouté le 10 septembre 2026

Un verdict peut contredire un fait mesurable. Sur une relation bâtiment ↔ parcelle, la part du
bâtiment tombant sur la parcelle du cas se calcule, et se compare à celle de la parcelle qui en
porte le plus.

**Ce contrôle est déclaré ici parce qu'il est postérieur au tirage.** Un contrôle *a posteriori*
appliqué aux seuls verdicts qui dérangent trierait les résultats au lieu de les mesurer. Trois
règles l'en empêchent :

1. il s'applique à **tous** les verdicts de la relation concernée, jamais à une sélection ;
2. il ne juge pas à la place du relecteur — il déclenche un **rappel**, qui rend le cas à juger
   et n'efface pas le premier verdict ;
3. son résultat complet est publié, y compris quand il ne trouve rien.

Premier passage, sur les 12 verdicts bâtiment ↔ parcelle rendus au 10 septembre 2026 :

| Constat | Cas |
|---|---:|
| Verdict cohérent avec la géométrie | **11** |
| Verdict contredit par la géométrie | **1** — cas 90 |

Le cas 90 portait un verdict `correct` sur une parcelle recevant **0,1 %** du bâtiment, alors
qu'une autre en reçoit **99,4 %** — une parcelle de 16 m² pour un bâtiment de 15,5 m², soit une
dépendance sur parcelle propre. Le relecteur a lui-même signalé avoir pu mal voir. Le cas a été
rappelé.

Le contrôle ne s'applique pas aux relations adresse ↔ parcelle : le point BAN est posé côté rue.
Sur les 20 cas jugés, 18 tombent hors de leur parcelle, de 12,8 m à 306 m, et 16 d'entre eux ont
été jugés corrects à juste titre. « Le point est dans la parcelle » n'est donc pas un critère —
ni pour la revue, ni pour une feature à venir.

### Résultat négatif : la relation adresse ↔ parcelle n'est pas vérifiable géométriquement

Le cas 17 — « 11 Rue Nina Companeez 35690 Acigné », jugé `incorrect`, motif « cela semble être
un lotissement mais c'était bien un champ auparavant » — a d'abord paru désigner un défaut de
grande ampleur. Il n'en est rien, et la démonstration mérite d'être conservée parce qu'elle
montre comment une statistique juste conduit à une conclusion fausse.

**Le fait de départ.** L'appariement adresse ↔ parcelle repose sur le champ expérimental
`cad_parcelles` de la BAN, vérifié contre la géométrie. Sur les 325 934 relations produites :

| Point dans la parcelle | À moins de 10 m | Décision | Confiance | Relations |
|---|---|---|---|---:|
| oui | oui | `certain` | 0,99 | 231 675 |
| non | oui | `certain` | 0,95 | 41 020 |
| **non** | **non** | `ambiguous` | 0,80 | **49 479** |
| — | — | `rejected` | 0,00 | 3 760 |

Sur les 49 479 qui échouent aux deux contrôles, **47 468 — soit 95,9 %** — ont une parcelle qui
contient réellement le point d'adresse. La conclusion s'imposait : le moteur ignore la bonne
réponse, qui est là, et il faudrait préférer la parcelle contenante.

**Ce que les verdicts en disent.** Vingt-et-un cas jugés appartiennent exactement à cette
catégorie « échec aux deux contrôles » :

| Verdict | Cas |
|---|---:|
| `correct` | **16** |
| `incorrect` | 3 |
| `undecidable` | 2 |

Seize sur dix-neuf tranchés sont **justes**. Préférer la parcelle contenante casserait seize
relations pour en réparer trois. La statistique était exacte et l'inférence fausse : le point
BAN est posé côté rue, donc la parcelle qui le contient est souvent la voirie ou le voisin.

**La distance ne sépare pas davantage.** Sur ces mêmes cas :

| Distance adresse → parcelle | Verdict |
|---:|---|
| 446 m | `incorrect` |
| 306 m | `undecidable` |
| **145,7 m** | **`correct`** |
| **102,6 m** | **`correct`** |
| **61,7 m** | **`incorrect`** |
| 50,6 · 50,3 · 40,9 m | `correct` |
| **38,0 m** | **`incorrect`** |
| 36,6 m à 12,8 m | `correct`, sauf un `undecidable` à 15,7 m |

Aucun seuil ne sépare : faux à 38 m, juste à 145,7 m.

**Conclusion.** Ni la containment, ni la proximité à 10 m, ni la distance ne distinguent une
relation adresse ↔ parcelle juste d'une fausse. Les trois erreurs ont été trouvées par jugement
humain sur contexte externe — nom de rue récent, lotissement visible, vue aérienne. Le taux
d'erreur de cette relation est réel, de l'ordre de 15 %, et **aucune règle dont nous disposons
ne le réduit**.

C'est un résultat négatif, et il est consigné comme tel. Il vaut mieux qu'un correctif qui
aurait dégradé seize relations sur vingt-et-une.

### Déviation assumée : douze cas rappelés pour une question ambiguë — 11 septembre 2026

La question posée sur la relation bâtiment ↔ parcelle — « Ce bâtiment est-il bien situé sur cette
parcelle ? » — admettait **deux lectures également justes** :

- *est-ce sa parcelle ?* — une identification, donc exclusive ;
- *en touche-t-il un bout ?* — une containment, donc inclusive.

La revue a produit les deux, sur des cas géométriquement identiques :

| Cas | Part sur la parcelle du cas | Meilleure parcelle | Verdict | Motif |
|---|---:|---:|---|---|
| 90 | 0,10 % | 99,40 % | `incorrect` | « non, pas la bonne parcelle » |
| 83 | 0,70 % | 99,30 % | `incorrect` | — |
| **168** | **0,93 %** | **99,07 %** | **`correct`** | « pas entièrement mais une partie est bien là » |

Les trois motifs sont exacts. Ce n'est pas le relecteur qui a varié, c'est la question qui
admettait deux réponses.

**Reformulation.** « Est-ce la parcelle de ce bâtiment ? », complétée par : un bâtiment déborde
souvent sur plusieurs parcelles, la question n'est donc pas s'il en touche un morceau mais si
c'est **la** parcelle à laquelle le rattacher pour compter le bâti du terrain.

Le texte s'arrête là délibérément. Annoncer que la bonne parcelle est celle qui en porte la plus
grande part rendrait **circulaire** la confirmation de cette règle — c'est elle que la revue est
en train d'établir.

**Périmètre du rappel.** Douze cas : `39, 44, 55, 64, 75, 83, 90, 92, 126, 163, 168, 179`. Ce
sont exactement ceux où les deux lectures divergent, c'est-à-dire où la parcelle du cas n'est pas
celle qui porte le plus du bâtiment.

Les quinze autres ne sont pas rappelés : la parcelle du cas y est la majoritaire, les deux
lectures y donnent la même réponse, et les rejuger ne mesurerait rien de plus.

**Pourquoi les douze et pas le seul qui dérange.** Le cas 168 est le seul à contredire la règle
du rang. Ne rappeler que lui aurait trié les résultats en faveur de l'hypothèse en cours de
test — exactement ce que le contrôle de cohérence géométrique déclaré plus haut s'interdit. Le
critère de rappel est la divergence des lectures, pas le désaccord avec une hypothèse.

**Effet sur le dépouillement.** Ces douze cas porteront deux verdicts. Le rapport devra dire
lequel a été rendu sous quelle formulation, et ne pas additionner les deux.

### Déviation assumée : deux strates abandonnées au 122ᵉ cas — 13 septembre 2026

Trente-huit cas non jugés sont **abandonnés**, et ne seront pas jugés. L'abandon est enregistré
cas par cas dans `meta.matching_review_abandonment`, avec son motif, sous le même append-only que
les verdicts : une décision de ce poids doit pouvoir être citée, pas déduite d'une condition
enfouie dans une requête. Un déclencheur interdit d'abandonner un cas déjà jugé — l'écarter après
coup retirerait un résultat connu du dénominateur, ce qui est la définition du tri.

| Strate abandonnée | Jugés | Erreurs | Taux | Écartés |
|---|---:|---:|---:|---:|
| `certain_source_relation` · bâtiment ↔ parcelle | 35 | 15 | **42,9 %** | 18 |
| `ambiguous` · adresse ↔ parcelle | 45 tranchés | 11 | **24,4 %** | 20 |

Les deux ont perdu le critère « zéro erreur sur 60 » dès leur première erreur, et aucun cas
restant ne peut y ramener. Surtout, **les deux ont déjà livré leur conclusion** :

- bâtiment ↔ parcelle : la règle du rang sépare exactement les 35 verdicts — la relation est
  juste si la parcelle est celle qui porte la plus grande part du bâtiment. Aucun seuil n'est
  nécessaire. Voir [BUG-09](../backlog/BUG-09-recouvrement-batiment-parcelle.md).
- adresse ↔ parcelle : résultat négatif acquis, ni containment, ni proximité, ni distance ne
  séparent le juste du faux.

**Le sens de la déviation.** On arrête les deux strates où le moteur a échoué, on poursuit la
seule où il est propre — `certain_official_identifier`, 40 verdicts, zéro erreur. C'est l'inverse
d'un tri favorable, et c'est le premier point à vérifier en relisant ce rapport.

**Ce que l'abandon interdit de conclure.** Une strate abandonnée ne peut plus affirmer de taux
d'erreur au sens de la règle de trois. Elle en **constate** un, sur l'effectif jugé, et le rapport
devra l'écrire ainsi : « 15 erreurs sur 35 cas tranchés », jamais « taux d'erreur de la strate ».

### « Cohérent » veut dire cohérent avec la géométrie, pas avec le moteur

La confusion mérite d'être levée par écrit, parce qu'elle porte sur ce que cette revue mesure.

Le moteur a déclaré **`certain`** les 35 relations bâtiment ↔ parcelle de l'échantillon. Le
relecteur en a contredit **15**, soit 43 %.

| Verdict | Cas | Confiance au plancher de 0,90 | Au-dessus |
|---|---:|---:|---:|
| `correct` | 20 | 4 | 16 |
| **`incorrect`** | **15** | **15** | **0** |

Les quinze erreurs sont **toutes** à la confiance exactement 0,90000 — la valeur produite par le
`greatest(0.9, …)` de `RnbImporter`. Aucune relation dont la confiance dépasse ce plancher n'a été
jugée fausse.

Dire que les verdicts sont « cohérents » signifie donc qu'un **critère unique les explique tous**,
appliqué de la même façon à chaque cas. Ce critère contredit le moteur quatre fois sur dix, et il
désigne précisément la ligne de code qui produit le défaut.

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
