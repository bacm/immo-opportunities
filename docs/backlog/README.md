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

## Chemin critique — révisé le 15 septembre 2026

> Montrer une liste à un professionnel avant de construire quoi que ce soit d'autre.

Le chemin précédent — *débloquer BAN, importer DVF+, profiler, publier un premier score* — est
**parcouru jusqu'à D5** : les quatre sources métier sont importées et mesurées. Il reste valable
techniquement, et c'est précisément ce qui pose problème : il place la seule validation qui compte,
[G8](./G8-pilote-trois-professionnels.md), derrière onze tickets dont une extension XL à trois
départements. H1 à H5 ne sont mesurées nulle part, et `SPEC.md` §25 demande encore quel est le
volume de travail hebdomadaire du premier marchand de biens.

La base contient pourtant déjà de quoi répondre : 1 333 327 unités, 20 M de valeurs de features,
133 066 mutations, 21 136 zones d'urbanisme. Une sonde sur Cesson-Sévigné ramène 679 candidats
plausibles sur 9 329 unités.

```text
E8 ──► E9 ──┬──► poursuivre : D6 ──► E1 ──► E2 ──► E3 ──► F1 ──► G*
            ├──► recadrer : périmètre produit amendé, puis reprise
            └──► arrêter : G9
```

Deux tickets seulement, et le second est un verrou humain :

| | |
|---|---|
| [E8](./E8-liste-exploratoire-terrain.md) | une liste exploratoire et sa baseline, sur une commune, sans rien publier |
| [E9](./E9-test-terrain-deux-professionnels.md) | deux professionnels, en aveugle, H1 · H2 · H5 |

Le reste du backlog n'est pas annulé : il est **suspendu à un verdict**. Les tickets de dette
sans lien avec la promesse produit ([BUG-02](./BUG-02-scripts-import-hors-dagster.md),
[BUG-08](./BUG-08-cycle-de-vie-des-releases-remplacees.md), [G6](./G6-exploitation-restauration.md),
[G7](./G7-observabilite-minimale.md)) restent menables, mais ne sont plus prioritaires.

[BUG-11](./BUG-11-unite-fonciere-degeneree.md) mérite une mention à part. Il est classé bug de
résolution d'entités ; c'est en réalité la question de savoir si l'objet que le produit vend — un
bien — est constructible avec les données autorisées. Le propriétaire est hors périmètre par
décision, et la contiguïté est mesurée puis disqualifiée. E9 est le moyen le moins cher de savoir
si cette limite est rédhibitoire ou seulement gênante : le relecteur du cas 90 l'avait signalée
spontanément, sans connaître le modèle.

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
| [A1](./A1-preuve-ci-github.md) | Exécuter le workflow CI sur GitHub et attacher la preuve | v0.1 | — | S | Terminé | — |
| [A2](./A2-readme-versions-conforme.md) | Une seule version « En cours » dans le suivi | transverse | — | S | Terminé | — |
| [A3](./A3-boucle-autonome-verrous.md) | Verrous humains et invariants de la boucle de développement | transverse | — | M | Terminé | — |
| [A4](./A4-decisions-hors-architecture.md) | Les décisions sortent d'ARCHITECTURE.md, qui reste un document de référence | transverse | — | S | Terminé | — |
| [A5](./A5-toute-modification-passe-par-un-ticket.md) | Toute modification du code passe par un ticket | transverse | — | S | Terminé | — |
| [A6](./A6-demo-sous-ensemble-vps.md) | Démo déployable : un sous-ensemble de communes sur une petite machine | transverse | — | L | À faire | **prêt** |

