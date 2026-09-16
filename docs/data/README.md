# Rapports de données

Chaque rapport est daté et dit ce qu'il a mesuré, sur quelle release, avec quel filtre. Ce sont des
documents **historiques** : ils restent vrais à leur date et ne sont pas réécrits. Un chiffre qui
en sort passe par `recompte-preuve` avant d'être repris ailleurs.

## Ce que les données ont établi sur le 35

Synthèse des rapports ci-dessous, au 16 septembre 2026. `SPEC.md` §10 dit ce que ces résultats
imposent au produit ; le chiffre à citer est celui du rapport, jamais celui de ce tableau.

### Résultats positifs, non recomptés

| Résultat | Mesure | Source |
|---|---|---|
| Dépôt DPE → mutation à 12 mois | 35,1 à 35,7 % contre 3,03 % ; lift × 11,8 ; 2023 : 34,2 % | `dpe-signal-vente-35.md`, `pistes-analyse-marche-35.md` §5.1 |
| Délai dépôt → acte | médiane 169 jours, Q1 113, Q3 282 | idem |
| Courbe de conversion | 2 % à 3 mois, 20 % à 6 mois, 35 % à 12 mois, 43 % à 24 mois | idem |
| Par étiquette | courbe en U : F et G convertissent 40 % de plus que C et D | idem |
| Plus-value nette par prix d'entrée | × 1,90 sous 60 % du marché, × 1,23 entre 60 et 80 %, × 1,01 au prix | §5.2 |
| Décote énergétique, maisons | 3 à 4 % pour E et F, invisible pour G (202 ventes) | §5.2 |
| Extension de surface | ratio prix total × 1,37, prix au m² × 1,00 (205 paires) | §5.2 |

### Résultats négatifs, établis

| Résultat | Mesure | Source |
|---|---|---|
| Adresse ↔ parcelle | 24 % d'erreur, irréductible par containment, proximité ou distance | `spatial-matching-manual-review-35.md` |
| Bâtiment ↔ parcelle | 37 % d'erreur avant BUG-09 ; 400 706 relations sur 1,24 M à recouvrement < 10 % | idem |
| Unité foncière | une par parcelle ; la contiguïté donne des grappes de 3 494 parcelles ; aucun signal autorisé ne réunit le cas 90, l'adresse commune est corroborée par les ventes à 92,8 % mais ne couvre que 3,1 % des parcelles | `property-unit-35.md` |
| DPE rattaché au bâtiment | 59 % ; 10 % non rattachés | `dpe-matching-35.md` |
| DVF sans prix allouable | 55,0 % des mutations 2021-2025, en version 5 (65,5 % publiés avant H7) | `dvf-quality-35.md` |
| Zone inondable typée | aucune source sur le 35 | `georisques-coverage-35.md` |
| Profils de règles d'urbanisme | zéro ; D2b estimé à quatre années-personne à l'échelle nationale | `gpu-coverage-35.md` |
| Usage du bâti par morphologie seule | 2 candidats d'intérêt sur 10 | `docs/backlog/E8b` |

## Ce qui fonde le produit actif

- [Le dépôt d'un DPE comme signal de mise en vente](./dpe-signal-vente-35.md) — lift × 11,8, non recompté
- [Pistes d'analyse du marché du 35](./pistes-analyse-marche-35.md) — marge par prix d'entrée, décote énergétique, sondages non recomptés
- [Qualité DVF](./dvf-quality-35.md) et [vérification](./dvf-verification-35.md)
- [Appariement DPE](./dpe-matching-35.md) et [vérification](./dpe-verification-35.md)
- [Appariement des DPE de logements neufs](./dpe-neuf-matching-35.md) — DS-13, affichés, hors mesures, recompté le 2026-09-16
- [Qualité, couverture et fraîcheur métier par commune](./market-data-quality-35.md)
- [Sonde : un signal d'abandon dans l'open data ?](./sonde-abandon-35.md) — non, sondage non recompté

## Référentiel spatial

- [DS-01 — Cadastre](./DS-01-acceptance.md)
- [Audit DS-02 à DS-05](./spatial-sources-audit.md)
- [Revue manuelle des appariements](./spatial-matching-manual-review-35.md) — 24 % et 37 % d'erreur, résultats négatifs
- [Rapport spatial 35](./spatial-reference-35-report.md), [bâtiments physiques](./physical-buildings-35.md)

## Listes exploratoires et kit terrain

- [Candidats divisibles, Cesson-Sévigné](./exploratory-candidates-35051.md)
- [Biens probablement en vente, Cesson-Sévigné](./biens-en-vente-35051.md)
- `field-test-35/` — fiches et grilles pour une session de revue

## Plateforme gelée

- [Scoring v0.6](./scoring-v0.6-report.md), [MVP connecté v0.7](./connected-mvp-v0.7-report.md), [pilote v0.8](./brittany-pilot-v0.8-report.md), [performance carte](./real-map-performance.md), [opérations pilote](./pilot-operations-v0.8-report.md)
- [Traçabilité de la DoD MVP](./mvp-dod-traceability.md) — instantané d'une DoD remplacée par ADR-016

## Audit

- [Audit critique du 15 septembre 2026](../audit-critique-2026-09-15.md)
