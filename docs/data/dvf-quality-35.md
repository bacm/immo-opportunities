# DVF — qualité et couverture, département 35

**Date :** 14 septembre 2026 · **Ticket :** [D1](../backlog/D1-import-dvf-ds06.md)
**Release :** `DS-06@2026-09-13`, millésimes 2021 à 2025 · **Transformation :** version 2

## La source a changé, et le contrat dit pourquoi

Le contrat DS-06 désignait **DVF+ open-data du Cerema**. Ses deux ressources sur data.gouv.fr
pointent vers un dossier **Box partagé**, pas vers des fichiers, et l'API Box répond **401** sans
authentification. Un import archivé, checksumé et relançable y est impossible.

La source retenue est **geo-dvf** : la même donnée DGFiP, géocodée par Etalab, partitionnée par
année et par département. Son `id_parcelle` **est** notre `cadastral_id`, ce qui supprime un
appariement et donc une source d'erreur.

Le prix payé est explicite : DVF+ pré-qualifie les mutations complexes, geo-dvf non. Cette
qualification est devenue notre code, donc testable — et c'est elle que ce rapport mesure.

## Volumétrie

| | |
|---|---:|
| Mutations | **133 066** |
| Biens (lots) | **337 019** |
| Millésimes | 2021 à 2025 |
| Communes vues | 333 |

## La profondeur d'historique — cinq ans par les canaux officiels, douze par l'archive

**Vérifié le 15 septembre 2026.** Nos cinq millésimes ne sont pas un choix d'import : c'est tout ce
que les canaux officiels publient aujourd'hui.

| Voie officielle | Constat |
|---|---|
| `files.data.gouv.fr/geo-dvf/latest/csv/` | ne liste que 2021 à 2025 ; 2014, 2019 et 2020 répondent 404 |
| `files.data.gouv.fr/geo-dvf/2025-12/csv/` | même contenu — le millésimé n'est pas plus profond que `latest` |
| jeu « Demandes de valeurs foncières », data.gouv.fr | 5 ressources, couverture déclarée **2021-01-01 → 2025-12-31** |
| `cadastre.data.gouv.fr/dvf` | renvoie au jeu ci-dessus, et à « DVF janvier 2021 - décembre 2025 » |

DVF open data est une **fenêtre glissante** : la DGFiP retire de ses pages les millésimes au-delà
de cinq ans.

### Les publications antérieures existent, archivées par un tiers

`https://data.cquest.org/dgfip_dvf/` conserve **onze publications semestrielles DGFiP**, de
`201904` à `202504`. Celle d'avril 2019 porte `valeursfoncieres-2014.txt` à
`valeursfoncieres-2018.txt` — vérifiés accessibles, 333 Mo pour 2014, format DGFiP brut à
séparateur `|`.

En combinant les publications archivées et les millésimes courants, **l'historique atteint 2014**,
soit douze ans.

| Ce que ça coûte | Détail |
|---|---|
| Provenance | archive **tierce**, pas le producteur. Le répertoire daté `201904` est un meilleur ancrage qu'un alias `latest`, mais la publication doit être nommée et son checksum épinglé |
| Format | DGFiP brut, pas le CSV géocodé d'Etalab : pas d'`id_parcelle` tout fait |
| Transformation | l'identifiant cadastral se reconstruit par concaténation — `Code departement` + `Code commune` + `Prefixe de section` + `Section` + `No plan`, champs 19 à 23. C'est une transformation à tester, pas une jointure acquise |
| Qualification | Etalab ne pré-qualifie pas ces fichiers ; notre code le fait déjà depuis D1 |

Le travail est porté par [D8](../backlog/D8-historique-dvf-2014.md).

### Le miroir coïncide avec la source officielle — contrôle préalable de D8

[D8](../backlog/D8-historique-dvf-2014.md) interdit d'importer l'archive avant d'avoir vérifié
qu'elle reproduit la source. Le contrôle porte sur **2022**, présent des deux côtés, au niveau
**ligne** — plus strict qu'un recomptage de mutations, et indépendant du regroupement.

| Source | Lignes | Somme valeur foncière | Communes |
|---|---:|---:|---:|
| miroir `202404` — avril 2024 | 78 427 | 37 333 825 102 € | 333 |
| miroir `202504` — avril 2025 | **78 448** | **37 337 408 616 €** | 333 |
| geo-dvf `latest` — décembre 2025 | **78 448** | **37 337 408 616 €** | 333 |

**La publication la plus récente du miroir coïncide au centime près** avec la donnée officielle
courante. L'écart de `202404` — 21 lignes, 0,027 % — n'est pas une infidélité du miroir : la DGFiP
**révise** ses fichiers d'une publication à l'autre.

