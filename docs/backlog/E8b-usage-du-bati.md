# E8b — Distinguer l'usage du bâti, faute de quoi la liste sélectionne des routes et des espaces verts

**Version :** v0.6 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/tests/test_exploratory_candidates.py, docs/data/exploratory-candidates/
**Dépend de :** E8 · **Bloque :** E9
**Découvert par :** relecture manuelle de 10 candidats, 15 septembre 2026

## Contexte à charger

- `docs/backlog/E8-liste-exploratoire-terrain.md`
- `docs/data/exploratory-candidates-35051.md`
- `docs/backlog/BUG-13-sujet-des-features-batiment.md`
- `docs/data/spatial-sources-audit.md` (verdicts DS-03 et DS-04 seulement)

Ne rien charger d'autre sans nécessité démontrée.

## Le constat qui ouvre le ticket

Dix candidats de la liste `35051` relus à la main : **deux présentent un intérêt**. Les huit autres
sont des délaissés de voirie, des parcelles industrielles ou des espaces verts.

Ce n'est pas un défaut de réglage. Le filtre de [E8](./E8-liste-exploratoire-terrain.md) sélectionne
« grande parcelle, petit bâtiment », et cette description convient **exactement aussi bien** à un
jardin de maison, à un espace vert communal, à un dépôt et à un délaissé de voirie. L'attribut qui
les sépare est l'usage de la parcelle, et il n'entre dans aucun critère.

## Ce qui existe en base, et pourquoi personne ne s'en sert

L'usage du bâti est importé **deux fois**, et n'est rattaché à rien :

| Source | Volume | Attribut | Rattachement |
|---|---:|---|---|
| DS-04 BD TOPO | 974 172 | `usage_1`, `nature`, `nombre_de_logements` | `entity_id` **NULL** sur la totalité |
| DS-03 BDNB | 546 301 | `ffo_bat_usage_niveau_1_txt`, `ffo_bat_nb_log` | `entity_id` **NULL** sur la totalité |

Seul RNB alimente `reference.building`, et donc `reference.building_parcel`. C'est la cause
racine de `BLD-001` « non matérialisée » et du verdict `display_only` de DS-03 et DS-04 —
[BUG-13](./BUG-13-sujet-des-features-batiment.md) porte le sujet général.

**Un pont existe pourtant, déclaré par le producteur** : BD TOPO publie `identifiants_rnb`, présent
sur **939 818 bâtiments sur 974 172, soit 96,5 %**, multivalué par `/` dans 29 236 cas. Il ne
demande aucun appariement géométrique — donc aucune des erreurs que
[B4](./B4-revue-manuelle-appariements.md) a mesurées sur l'adresse.

### Ce que le pont donne, mesuré sur les 36 candidats

| Usage BD TOPO | Candidats |
|---|---:|
| au moins un bâtiment `Résidentiel` | 14 |
| `Commercial et services` seulement | 5 |
| `Indifférencié` seulement | 7 |
| aucun bâtiment BD TOPO rattaché | 10 |

La parcelle `35051000AZ0323`, rejetée à la relecture, est classée `Commercial et services`.

### La couverture de l'attribut, et sa limite

| | `Résidentiel` | inconnu | autres usages |
|---|---:|---:|---:|
| BD TOPO `usage_1` | 38,2 % | 44,7 % `Indifférencié` | 17,1 % |
| BDNB `ffo_bat_usage_niveau_1_txt` | 65,4 % individuel + collectif | 28,4 % vide | 6,2 % |

Les deux sont **complémentaires** : là où BD TOPO dit « Indifférencié », BDNB dit souvent
« Résidentiel individuel ». BDNB n'a cependant aucun identifiant RNB et ne se rattacherait que par
géométrie ; ce ticket ne l'instruit pas.

## La décision que ce ticket prend, et qu'il doit assumer

**Filtrer sur une source `display_only`.** DS-04 n'est pas acceptée. L'utiliser pour écarter des
candidats est acceptable ici parce que la liste ne publie rien et sert à être contestée par un
humain — mais ce serait inacceptable dans un score publié. La distinction doit être écrite dans le
rapport, pas sous-entendue.

**Ne pas écarter l'inconnu comme s'il était connu.** Un bâtiment `Indifférencié` n'est pas un
bâtiment non résidentiel. Les trois populations — usage résidentiel, usage non résidentiel connu,
usage inconnu — restent distinctes, et le rapport publie leurs volumes.

## Ce que ce ticket ne doit pas faire

- **Régler les seuils existants sur les dix verdicts.** Descendre `max_footprint_ratio` parce que la
  liste « a l'air mieux » serait de l'ajustement sur un échantillon de dix. Ce ticket ajoute une
  **dimension manquante**, nommée par la relecture ; il ne retouche pas les bornes de E8.
- **Recoder le libellé de zone d'urbanisme.** Toujours interdit, toujours pour la raison de D2.
- **Résoudre BUG-13.** Le pont `identifiants_rnb` sert la liste exploratoire ; il ne matérialise pas
  `BLD-001` et ne change aucun verdict de release.

## Travail à réaliser

1. Rattacher l'usage BD TOPO à la parcelle par `identifiants_rnb`, en tenant le multivaleur `/`.
2. Ajouter au filtre une exigence d'usage résidentiel, et à l'entonnoir les étapes correspondantes.
3. Publier dans le rapport les trois populations — résidentiel, non résidentiel connu, inconnu —
   avec leurs volumes, et l'usage de chaque candidat retenu.
4. Écrire dans le rapport que le filtre s'appuie sur une release `display_only`.
5. Régénérer la liste sur `35051` et mesurer ce que le filtre change.

## Tests obligatoires

- un identifiant RNB multivalué `a/b` rattache les deux bâtiments ;
- une parcelle sans bâtiment BD TOPO est comptée `inconnu`, jamais `non résidentiel` ;
- une parcelle dont tous les bâtiments connus sont non résidentiels est écartée ;
- une parcelle mêlant `Résidentiel` et `Annexe` est retenue.

## Critères d'acceptation

- l'usage est rattaché sans appariement géométrique ;
- inconnu et non résidentiel restent deux populations distinctes, aux volumes publiés ;
- le recours à une source `display_only` est écrit dans le rapport ;
- les seuils de E8 sont inchangés ;
- l'effet du filtre sur la liste `35051` est mesuré et publié.

## Preuve à produire

`docs/data/exploratory-candidates-35051.md`, régénéré : entonnoir enrichi, volumes par population
d'usage, usage affiché par candidat.

**Relu le 16 septembre 2026 ([BUG-13](./BUG-13-sujet-des-features-batiment.md)).** BUG-13 a
donné aux features de bâtiment leur sujet, le bâtiment physique RNB. Il n'a pas rattaché BDNB au
RNB : cet appariement géométrique reste à ouvrir sous son propre ticket.
