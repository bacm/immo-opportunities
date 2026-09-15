# E8i — Écarter les parcelles en ZAC de la liste de divisibilité, et montrer la signature d'un aménageur

**Version :** v0.6 · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/scripts/field_test_kit.py, pipelines/tests/test_exploratory_candidates.py, pipelines/tests/test_field_test_kit.py, docs/data/exploratory-candidates/, docs/data/exploratory-candidates-35051.md, docs/data/field-test-35/
**Dépend de :** E8h · **Bloque :** E9
**Demandé par :** revue du 15 septembre 2026 — « j'ai trouvé un loup : 35051000ZY0198 »

## Contexte à charger

- `pipelines/scripts/exploratory_candidates.py` — `Parameters`, `eligible`, `enrich`
- `docs/backlog/D2-import-gpu-ds08.md` — l'interdit structurant, section « Interdit »
- `docs/data/exploratory-candidates-35051.md`

Ne rien charger d'autre sans nécessité démontrée.

## Le loup

`35051000ZY0198` figurait dans la liste : 2 372 m², emprise 11 %, 43 m de large. Ses deux seules
voisines, 3,5 ha et 5 600 m², ont été achetées par un aménageur le 28 décembre 2020 dans un acte
à dix parcelles et 564 k€, et une trentaine de lots à bâtir ont été revendus autour depuis 2021.
La parcelle est dans une **zone d'aménagement concerté**, code CNIG `information 02`, que la
feature `URB-003` portait déjà — comptée dans « 10 information », jamais lue.

Ce n'est pas un cas isolé : **10 des 35 candidats** sont en ZAC, contre 5 % des parcelles bâties
en zone `U` de la commune. Le filtre de divisibilité cherche de grandes parcelles peu bâties, et
c'est exactement ce qu'une ZAC contient. Quatre touchent l'acte de 2020.

## Choix retenus

- **Exclusion, pas marquage** — arbitrage du 15 septembre 2026. Dans une ZAC le foncier est sous
  la main de l'aménageur et du droit de préemption ; un marchand n'y a rien à faire, et le lui
  montrer coûte sa confiance dans le reste de la liste.
- **Lire un code typé n'est pas interpréter un règlement.** [D2](./D2-import-gpu-ds08.md) interdit
  l'interprétation automatique du texte des règlements PLU. `information 02` est une entrée du
  dictionnaire CNIG, au même titre que le type de zone `U` que l'entonnoir lit déjà. Le refus de
  traduire ce qu'une zone *autorise* ne justifie pas d'ignorer ce qu'un code *désigne*.
- **Une parcelle est en ZAC si le périmètre couvre plus de la moitié de sa surface.** Paramètre
  déclaré arbitraire, comme les autres. La distribution observée sur 35051 est bimodale — 133
  unités sous 5 %, 670 au-dessus de 50 %, 8 entre les deux — la règle ne tranche donc presque
  rien à la marge.
- **La signature d'un aménageur est un contexte, pas un filtre.** Une voisine contiguë entrée dans
  un acte « Vente terrain à bâtir » portant au moins trois parcelles depuis 2014 est écrite sur la
  ligne et sur la fiche, avec la date et le nombre de parcelles. Elle ne dépend pas du PLU et
  aurait suffi à repérer les quatre cas. Le seuil de trois parcelles est déclaré.
- **La date 1600 n'est pas traitée.** Vérifié : BD TOPO arrondit les dates anciennes au siècle ou
  au demi-siècle — 21 321 bâtiments à 1800, 4 911 à 1700, 1 198 à 1600. Le rapport le disait déjà.

## Tests obligatoires

- une ZAC couvrant plus de la moitié de la parcelle exclut, une bande de 0,1 m² n'exclut pas ;
- une feature de contraintes absente n'exclut pas comme « hors ZAC » : elle reste absente, comptée ;
- la signature d'aménageur ne lit que des voisines contiguës et des actes multi-parcelles ;
- les deux listes gardent leur graine ; la liste E8 change de candidats, et le rapport le dit.

## Critères d'acceptation

- l'entonnoir de 35051 porte une étape « hors ZAC » avec son décompte ;
- `35051000ZY0198`, `ZE0101`, `ZE0186`, `YC0199` ne figurent plus dans la liste ;
- la colonne de contexte et la fiche portent la signature d'aménageur quand elle existe.

## Preuve à produire

`docs/data/exploratory-candidates-35051.md` et `docs/data/field-test-35/35051/` régénérés.
