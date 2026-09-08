# Backlog d'exécution — clôture du MVP

**Date :** 4 septembre 2026
**Périmètre :** ce qu'il reste à faire pour atteindre la Definition of Done du MVP
([`SPEC.md` §26](../../SPEC.md#26-definition-of-done-du-mvp)) et la DoD architecture
([`ARCHITECTURE.md` §25](../../ARCHITECTURE.md#25-definition-of-done-architecture-mvp)).

Ce dossier est un **plan d'exécution**, pas une source de vérité produit. L'ordre des sources reste :
`SPEC.md` → `ARCHITECTURE.md` → [`docs/versions/`](../versions/) → [`contracts/`](../../contracts/) →
[`docs/data/mvp-dod-traceability.md`](../data/mvp-dod-traceability.md).

## Verdict d'état

Le logiciel est écrit. La DoD n'est pas atteinte, et le goulot n'est pas l'interface : c'est
l'absence de **données réelles acceptées** au-delà du cadastre, donc l'absence de tout
`OpportunitySnapshot` publié.

| Constat | Preuve |
|---|---|
| DS-01 Cadastre 35 accepté, 1 333 327 parcelles | [v0.2](../versions/v0.2-cadastre-35.md) |
| DS-02 RNB 35 importé, 741 376 bâtiments, revue manuelle non faite | [rapport spatial 35](../data/spatial-reference-35-report.md) |
| DS-05 BAN 35 archivé et checksumé, acceptation débloquée par la décision du 4 septembre 2026 | [audit spatial](../data/spatial-sources-audit.md), [BUG-03](./BUG-03-quarantaine-par-attribut.md) |
| DS-03, DS-04, DS-06 à DS-09 : contrats seulement, aucune release réelle | [audit spatial](../data/spatial-sources-audit.md), [audit métier](../data/market-data-sources-audit.md) |
| Moteur de score reproductible, définitions en `publication_eligible: false` | [rapport v0.6](../data/scoring-v0.6-report.md) |
| v0.7 entièrement codé, aucun candidat réel à afficher | [rapport v0.7](../data/connected-mvp-v0.7-report.md) |

Le dépôt ne versionne pas l'état de la base : une copie fraîche part d'une base vide. La séquence
qui rétablit l'état sur lequel ces preuves ont été mesurées est dans
[`docs/operations/referentiel-local-35.md`](../operations/referentiel-local-35.md).

## Chemin critique

> Débloquer BAN sur le 35, importer DVF+, profiler les distributions réelles, publier un premier
> score. v0.7 est déjà écrit et n'attend que des candidats.

```text
A1 ──► (preuve CI, hors chemin données)

BUG-03 ──► B1 ──► B3 ──► B4 ──┐
                              ├──► B5 ──► C1 ──► D1 ──► D5 ──► E1 ──► E2 ──► E3 ──► F1 ──► G*
           B2a, B2b ──────────┘                  D2, D3, D4 ┘
```

Aucun ticket des sections `NICE-*` ne démarre tant que E3 (premier top-N réel publiable sur le 35)
n'est pas livré.

## Tickets

Ce tableau est **généré** par `make backlog` depuis l'en-tête de chaque ticket. Ne pas l'éditer à
la main : l'état d'un ticket se change dans son propre fichier, la colonne « Disponibilité » est
dérivée du graphe de dépendances.

<!-- BEGIN:tickets -->

### A — Clôture process

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [A1](./A1-preuve-ci-github.md) | Exécuter le workflow CI sur GitHub et attacher la preuve | v0.1 | — | S | À faire | **prêt** |
| [A2](./A2-readme-versions-conforme.md) | Une seule version « En cours » dans le suivi | transverse | — | S | Terminé | — |

### B — v0.3 Référentiel spatial 35

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [B1](./B1-audit-ban-ds05.md) | Terminer l'audit BAN DS-05 et prononcer un verdict | v0.3 | BUG-03 | M | Terminé | — |
| [B2a](./B2a-import-bdnb-ds03.md) | Importer et auditer DS-03 BDNB Open sur le 35 | v0.3 | — | L | Terminé | — |
| [B2b](./B2b-import-bdtopo-ds04.md) | Importer et auditer DS-04 BD TOPO sur le 35 | v0.3 | BUG-05 | L | Terminé | — |
| [B3](./B3-rapport-appariements.md) | Rapport de distribution et métriques d'appariement par commune | v0.3 | B1, B2a, B2b | M | Terminé | — |
| [B4](./B4-revue-manuelle-appariements.md) | Revue manuelle stratifiée d'un échantillon d'appariements | v0.3 | B3 | M | À faire | **prêt** |
| [B5](./B5-features-morphologiques.md) | Calculer LAND-001..010 et BLD-001..003 sur releases acceptées | v0.3 | B4 | M | À faire | attend B4 |

### Bugs et dette technique

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [BUG-01](./BUG-01-chiffres-audit-ban.md) | Volumétries BAN erronées dans le rapport spatial 35 | v0.3 | — | S | Terminé | — |
| [BUG-02](./BUG-02-scripts-import-hors-dagster.md) | Les imports réels passent par des scripts one-shot, pas par Dagster | dette transverse | — | L | À faire | **prêt** |
| [BUG-03](./BUG-03-quarantaine-par-attribut.md) | Le modèle de quarantaine ne connaît que l'enregistrement, pas l'attribut | v0.3 | — | M | Terminé | — |
| [BUG-04](./BUG-04-propagation-referentiel-spatial.md) | Publier DS-01 ne propage pas le référentiel spatial canonique | v0.3 | — | S | Terminé | — |
| [BUG-05](./BUG-05-ds02-rnb-non-reproductible.md) | DS-02 RNB n'est pas reproductible : l'URL épinglée est un alias mouvant | v0.3 | — | M | Terminé | — |
| [BUG-06](./BUG-06-reglage-postgresql.md) | PostgreSQL tourne avec le `postgresql.conf` d'initdb | dette transverse | — | S | Terminé | — |
| [BUG-07](./BUG-07-tuiles-vides-et-recherche-adresse.md) | L'Explorer ne montre rien : carte vide et recherche d'adresse en erreur | v0.4 | — | M | Terminé | — |

### C — v0.4 Carte réelle

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [C1](./C1-recherche-adresse-reelle.md) | Recherche adresse réelle FR-001 sur données BAN acceptées | v0.4 | B1 | M | Terminé | — |
| [C2](./C2-zone-non-couverte.md) | Distinguer zone non couverte et zone sans résultat | v0.4 | C1 | S | Terminé | — |
| [C3](./C3-capture-demo-adresse.md) | Capture de démonstration adresse 35 | v0.4 | C1, C2 | S | À faire | **prêt** |

### D — v0.5 Données métier 35

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [D1](./D1-import-dvf-ds06.md) | DS-06 DVF+ : archive, import relançable, comparables explicables | v0.5 | B5 | XL | À faire | attend B5 |
| [D2](./D2-import-gpu-ds08.md) | DS-08 GPU : documents, zones et contraintes | v0.5 | D1 | L | À faire | attend D1 |
| [D3](./D3-import-georisques-ds09.md) | DS-09 Géorisques : granularité conservée | v0.5 | D2 | L | À faire | attend D2 |
| [D4](./D4-import-dpe-ds07.md) | DS-07 DPE : diagnostics réellement déposés | v0.5 | D3 | L | À faire | attend D3 |
| [D5](./D5-rapports-qualite-metier.md) | Rapports qualité, couverture et fraîcheur par commune | v0.5 | D1, D2, D3, D4 | M | À faire | attend D1, D2, D3, D4 |
| [D6](./D6-revue-manuelle-metier.md) | Revue manuelle stratifiée comparables / GPU / DPE / risques | v0.5 | D5 | M | À faire | attend D5 |

### E — v0.6 Scoring

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [E1](./E1-profiling-distributions.md) | Profiler les distributions réelles du 35 et figer les transformations | v0.6 | D6 | L | À faire | attend D6 |
| [E2](./E2-publication-eligible.md) | Passer les deux définitions en `publication_eligible` | v0.6 | E1 | M | À faire | attend E1 |
| [E3](./E3-publier-snapshots.md) | Publier des `OpportunitySnapshot` immuables | v0.6 | E2 | M | À faire | attend E2 |
| [E4](./E4-backtest-baseline.md) | Backtest régional contre baseline cadastrale | v0.6 | E3 | L | À faire | attend E3 |
| [E5](./E5-resultats-par-segment.md) | Résultats par segment urbain / périurbain / littoral / rural | v0.6 | E4 | M | À faire | attend E4 |

### F — v0.7 Activation

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [F1](./F1-parcours-reel-sans-fixture.md) | Parcours complet sans fixture sur candidats publiés | v0.7 | E3 | M | À faire | attend E3 |
| [F2](./F2-verification-fr-001-012.md) | Vérifier FR-001 à FR-012 sur candidats réels | v0.7 | F1 | M | À faire | attend F1 |
| [F3](./F3-isolation-organisations.md) | Isolation des organisations en conditions proches production | v0.7 | F1 | M | À faire | attend F1 |

### G — v0.8 Pilote Bretagne

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [G1](./G1-extension-22-29-56.md) | Étendre DS-01 à DS-09 aux départements 22, 29, 56 | v0.8 | F2 | XL | À faire | attend F2 |
| [G2](./G2-matrice-acceptation.md) | Matrice d'acceptation par territoire | v0.8 | G1 | M | À faire | attend G1 |
| [G3](./G3-carte-bretagne.md) | Carte Bretagne entière et zones non publiables signalées | v0.8 | G1 | M | À faire | attend G1 |
| [G4](./G4-couverture-documentee.md) | Couverture documentée département / EPCI / commune | v0.8 | G2 | M | À faire | attend G2 |
| [G5](./G5-administration-bundle.md) | Administration : import-runs, qualité, publication et rollback régional | v0.8 | G2 | M | À faire | attend G2 |
| [G6](./G6-exploitation-restauration.md) | Backup, réplication et restauration chronométrée sur VPS vierge | v0.8 | — | L | À faire | **prêt** |
| [G7](./G7-observabilite-minimale.md) | Observabilité minimale mesurable | v0.8 | — | M | À faire | **prêt** |
| [G8](./G8-pilote-trois-professionnels.md) | Trois professionnels sur cas réels, dataset `CandidateReview`, H1–H5 | v0.8 | G3, G4 | XL | À faire | attend G3, G4 |
| [G9](./G9-decision-finale.md) | Décision documentée : poursuivre / pivoter / arrêter | v0.8 | G8 | S | À faire | attend G8 |

**13/41 terminés.** Prêts à démarrer : A1, B4, BUG-02, C3, G6, G7.

<!-- END:tickets -->

### NICE — après un score publié

Rien ci-dessous ne démarre avant E3. Détail dans [NICE-backlog.md](./NICE-backlog.md).