Conséquence à porter dans le contrat : un millésime ancien n'existe que dans la version publiée à
sa date. 2014 à 2018 ne sont disponibles que dans la publication d'**avril 2019**, et aucune
correction ultérieure ne les atteindra. La publication fait partie de l'identité de la release,
pas de sa provenance seulement.

### L'identité de mutation d'Etalab n'est pas reproductible, et l'écart est mesuré

Le format DGFiP brut ne porte **pas** d'`id_mutation` : Etalab le fabrique. Le regroupement doit
donc être reconstruit, et il a été calibré contre la vérité d'Etalab sur 2022, où les deux
sources existent — 31 072 mutations pour 78 448 lignes.

| Clé reconstruite | Mutations | Écart |
|---|---:|---:|
| date + commune + valeur + n° disposition | **31 112** | **+40 — 0,13 %** |
| date + commune + valeur + disposition + nature | 31 148 | +76 |
| date + commune + valeur | 30 935 | −137 |
| date + valeur + disposition, sans commune | 28 171 | −2 901 |
| date + commune + disposition, sans valeur | 18 319 | −12 753 |

Aucune clé ne reproduit exactement la partition. La meilleure s'en écarte de **0,13 %**, et la
distribution des tailles de groupe suit de près — écarts de quelques dizaines par taille.

Ce que cet écart affecte, et ce qu'il n'affecte pas :

- **sans effet** sur « cette parcelle a-t-elle jamais été vendue » : la question se pose au niveau
  de la ligne, pas de la mutation ;
- **avec effet** sur la qualification de complexité, donc sur les comparables : 0,13 % des
  mutations d'un millésime archivé seront groupées autrement qu'Etalab ne l'aurait fait.

Le chiffre est publié plutôt qu'absorbé, et il porte la version de transformation.

### Ce que douze ans changeraient

Le signal « ce bien n'a pas changé de mains depuis longtemps », marqueur de succession latente,
**n'est pas exploitable sur cinq ans** : sur le 35051, 1 390 parcelles sur 9 329 — 14,9 % — portent
au moins une mutation. Les 85,1 % restantes ne forment pas une population remarquable, ne pas avoir
vendu en cinq ans étant le cas ordinaire. Sur douze ans, l'absence redevient discriminante.

## Rattachement au référentiel spatial

**328 571 lots sur 337 019, soit 97,49 %**, se rattachent à une parcelle du cadastre par jointure
directe.

### Les 2,5 % non rattachés sont un décalage temporel, pas un défaut d'appariement

Le taux monte régulièrement vers le présent :

| Millésime | Lots | Rattachés | Taux |
|---|---:|---:|---:|
| 2021 | 77 928 | 75 057 | 96,32 % |
| 2022 | 78 448 | 76 287 | 97,25 % |
| 2023 | 63 251 | 61 721 | 97,58 % |
| 2024 | 57 147 | 55 659 | 97,40 % |
| **2025** | 60 245 | 59 847 | **99,34 %** |

C'est la signature d'une **dérive de numérotation parcellaire** : DVF est historique, le cadastre
est un instantané au 1ᵉʳ juin 2026. Une parcelle divisée, fusionnée ou renumérotée depuis la vente
n'existe plus sous son ancien identifiant. Aucun appariement meilleur ne récupérerait ces lots :
l'objet qu'ils désignent n'existe plus.

### Quatre communes sous 90 %, et l'une d'elles s'explique entièrement

| Commune | Lots | Rattachés | Taux |
|---|---|---:|---:|
| **35112 Fleurigné** | 226 | 1 | **0,4 %** |
| 35031 La Bouëxière | 1 633 | 900 | 55,1 % |
| 35189 Montgermont | 762 | 658 | 86,4 % |
| 35207 Noyal-sur-Vilaine | 1 829 | 1 627 | 89,0 % |

**Fleurigné apparaît dans DVF en 2021 et 2023, plus du tout en 2025**, et ne figure ni dans nos
parcelles ni dans notre référentiel de communes — notre cadastre en compte 332, DVF en voit 333.
La commune a fusionné et ses parcelles ont été renumérotées sous la commune absorbante. Ses
transactions restent enregistrées, sans rattachement, avec le motif que porte leur `parcel_id`
nul.

Les trois autres relèvent du même phénomène à moindre échelle : des parcelles divisées entre la
vente et le millésime cadastral.

## Mutations complexes — 65,5 % n'ont pas de prix allouable

C'est le résultat central, et le ticket le désignait comme « le point le plus sensible ».

`geo-dvf` répète la `valeur_fonciere` **à l'identique sur chaque ligne** d'une même mutation. Elle
n'alloue jamais le prix par bien. Diviser ce montant par la surface d'un lot fabriquerait un prix
faux et parfaitement crédible.