### B — v0.3 Référentiel spatial 35

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [B1](./B1-audit-ban-ds05.md) | Terminer l'audit BAN DS-05 et prononcer un verdict | v0.3 | BUG-03 | M | Terminé | — |
| [B2a](./B2a-import-bdnb-ds03.md) | Importer et auditer DS-03 BDNB Open sur le 35 | v0.3 | — | L | Terminé | — |
| [B2b](./B2b-import-bdtopo-ds04.md) | Importer et auditer DS-04 BD TOPO sur le 35 | v0.3 | BUG-05 | L | Terminé | — |
| [B3](./B3-rapport-appariements.md) | Rapport de distribution et métriques d'appariement par commune | v0.3 | B1, B2a, B2b | M | Terminé | — |
| [B4](./B4-revue-manuelle-appariements.md) | Revue manuelle stratifiée d'un échantillon d'appariements | v0.3 | B3 | M | Terminé | — |
| [B5](./B5-features-morphologiques.md) | Calculer LAND-001..010 et BLD-001..003 sur releases acceptées | v0.3 | B4 | M | Terminé | — |

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
| [BUG-08](./BUG-08-cycle-de-vie-des-releases-remplacees.md) | Une release remplacée n'est jamais retirée | dette transverse | — | M | À faire | **prêt** |
| [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md) | Un tiers des relations bâtiment ↔ parcelle sont des contacts marginaux déclarés certains | v0.3 | — | M | Terminé | — |
| [BUG-10](./BUG-10-aucun-compte-utilisateur.md) | Personne ne peut se connecter : ni compte, ni inscription, ni administrateur | v0.7 | — | M | Terminé | — |
| [BUG-11](./BUG-11-unite-fonciere-degeneree.md) | L'unité analysée par le moteur est une parcelle isolée, et la contiguïté ne peut pas y suppléer | v0.6 | D1 | L | À faire | **prêt** |
| [BUG-12](./BUG-12-deduplication-batiments-physiques.md) | Compter des enregistrements n'est pas compter des bâtiments | v0.3 | — | M | Terminé | — |
| [BUG-13](./BUG-13-sujet-des-features-batiment.md) | Une feature de bâtiment ne peut se poser que sur un enregistrement, pas sur un bâtiment | dette transverse | — | M | À faire | **prêt** |
| [BUG-14](./BUG-14-import-gpu-sans-trace.md) | Deux imports métier ne laissent aucune trace, et le calcul URB ne vérifie aucun verdict | v0.5 | — | M | En cours | en cours |
| [BUG-15](./BUG-15-collision-identifiants-tickets.md) | Deux fichiers pour un identifiant : un ticket disparaît du tableau sans bruit | dette transverse | — | S | Terminé | — |

### C — v0.4 Carte réelle

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [C1](./C1-recherche-adresse-reelle.md) | Recherche adresse réelle FR-001 sur données BAN acceptées | v0.4 | B1 | M | Terminé | — |
| [C2](./C2-zone-non-couverte.md) | Distinguer zone non couverte et zone sans résultat | v0.4 | C1 | S | Terminé | — |
| [C3](./C3-capture-demo-adresse.md) | Capture de démonstration adresse 35 | v0.4 | C1, C2 | S | Terminé | — |

### D — v0.5 Données métier 35

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [D1](./D1-import-dvf-ds06.md) | DS-06 DVF+ : archive, import relançable, comparables explicables | v0.5 | B5 | XL | Terminé | — |
| [D2](./D2-import-gpu-ds08.md) | DS-08 GPU : zonage et contraintes, sans interprétation de règlement | v0.5 | D1 | M | Terminé | — |
| [D2b](./D2b-profils-de-regles.md) | Profils de règles d'urbanisme, là où un candidat le justifie | v0.6 | D2, E3 | L | À faire | attend E3 |
| [D3](./D3-import-georisques-ds09.md) | DS-09 Géorisques : granularité conservée | v0.5 | D1 | L | Terminé | — |
| [D4](./D4-import-dpe-ds07.md) | DS-07 DPE : diagnostics réellement déposés | v0.5 | D1 | L | Terminé | — |
| [D5](./D5-rapports-qualite-metier.md) | Rapports qualité, couverture et fraîcheur par commune | v0.5 | D1, D2, D3, D4 | M | Terminé | — |
| [D6](./D6-revue-manuelle-metier.md) | Revue manuelle stratifiée comparables / GPU / DPE / risques | v0.5 | D5 | M | À faire | **verrou humain** |
| [D6a](./D6a-verification-mutations-parcelle.md) | Voir les mutations d'une parcelle, pour vérifier que DVF tient | v0.5 | D1 | S | Terminé | — |
| [D6b](./D6b-verification-diagnostics-parcelle.md) | Voir les diagnostics d'une parcelle, pour vérifier que l'appariement DPE tient | v0.5 | D4 | S | En cours | en cours |
| [D7](./D7-sources-territoriales.md) | DS-10 population et DS-11 équipements : les variables qui séparent les marchés | v0.5 | D1 | L | À faire | **prêt** |

