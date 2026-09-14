# D3 — DS-09 Géorisques : granularité conservée

**Version :** v0.5 · **Taille :** L · **État :** Terminé
**Dépend de :** D1 · **Bloque :** D5
**Touche :** pipelines/scripts/import_georisques_release.py, contracts/datasets/DS-09/, docs/data/georisques-quality-35.md

> **Parallélisable avec D2 et D4** — resequencage du 14 septembre 2026. Ce ticket dépendait de
> D2, mais son seul besoin réel est le module `immo_pipelines.market_data.cnig`, écrit et livré.
> Géorisques et le GPU sont deux sources sans rapport ; attendre la fin de D2 pour commencer D3
> allongeait le chemin critique sans raison.

## Contexte à charger

- `contracts/datasets/DS-09/v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md` (§DS-09)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Verdict actuel : « rejeté pour publication — releases par famille de risque absentes ».

**Règle structurante :** la granularité `point`, `zone`, `parcel` ou `commune` est obligatoire et
persistée. Une observation communale reste dans `commune_context_only` et **ne devient jamais** une
exposition parcellaire. C'est la garantie centrale de ce ticket.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Une observation communale est une observation valide dont l'exposition parcellaire est absente.

## Les servitudes d'utilité publique relèvent de ce ticket — décision du 14 septembre 2026

Le catalogue du Géoportail de l'urbanisme expose des **SUP** aux côtés des documents d'urbanisme :
neuf sur le territoire `35` en production. Elles auraient pu entrer par
[D2](./D2-import-gpu-ds08.md), qui lit déjà ce catalogue et sait en extraire les couches CNIG.

Elles n'y entrent pas, parce qu'une SUP n'est pas un document d'urbanisme :

- un PLU **exprime un projet communal** — ce que la collectivité veut faire de son territoire ;
- une SUP **constate une contrainte extérieure** — un périmètre de captage, une canalisation, un
  monument, une servitude aéronautique — qui s'impose au document d'urbanisme sans en dépendre.

C'est la même nature que ce que D3 traite déjà : une contrainte subie, rattachée à un objet
géographique, avec sa granularité propre. Les ranger avec les PLU aurait mélangé un projet et une
contrainte dans la même table, et rendu `URB-005` — la complétude des règles d'urbanisme —
dépendante d'objets qui n'ont pas de règles à valider.

**Conséquence pratique :** la source des SUP est le GPU, pas Géorisques, mais leur traitement est
celui de D3. Le module `immo_pipelines.market_data.cnig` écrit pour D2 sert donc aux deux, ce qui
est un effet secondaire heureux et non une raison d'avoir choisi ainsi.

La règle de granularité de ce ticket s'y applique telle quelle : une SUP dont le périmètre est
communal reste `commune_context_only` et ne devient jamais une exposition parcellaire.

## Travail à réaliser

1. Traiter chaque famille de risque comme une **release distincte** : elles n'ont ni la même
   granularité, ni la même fraîcheur, ni le même producteur. Une release unique « Géorisques »
   masquerait ces différences.
2. Pour le 35, couvrir au minimum les familles pertinentes à la qualification : inondation,
   retrait-gonflement des argiles, submersion marine et recul du trait de côte sur le littoral,
   sites et sols pollués, installations classées, radon.
3. Épingler et checksumer chaque release par famille.
4. Importer les `RiskObservation` en persistant la granularité d'origine et la date de la donnée.
5. Rattacher spatialement selon la granularité disponible, sans jamais en inventer une plus fine.
6. Produire `RISK-001` à `RISK-004` et `RISK-101` avec, pour chaque valeur, la granularité de la
   source qui la fonde.

## Points de vigilance

- **Risque déclaré :** surinterpréter un risque. « La commune est concernée par un PPRI » et « la
  parcelle est en zone inondable » sont deux affirmations différentes ; la seconde exige une donnée
  zonale, pas communale.
- Zéro intersection n'est produit **que** lorsque la couverture fine concernée est connue. Sinon,
  l'absence de risque détecté est une absence d'information, pas une absence de risque.
- Le littoral breton rend la submersion et le recul du trait de côte structurants sur le 35 nord ;
  ces familles ne peuvent pas être traitées comme secondaires.
- Un risque n'est pas un signal négatif automatique pour le scoring : il peut être une contrainte
  chiffrable dans un scénario de rénovation. Le lien risque → score se décide en [E1](./E1-profiling-distributions.md),
  pas ici.

## Tests obligatoires

- une observation communale ne produit jamais d'exposition parcellaire ;
- l'absence de couverture fine produit une absence motivée, pas un zéro ;
- chaque valeur porte la granularité de sa source ;
- une famille de risque non importée désactive explicitement les features correspondantes ;
- réimport stable.

## Critères d'acceptation