| Motif | Mutations | Part |
|---|---:|---:|
| `multiple_priced_lots` | **38 920** | 29,2 % |
| `multiple_parcels` | **33 973** | 25,5 % |
| `no_priced_lot` | 11 301 | 8,5 % |
| `surface_missing` | 2 125 | 1,6 % |
| `price_missing` | 800 | 0,6 % |
| **Allouables** | **45 947** | **34,5 %** |

Chaque transaction est **conservée** : c'est son prix unitaire qui est inutilisable, avec sa
raison. C'est la quarantaine par attribut de [BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md),
que D1 demandait de réutiliser.

### La règle d'allocation, et l'erreur qu'elle a corrigée

Le prix ne va qu'au **lot auquel il se rapporte** :

- des lots bâtis existent → le prix se rapporte au bâti, par la convention du prix au m²
  habitable, le terrain venant avec ;
- aucun lot bâti → c'est une vente de terrain, le prix se rapporte au terrain ;
- **plusieurs lots chiffrables → la mutation est complexe.** Une maison avec son garage tombe
  ici : le montant couvre les deux sans dire ce qui revient à chacun.

Les lots de terrain d'une vente bâtie ne sont pas ignorés — ils restent enregistrés avec leur
surface et leur nature de culture, simplement sans prix.

**La version 1 de cette règle était fausse.** Elle regardait les types de local distincts ; un
lot de terrain n'ayant pas de `type_local`, une vente de maison-avec-terrain ne comptait qu'un
type et n'était pas jugée complexe — **chacun des deux lots recevait donc le montant entier**.
5 410 mutations et 13 303 lots étaient concernés, soit 8,3 % des mutations alors jugées simples.
Le même argent était compté deux fois, et un lot de terrain portait le prix d'une maison.

Le défaut se voyait dans les chiffres : 21 469 lots « Terrain » avec un prix alloué, pour 274
ventes de terrain à bâtir par an. La médiane du prix au m² d'une maison est passée de 2 471 € à
**2 586 €** une fois la correction faite.

## Nature des mutations — 1,0 % écartées des comparables

Un **échange** valorise une soulte ; une **adjudication** est une vente forcée dont le prix dépend
des conditions de l'enchère. Les deux portent un prix, et sans filtre ils entraient dans les
comparables exactement comme une vente.

1 386 mutations, soit 1,0 %, sont écartées par leur nature avec le motif
`mutation_nature_not_market`. La liste des natures retenues est **fermée** : une nature inconnue
est écartée avec son motif plutôt qu'admise par défaut, de sorte qu'un millésime introduisant un
libellé nouveau le fasse savoir.

## Distributions observées du prix au m²

Sur les lots allouables, rattachés, et de nature marchande :

| Type de bien | Lots | Q1 | Médiane | Q3 |
|---|---:|---:|---:|---:|
| Maison | 19 246 | 1 981 € | **2 586 €** | 3 293 € |
| Terrain | 18 478 | 1 € | **75 €** | 181 € |
| Appartement | 4 229 | 2 605 € | **3 839 €** | 5 000 € |
| Local industriel ou commercial | 2 566 | 750 € | **1 527 €** | 2 695 € |
| Dépendance | 287 | 58 € | **177 €** | 653 € |

L'étendue du terrain — de 1 € à 181 € entre quartiles — n'est pas une anomalie : elle mêle terres
agricoles et terrains à bâtir. C'est précisément ce qu'un **segment** doit séparer, et les
frontières de segment viennent du profiling de [E1](../backlog/E1-profiling-distributions.md),
pas d'un découpage choisi ici.

## Support statistique par commune

Ventes de maison exploitables — allouables, rattachées, de nature marchande — sur cinq ans :

| Seuil | Communes |
|---|---:|
| Au moins 5 ventes | 305 sur 332 |
| Au moins 10 ventes | 267 sur 332 |
| Au moins 30 ventes | **152 sur 332** |
| Aucune vente exploitable | 4 |

Ces seuils sont donnés **à titre de lecture, pas de décision**. Le support minimal requis pour
qu'une médiane soit exploitable vient du profiling de E1, jamais d'une valeur choisie ici. Le
risque déclaré de la v0.5 — la fausse précision de prix — se lit dans ce tableau : si E1 retient
un support de 30 ventes, **moins d'une commune sur deux** disposera d'une médiane maison.

Une commune sans comparable exploitable est un résultat légitime. Elle doit produire une feature
absente motivée et une confiance réduite, jamais un repli sur la moyenne départementale.

## Reproduire

```bash
make dvf-import DEPARTMENT=35
```

Idempotent : la clé d'idempotence et l'identifiant de run portent la version de transformation.
La version 2 a rendu la version 1 rejouable, ce que BUG-09 avait montré nécessaire.