### E — v0.6 Scoring

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [E1](./E1-profiling-distributions.md) | Profiler les distributions réelles du 35 et figer les transformations | v0.6 | D6 | L | À faire | attend D6 |
| [E2](./E2-publication-eligible.md) | Passer les deux définitions en `publication_eligible` | v0.6 | E1 | M | À faire | attend E1 |
| [E3](./E3-publier-snapshots.md) | Publier des `OpportunitySnapshot` immuables | v0.6 | E2 | M | À faire | attend E2 |
| [E4](./E4-backtest-baseline.md) | Backtest régional contre baseline cadastrale | v0.6 | E3 | L | À faire | attend E3 |
| [E5](./E5-resultats-par-segment.md) | Résultats par segment urbain / périurbain / littoral / rural | v0.6 | E4 | M | À faire | attend E4 |
| [E6](./E6-segmentation-observee.md) | Segmenter les marchés sur distribution observée, et mesurer ce que ça change | v0.6 | D7, E1 | M | À faire | attend D7, E1 |
| [E7](./E7-decision-valorisation.md) | Décider si le produit estime la valeur des biens non vendus | v0.6 | E6 | M | À faire | attend E6 |
| [E8](./E8-liste-exploratoire-terrain.md) | Produire une liste exploratoire de candidats, confrontable à un professionnel | v0.6 | — | M | À faire | **prêt** |
| [E9](./E9-test-terrain-deux-professionnels.md) | Confronter la liste à deux professionnels, et mesurer H1, H2 et H5 | v0.6 | E8 | M | À faire | attend E8 |

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

**30/61 terminés.** Prêts à démarrer : A6, BUG-02, BUG-08, BUG-11, BUG-13, D7, E8, G6, G7.

### Verrous humains

Ces tickets ne dépendent plus de rien et ne sont pourtant pas à prendre : leur verdict porte sur l'exactitude dans le monde réel ou sur un arbitrage produit. Une boucle de développement s'y arrête et rend la main.

- **D6** — revue humaine · preuve attendue : `docs/data/market-data-manual-review-35.md`

### Déjà démarré

Ces tickets occupent leurs chemins : ne pas y lancer un second travail. L'état vit dans la ligne `**État :**` de chaque fichier, source unique.

- **BUG-14** — pipelines/scripts/import_gpu_release.py, pipelines/scripts/import_dvf_release.py, pipelines/scripts/compute_urban_features.py
- **D6b** — backend/src/immo/explorer.py, backend/src/immo/api/routes/explorer.py, apps/web/src/App.tsx, docs/data/dpe-verification-35.md

### Lots menables de front

Dérivé des chemins déclarés par `**Touche :**`. Deux tickets d'un même lot n'écrivent pas dans les mêmes fichiers ; un ticket sans `Touche` déclaré est supposé entrer en conflit avec tout le monde.

1. A6, BUG-02, BUG-08, D7, E8, G6
2. BUG-11, G7
3. BUG-13

<!-- END:tickets -->

### NICE — après un score publié

Rien ci-dessous ne démarre avant E3. Détail dans [NICE-backlog.md](./NICE-backlog.md).