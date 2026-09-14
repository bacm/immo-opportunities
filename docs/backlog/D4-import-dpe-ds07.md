# D4 — DS-07 DPE : diagnostics réellement déposés

**Version :** v0.5 · **Taille :** L · **État :** Terminé
**Dépend de :** D1 · **Bloque :** D5
**Touche :** pipelines/scripts/import_dpe_release.py, contracts/datasets/DS-07/, docs/data/dpe-quality-35.md

> **Parallélisable avec D2 et D3** — resequencage du 14 septembre 2026. Ce ticket dépendait de
> D3 sans qu'aucune ligne ne le justifie : les DPE de l'ADEME et les risques de Géorisques sont
> deux sources distinctes, de producteurs distincts. La dépendance venait de l'ordre de la liste,
> pas du travail.

## Contexte à charger

- `contracts/datasets/DS-07/v1.json`
- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md` (§DS-07)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Verdict actuel : « rejeté pour publication — release et contrôle d'appariement réels absents ».

**Deux interdits structurants :**
- aucun DPE simulé ou prédit — seuls les diagnostics réellement déposés sont admis ;
- l'absence de DPE est **neutre sur le score** et réduit seulement la confiance. Elle ne crée ni
  signal de vacance, ni signal de dégradation.

Le second point est la principale tentation à écarter : un bien sans DPE récent ressemble
superficiellement à un bien inoccupé. Le produit ne fait pas de prédiction de vacance.

> **Mécanisme réutilisé :** la quarantaine par attribut de [BUG-03](./BUG-03-quarantaine-par-attribut.md).
> Un `ambiguous_match` est un diagnostic valide dont le rattachement bâtiment est inutilisable.

## Travail à réaliser

1. Épingler et checksumer une release réelle de la base ADEME pour le 35.
2. Importer les `EnergyAssessment` : classe, consommation, date, caractéristiques déclarées,
   référence du diagnostic retenu.
3. Filtrer strictement : diagnostics déposés, non simulés, non annulés, antérieurs au snapshot.
4. Résoudre l'appariement DPE ↔ bâtiment via le référentiel spatial issu de v0.3 :
   - rattachement direct au bâtiment → retenir le dernier diagnostic ;
   - plusieurs diagnostics rattachés seulement à la même adresse → `ambiguous_match` ;
   - aucun rattachement → absence motivée.
5. Persister la **confiance d'appariement** distinctement de la valeur.
6. Mesurer et publier le taux d'appariement par commune, avec la ventilation certain / ambigu /
   non apparié.
7. Produire `REN-001` à `REN-008` avec leur provenance.

## Points de vigilance

- L'appariement DPE est structurellement difficile : l'adresse du diagnostic est saisie
  manuellement et souvent approximative. Un taux d'appariement modeste est un résultat attendu et
  doit être publié tel quel, pas amélioré par un assouplissement non mesuré des règles.
- Un DPE ancien reste un DPE valide : sa fraîcheur alimente la confiance, elle n'invalide pas la valeur.
- Un logement dans un immeuble collectif peut avoir plusieurs DPE légitimes. La cardinalité est
  réelle, pas une anomalie.
- **Risque déclaré :** surinterpréter un DPE. Une classe F ou G est une observation d'un diagnostic,
  pas une preuve d'état du bâti.

## Tests obligatoires

- un diagnostic simulé, annulé ou postérieur au snapshot est rejeté avec motif ;
- plusieurs diagnostics à la même adresse sans rattachement bâtiment : `ambiguous_match` ;
- l'absence de DPE ne modifie aucune contribution de score, seulement la confiance ;
- la référence du diagnostic retenu est conservée et vérifiable ;
- réimport stable.

## Critères d'acceptation

- release réelle, checksumée, importée et auditée ;
- taux d'appariement publié par commune, y compris s'il est faible ;
- verdict documenté ;
- neutralité de l'absence vérifiée par un test, pas seulement affirmée ;
- distributions REN disponibles pour [E1](./E1-profiling-distributions.md).

## Preuves à produire

- manifeste `contracts/datasets/DS-07/releases/<release>-35.json` ;
- section DS-07 de [`market-data-sources-audit.md`](../data/market-data-sources-audit.md) ;
- rapport `docs/data/dpe-matching-35.md`.

## Résultat — 14 septembre 2026, verdict `display_only`

**Preuve :** [`dpe-matching-35.md`](../data/dpe-matching-35.md) · §DS-07 de
[`market-data-sources-audit.md`](../data/market-data-sources-audit.md) · manifeste
`contracts/datasets/DS-07/releases/2026-09-14-extract-35.json`.

231 416 diagnostics épinglés, **aucun écarté à l'éligibilité** : la source ne publie que des
diagnostics réglementaires déposés. 208 086 conservés, 23 330 sans sujet et consignés.

| Classe | Diagnostics | Part |
|---|---:|---:|
| Bâtiment, par `id_rnb` | 136 628 | 59,04 % |
| Adresse seule, par `identifiant_ban` | 71 458 | 30,88 % |
| Non rattaché, motif consigné | 23 330 | 10,08 % |

### Quatre choses que ce ticket a apprises

**L'appariement DPE n'avait pas besoin d'être difficile.** Le point de vigilance annonçait un
taux modeste parce que l'adresse est saisie à la main. C'est vrai de l'adresse — mais la source
publie `id_rnb` sur 59 % des diagnostics, et le RNB est notre référentiel bâtiment. Le
rattachement est une **jointure d'identifiant**, pas une règle géométrique : le résultat négatif
de [B4](./B4-revue-manuelle-appariements.md) n'avait pas à être redécouvert.

**La source se contredit sur son propre géocodage.** 17 135 diagnostics portent un
`identifiant_ban` qui se résout chez nous alors que `statut_geocodage` annonce « aucune
correspondance trouvée », avec un `score_ban` médian *supérieur* à celui des lignes géocodées.
L'adresse est conservée, la confiance devient absente avec motif. Quarantaine par attribut de
[BUG-03](./BUG-03-quarantaine-par-attribut.md), sans qu'aucun seuil soit inventé.

**Le critère « réimport stable » a trouvé un défaut que les tests n'auraient pas vu.** La purge
ne retirait que les *autres* versions de transformation ; un réimport de la même version butait
sur la clé primaire, et un run interrompu ne repartait jamais. Corrigé — la purge porte sur la
release entière — et couvert par test. La leçon de [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md)
avait été à moitié apprise : la version dans l'identifiant ne sert à rien si l'écriture ne peut
pas avoir lieu.

**Un contrôle de mesure n'est pas une étape d'import.** Les contrôles du contrat DS-07 vivaient
d'abord dans l'import, donc derrière son court-circuit d'idempotence : les recalculer demandait
de réimporter 458 Mo. Ils sont passés dans le rapport, qui est rejouable.

### Ce que ce ticket ne livre pas, et pourquoi

`REN-001..008` **ne sont pas matérialisées**. `feature.feature_value.building_id` réfère les
enregistrements RNB, sujet que [BUG-12](./BUG-12-deduplication-batiments-physiques.md) a
invalidé ; [B5](./B5-features-morphologiques.md) avait refusé la même chose pour `BLD-001..003`.
Les distributions dont [E1](./E1-profiling-distributions.md) a besoin sont au rapport. Le
changement de schéma est [BUG-13](./BUG-13-sujet-des-features-batiment.md).

`accepted` attend la revue manuelle stratifiée de [D6](./D6-revue-manuelle-metier.md). 9 423
adresses portent plusieurs diagnostics sans rattachement bâtiment : c'est la population qu'une
revue humaine doit trancher, et B4 a montré ce que cette étape trouve.