- une release par famille, réelle, checksumée, auditée ;
- granularité persistée et vérifiable sur chaque observation ;
- verdict documenté par famille ;
- couverture publiée par commune et par famille ;
- distributions RISK disponibles pour E1.

## Preuves à produire

- manifestes `contracts/datasets/DS-09/releases/…` par famille ;
- section DS-09 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/georisques-coverage-35.md`.

## Résultat — 14 septembre 2026, `display_only` sur dix familles

**Preuves :** [`georisques-source-inventory-35.md`](../data/georisques-source-inventory-35.md) ·
[`georisques-coverage-35.md`](../data/georisques-coverage-35.md) · §DS-09 de
[`market-data-sources-audit.md`](../data/market-data-sources-audit.md) · dix manifestes dans
`contracts/datasets/DS-09/releases/`.

**10 824 observations, dont 6 985 à granularité fine.** Une release par famille, comme le ticket
le demandait.

### L'inventaire avant le premier lot a changé la forme du ticket

`ARCHITECTURE.md` §10.6 impose d'inventorier la variété d'une source avant son premier lot. Fait
ici, il a montré que le ticket supposait un mode d'accès là où la source en a **quatre** :

| Mode | Familles |
|---|---|
| API départementale, un appel | ICPE, cavités, mouvements de terrain, sites pollués |
| API communale, 332 appels | radon, GASPAR, atlas des zones inondables, CatNat |
| Téléchargement national de 623 Mo | argiles |
| Géoportail de l'urbanisme | servitudes |

C'est cet inventaire, et non l'import, qui a permis d'écrire les gardes qui suivent.

### Quatre pièges, tous silencieux

**Un paramètre territorial inconnu est ignoré, pas rejeté.**
`installations_classees?code_departement=35` répond `200` avec **138 248 résultats** — la France
entière — parce que le paramètre attendu s'appelle `departement`. Sur `ssp/instructions`, c'est
l'inverse. Le filtre est vérifié ligne à ligne ; s'y fier au code HTTP aurait peuplé la base de
134 000 lignes étrangères sans une erreur.

**Le lien de pagination pointe une machine interne du producteur** —
`api-georisques.bike-prod.brgm.fr`, en clair et injoignable. Toute famille de plus d'une page
échouait. Les pages sont reconstruites sur l'hôte public.

**Un `500` peut vouloir dire « paramètre manquant ».** La temporisation se décide sur le corps,
pas sur le statut.

**Un `403` du GPU n'est pas toujours un refus.** `T1` a échoué une fois puis répondu ; quatre
autres documents le refusent aux trois tentatives. Sans reprise, un refus passager retirait un
document du manifeste et personne n'y revenait.

**Et un cinquième, trouvé après coup.** `_geojson_wkt` ne traitait que les `MultiPolygon` : le
découpage des argiles par commune produit un `Polygon` dès que l'intersection est d'un seul
tenant, et **1 131 observations sur 1 428 disparaissaient**, import en succès. Corrigé, couvert
par test, et l'import compte désormais tout enregistrement qui ne produit aucune observation —
c'est ce compteur qui empêche la perte silencieuse de recommencer.

### `RISK-002` reste absente, et c'est un résultat

Aucune source du 35 ne donne une zone inondable **typée**. GASPAR et l'atlas disent qu'une commune
est concernée : c'est communal, et « la commune est concernée par un PPRI » n'est pas « la
parcelle est en zone inondable » — l'interdit central du ticket.

La servitude `PM1` donne bien des géométries de zone, seul zonage opposable du département, mais
elle porte les risques naturels prévisibles **sans dire lequel** : son assiette est une
« enveloppe des zonages réglementaires ». En déduire « inondation » serait la faute commise sur le
champ `ETAT` du CNIG pendant [D2](./D2-import-gpu-ds08.md). Les périmètres restent visibles dans
`RISK-101` sous `sup_PM1`.

**Ce qui débloquerait `RISK-002`** est la table de correspondance assiette `PM1` → aléa, à sourcer
auprès du producteur. Travail court, non fait ici parce qu'il demande une source, pas du code.

### Ce que les servitudes ont apporté, et ce qui manque

Cinq des neuf servitudes du 35 sont lisibles, dont `PM1` et `PM3`, les deux qui portent des
risques. Les quatre autres — canalisations, aéronautique, télécoms — sont refusées au
téléchargement par leur producteur, aux trois tentatives. Aucune feature RISK ne les consulte, et
le manifeste consigne le refus plutôt que de laisser croire à une couverture complète.

`find_layers` de `market_data.cnig` accepte désormais une liste de couches : la reconnaissance est
la même pour un document d'urbanisme et pour une servitude, seule la liste change.

### Pourquoi `display_only`

La revue manuelle stratifiée relève de [D6](./D6-revue-manuelle-metier.md). B4 a montré ce qu'elle
trouve que les contrôles automatiques ne voient pas.
