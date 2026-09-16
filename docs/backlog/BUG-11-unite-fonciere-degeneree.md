# BUG-11 — L'unité analysée par le moteur est une parcelle isolée, et la contiguïté ne peut pas y suppléer

**Version :** v0.6 · **Taille :** L · **État :** En cours
**Dépend de :** D1 · **Bloque :** E2, E3
**Touche :** docs/data/property-unit-35.md, backend/migrations/versions/
**Découvert par :** revue manuelle B4, cas 90, 10 septembre 2026

## Contexte à charger

- `SPEC.md` §14.1 (`PropertyUnit`, `PropertyUnitMember`) — cette section seulement
- `backend/src/immo/explorer.py` (`list_property_units_in_viewport`, `find_property_unit`)
- `docs/backlog/BUG-09-recouvrement-batiment-parcelle.md`
- `docs/backlog/D1-import-dvf-ds06.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

`SPEC.md` définit `PropertyUnit` comme **« l'unité analysée par le moteur ; elle peut contenir
plusieurs parcelles et bâtiments »**. En base, elle n'en contient jamais plus d'une :

| | Valeur |
|---|---|
| Unités foncières | 1 333 327 — soit exactement une par parcelle |
| `unit_type` | `single_parcel` |
| `publication_eligible` | `false` |
| `exclusion_reason` | `entity_resolution_incomplete` |

Le modèle est donc honnête sur son état : il se déclare lui-même inapte à la publication. Ce
ticket ne signale pas un mensonge, il signale que **personne n'a de plan pour lever cette
exclusion**, et qu'aucun ticket ne la porte.

### Ce que le cas 90 a montré

Un bâtiment de 15,5 m² occupe 99,4 % de la parcelle `35288000DA0322`, qui fait **16 m²** — une
dépendance sur parcelle propre, à côté de la `DA0321` de 163 m².

Prises séparément, aucune des deux ne décrit un bien. La 322 seule n'est candidate ni à la
division ni à l'extension : c'est un garage. La 321 seule paraît un terrain nu de 163 m² alors
qu'elle est bâtie de fait. Le moteur, qui score par unité, scorerait deux fois du bruit là où il
y a un bien.

Le relecteur l'a formulé sans connaître le modèle : « ce bâtiment est bien sur la 322 mais pour
moi elle appartient à la personne qui possède la 321 ».

## La contiguïté ne peut pas servir d'approximation — mesuré

Une unité foncière au sens juridique, ce sont des **parcelles contiguës du même propriétaire**.
Le propriétaire nous est inaccessible : le scraping de propriétaires et les données type LOVAC
sont hors périmètre, par décision produit et non par difficulté technique.

Reste la contiguïté seule. Elle ne tient pas. Regroupement des parcelles qui se touchent,
`ST_ClusterDBSCAN` à 1 cm, sur trois communes de profils différents :

| Commune | Parcelles | Grappes | Taille moyenne | Plus grande grappe | Parcelles isolées |
|---|---:|---:|---:|---:|---:|
| Dinard (35093) | 11 188 | 272 | 41,1 | **840** | 0,2 % |
| Rennes (35238) | 38 807 | 1 049 | 37,0 | **3 494** | 0,3 % |
| Saint-Malo (35288) | 30 801 | 822 | 37,5 | **1 320** | 0,3 % |

La contiguïté chaîne d'îlot en îlot : un quartier entier devient une seule « unité », et à peine
0,3 % des parcelles restent isolées. **Ce n'est pas une approximation dégradée, c'est un
non-sens** — et il vaut mieux l'avoir mesuré que de l'avoir supposé.

Le contraste avec [BUG-12](./BUG-12-deduplication-batiments-physiques.md) est net et mérite d'être
retenu : **la même contiguïté, appliquée au bâti, fonctionne** — deux sources indépendantes y
convergent à 0,5 % sur le nombre de bâtiments physiques. Ce n'est donc pas la méthode qui est
mauvaise, c'est le parcellaire qui n'a pas de discontinuité naturelle à exploiter.

## Pourquoi ce ticket est en v0.6 et non en v0.3

Il dépend de [D1](./D1-import-dvf-ds06.md), qui est en v0.5, et bloque
[E2](./E2-publication-eligible.md) et [E3](./E3-publier-snapshots.md), qui sont en v0.6. Une
étiquette v0.3 le rendait irrésoluble dans sa propre version et bloquait la clôture de celle-ci
sans raison.

## Pourquoi ce ticket ne bloque pas B5 — arbitrage du 13 septembre 2026

Ce ticket bloquait `B5`. C'était un **cycle** : il attend les mutations DVF+ pour choisir son
signal de regroupement, DVF+ est importé par [D1](./D1-import-dvf-ds06.md), et D1 dépend de
[B5](./B5-features-morphologiques.md). Attendre revenait à ne jamais commencer.

Le blocage a donc été déplacé là où il a un sens. **Calculer une feature sur une parcelle n'est
pas dangereux ; publier une parcelle en la présentant comme un bien l'est.** Le mal est à la
publication, pas au calcul.

Le garde-fou correspondant existe déjà et tient : les 1 333 327 unités sont en
`publication_eligible: false` avec le motif `entity_resolution_incomplete`. Rien de faux ne peut
sortir, même avec toutes les features calculées.

Ce ticket bloque donc désormais [E2](./E2-publication-eligible.md) et
[E3](./E3-publier-snapshots.md) — le passage en publiable et la publication des snapshots — et
dépend de D1, qui lui apporte le signal qui lui manque.

## Conséquences

Cinq tables portent `property_unit_id`, et toutes sont en aval :

- `feature.feature_value` — les features LAND-* et BLD-* sont calculées **par unité** ;
- `scoring.opportunity_snapshot`, `scoring.published_opportunity`,
  `scoring.opportunity_publication_event` — le produit publie des unités, pas des parcelles ;
- `market.comparable_selection` — les comparables se choisissent par unité.

Donc :

- **[B5](./B5-features-morphologiques.md)** calculerait LAND-001..010 sur des parcelles isolées.
  Une parcelle annexe de 16 m² recevrait une emprise bâtie de 97 %, une parcelle bâtie de fait
  recevrait 0 %.
- **[E3](./E3-publier-snapshots.md)** publierait des candidats qui ne sont pas des biens.
- Le défaut se combine avec **[BUG-09](./BUG-09-recouvrement-batiment-parcelle.md)** : l'un
  attribue le bâti à la mauvaise parcelle, l'autre analyse la parcelle au lieu du bien. Ils
  doivent être lus ensemble, pas corrigés indépendamment.

## Ce que ce ticket ne doit pas faire

- **Choisir l'approximation.** Les signaux candidats ci-dessous ont des propriétés différentes et
  aucun n'est évidemment supérieur. Le ticket les instruit et les mesure ; il ne tranche pas seul.
- **Reprendre la contiguïté nue.** Elle est disqualifiée par la mesure ci-dessus. Toute variante
  qui y revient doit d'abord expliquer pourquoi les grappes de 3 494 parcelles disparaîtraient.
- **Chercher le propriétaire.** Hors périmètre, et ce n'est pas négociable dans ce ticket.

## Signaux candidats à instruire

| Signal | Ce qu'il apporte | Ce qu'il coûte |
|---|---|---|
| **Mutations DVF+** — parcelles vendues dans la même disposition | preuve d'une propriété commune à une date, la plus proche du sens juridique | ne couvre que les parcelles mutées ; dépend de [D1](./D1-import-dvf-ds06.md) |
| **Bâtiment partagé** — parcelles reliées par un même bâtiment | supposé capter le motif du cas 90 — faux, mesuré le 16 septembre | la mitoyenneté produit des faux positifs ; dépend de [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md) et de [BUG-12](./BUG-12-deduplication-batiments-physiques.md), un bâtiment n'étant pas encore défini |
| **Adresse commune** — parcelles portant la même adresse BAN | déjà mesuré, déjà exposé dans la revue | une adresse couvre parfois trois parcelles sans propriétaire commun |
| **Aucun regroupement** — assumer `single_parcel` | honnête, déjà en place | laisse le bruit décrit ci-dessus dans le score |

La dernière ligne est une option réelle, pas un aveu d'échec : publier des parcelles en le disant
vaut mieux que publier des unités inventées.

## Choix retenus — 16 septembre 2026

Repris après le dégel d'[ADR-019](../decisions/ADR-019-lever-le-gel-de-la-plateforme.md). Ce
ticket **mesure et documente** ; le choix du signal est une décision, qui revient au porteur.

- **Contexte** : `SPEC.md` §14.1 n'existe plus depuis la réécriture du 15 septembre ; le modèle est
  décrit dans `ARCHITECTURE.md` §9, et la définition de `PropertyUnit` citée plus haut reste celle
  de la version 0.2.
- **Mesure reproductible** : `pipelines/scripts/property_unit_signals_report.py`, cible
  `make property-unit-report`, sortie `docs/data/property-unit-35.md`, recomptée.
- **Signaux mesurés** : DVF même acte, brut et chaîné ; DVF même acte restreint aux parcelles
  contiguës ; adresse BAN commune (appariements `certain`) ; bâti partagé.
- **Contiguïté** : 1 cm, la tolérance de la mesure déjà publiée plus haut.
- **Bâti partagé** : BUG-09 renvoie le seuil de la relation secondaire à E1. Le rapport ne le
  choisit pas : il balaie quatre valeurs déclarées (5, 10, 25, 40 % de l'emprise).
- **Corroboration** : pour chaque signal, parmi les paires dont les deux parcelles ont été
  vendues, la part vendue dans un même acte ; ligne de base sur les paires contiguës quelconques
  des trois communes de la mesure ci-dessus. C'est un indice d'appartenance commune, pas une
  preuve.
- **Cas de référence** : cas 90 (`DA0321`, `DA0322`) et cas 55 (`ZS0089`, `ZS0091`).
- **Aucune migration** tant que la décision n'est pas écrite.

## Mesure du 16 septembre 2026 — recomptée, en attente de décision

Rapport : [`property-unit-35.md`](../data/property-unit-35.md), recompté en isolement du code,
aucune divergence. Les étapes 1 et 2 sont faites ; l'étape 3 attend la décision du porteur.

| Signal | Parcelles regroupées | Plus grande unité | Vendues ensemble, paires dont les deux sont vendues |
|---|---:|---:|---:|
| DVF même acte, chaîné | 17,0 % | 1 590 | par construction |
| DVF même acte, parcelles contiguës, chaîné | 14,7 % | 171 | par construction |
| Adresse BAN commune | 3,1 % | 41 | 92,8 % |
| Bâti partagé, 10 % → 40 % de l'emprise | 12,0 % → 1,4 % | 48 → 6 | 69,2 % → 78,5 % |
| Ligne de base, parcelles contiguës quelconques | — | — | 26,2 % à 37,8 % |

Ce que la mesure établit :

- **Le cas 90 n'est réuni par aucun signal.** Le garage couvre 0,06 % de la 321. La 322 n'a
  jamais été vendue ; la 321 l'a été en 2018 avec la 323, qui touche les deux. L'intuition du
  relecteur n'est ni confirmée ni infirmée. La ligne « capte exactement le motif du cas 90 » du
  tableau des signaux est fausse.
- **Le bâti partagé repose entièrement sur la relation secondaire**, dont BUG-09 renvoie le seuil
  à E1 : il ne peut pas être retenu avant E1.
- **Le chaînage DVF dans le temps crée une grappe de 1 590 parcelles** ; restreint aux parcelles
  contiguës d'un même acte, il n'en crée plus. Mais un acte dit une propriété commune **à sa
  date**, pas aujourd'hui, et 3 395 actes à plusieurs parcelles ont perdu leurs rattachements
  (parcelles renumérotées), sur une archive 2014-2020 encore `pending`.
- **L'adresse commune est le signal le mieux corroboré**, et le plus étroit.

## Travail à réaliser

1. Mesurer, sur le 35, ce que chaque signal regrouperait : nombre d'unités, distribution des
   tailles, part des parcelles concernées.
2. Confronter chaque signal au cas 90 et aux motifs relevés en revue.
3. Documenter le choix, ou l'absence de choix, dans `docs/data/` avant toute implémentation.
4. Si un regroupement est retenu : `unit_type` en porte le nom, et `exclusion_reason` disparaît
   seulement pour les unités réellement résolues — jamais globalement.
5. Si aucun n'est retenu : l'écrire, et rendre visible dans l'Explorer que l'objet analysé est une
   parcelle et non un bien.

## Tests obligatoires

- une unité regroupant plusieurs parcelles porte un `unit_type` distinct de `single_parcel` ;
- une unité non résolue conserve `publication_eligible: false` avec son motif ;
- le cas 90 — `35288000DA0321` et `35288000DA0322` — sert de cas de référence dans les tests.

## Critères d'acceptation

- la mesure des signaux candidats est publiée dans `docs/data/` ;
- le choix retenu, ou son absence, est écrit et motivé ;
- aucune unité ne devient publiable sans que sa résolution soit prouvée.
