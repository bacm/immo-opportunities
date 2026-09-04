# D4 — DS-07 DPE : diagnostics réellement déposés

**Version :** v0.5 · **Taille :** L · **État :** À faire
**Dépend de :** D3 · **Bloque :** D5

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
