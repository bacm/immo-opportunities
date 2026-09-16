# Backlog d'exécution

**Périmètre :** ce qu'il reste à faire pour livrer le produit décidé par
[ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md) — le baromètre du 35, puis
le radar de mise en vente — et ce qui est gelé avec la plateforme.

Ce dossier est un **plan d'exécution**, pas une source de vérité produit. L'ordre des sources :
`SPEC.md` → `ARCHITECTURE.md` → [`docs/decisions/`](../decisions/) → [`contracts/`](../../contracts/) →
[`docs/data/`](../data/).

## Verdict d'état — 15 septembre 2026

Le logiciel est écrit. Personne ne l'a vu. L'audit du 15 septembre
([`docs/audit-critique-2026-09-15.md`](../audit-critique-2026-09-15.md)) établit que la
définition initiale n'est pas tenable avec les données autorisées, et
[ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md) redéfinit le produit.

| Constat | Preuve |
|---|---|
| Référentiel spatial 35 accepté : DS-01, DS-02 ; DS-03 à DS-09 importés en `display_only` | [audit spatial](../data/spatial-sources-audit.md), [qualité métier](../data/market-data-quality-35.md) |
| Signal DPE → vente, lift × 11,8, non recompté | [`dpe-signal-vente-35.md`](../data/dpe-signal-vente-35.md) |
| Marge de revente par prix d'entrée, décote énergétique 3-4 %, non recomptés | [`pistes-analyse-marche-35.md`](../data/pistes-analyse-marche-35.md) §5 |
| Moteur de score sans appelant, aucun `OpportunitySnapshot`, aucun utilisateur, aucun entretien | [audit](../audit-critique-2026-09-15.md) §0, §7 |

Le dépôt ne versionne pas l'état de la base. La séquence qui rétablit le référentiel est dans
[`docs/operations/referentiel-local-35.md`](../operations/referentiel-local-35.md) — elle ne
couvre que quatre datasets sur neuf et doit être complétée avant toute reconstitution.

## Chemin critique — ADR-016, 15 septembre 2026

> Produire le baromètre du 35, le mettre entre les mains de cinq professionnels, obtenir un avis
> juridique, puis lancer le radar.

```text
A7 ──► H1 ──► H2 ──► H3 ──┬──► H5 radar (H4 avis juridique en parallèle, requis)
                          └──► H6 SPEC.md réécrit
```

| | |
|---|---|
| [H1](./H1-barometre-marche-35-mesures.md) | les mesures du baromètre, reproductibles et recomptées |
| [H2](./H2-barometre-document-publiable.md) | un document publiable par EPCI, hors plateforme |
| [H3](./H3-entretiens-professionnels-barometre.md) | cinq professionnels, le prix du baromètre et celui du radar — **verrou humain** |
| [H4](./H4-avis-juridique-donnees.md) | avis juridique écrit, préalable au radar — **verrou humain** |
| [H5](./H5-radar-mise-en-vente.md) | le radar hebdomadaire de mise en vente |
| [H6](./H6-reecrire-spec.md) | `SPEC.md` réécrit après le premier retour client |

**Tout le reste est gelé**, pas abandonné : D6, E1 à E7, F1 à F3, G1 à G8, BUG-02, BUG-08,
BUG-11, BUG-13, D7, A6, G6, G7 restent dans le tableau avec leur disponibilité dérivée, mais
aucun ne se prend avant le verdict de H3. E9 reste disponible pour être joint aux entretiens de
H3, à condition de corriger son protocole (aveugle cassé sur la liste E8f, audit §3.4).

## Questions ouvertes

Elles n'empêchent ni H1 ni H2 ; elles conditionnent H5 et la suite. `SPEC.md` §25 renvoie ici.

| Question | Répond |
|---|---|
| Que sait déjà un marchand de biens du 35 de sa marge et de ses délais ? (HB1) | H3 |
| Le goulot du métier est-il trouver, acheter au bon prix, ou obtenir l'autorisation ? (HP) | H3 |
| Combien de lignes par semaine un agent ou un marchand veut-il recevoir, et pour quel secteur ? | H3 |
| Quel canal : courriel, PDF, CSV, page ? | H3 |
| Le même radar est-il vendu à plusieurs professionnels d'un même secteur, ou exclusif ? | H3 |
| Que vaut légalement l'adresse dans le radar ? | H4 |
| Existe-t-il quelques centaines de cibles personnes morales sur le 35 ? | V3, à sonder par ADR |
| Une DP de division suit-elle réellement les parcelles jugées divisibles ? | V1, Sitadel, par ADR |

## Tickets

Ce tableau est **généré** par `make backlog` depuis l'en-tête de chaque ticket. Ne pas l'éditer à
la main : l'état d'un ticket se change dans son propre fichier, la colonne « Disponibilité » est
dérivée du graphe de dépendances.

<!-- BEGIN:tickets -->

### A — Clôture process

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [A1](./A1-preuve-ci-github.md) | Exécuter le workflow CI sur GitHub et attacher la preuve | v0.1 | — | S | Terminé | — |
| [A10](./A10-spec-sans-etat-ni-historique.md) | `SPEC.md` ne porte ni état réel, ni résultat mesuré, ni décision : une règle de propriété et son application | transverse | A9 | M | Terminé | — |
| [A2](./A2-readme-versions-conforme.md) | Une seule version « En cours » dans le suivi | transverse | — | S | Terminé | — |
| [A3](./A3-boucle-autonome-verrous.md) | Verrous humains et invariants de la boucle de développement | transverse | — | M | Terminé | — |
| [A4](./A4-decisions-hors-architecture.md) | Les décisions sortent d'ARCHITECTURE.md, qui reste un document de référence | transverse | — | S | Terminé | — |
| [A5](./A5-toute-modification-passe-par-un-ticket.md) | Toute modification du code passe par un ticket | transverse | — | S | Terminé | — |
| [A6](./A6-demo-sous-ensemble-vps.md) | Démo déployable : un sous-ensemble de communes sur une petite machine | transverse | — | L | À faire | **prêt** |
| [A7](./A7-ouvrir-la-serie-h.md) | Ouvrir la série H dans les outils du backlog, et aligner les documents de pilotage sur ADR-016 | transverse | — | S | Terminé | — |
| [A8](./A8-condenser-claude-md.md) | Condenser `CLAUDE.md` sans perdre une consigne | transverse | — | S | Terminé | — |
| [A9](./A9-claude-md-routage.md) | `CLAUDE.md` devient un document de routage et de méthode, sans état ni décision | transverse | A8 | S | Terminé | — |

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
| [BUG-14](./BUG-14-import-gpu-sans-trace.md) | Deux imports métier ne laissent aucune trace, et le calcul URB ne vérifie aucun verdict | v0.5 | — | M | Terminé | — |
| [BUG-15](./BUG-15-collision-identifiants-tickets.md) | Deux fichiers pour un identifiant : un ticket disparaît du tableau sans bruit | dette transverse | — | S | Terminé | — |
| [BUG-16](./BUG-16-suffixes-de-tickets-limites.md) | Un ticket suffixé au-delà de `b` est invisible des contrôles, sans bruit | dette transverse | — | S | Terminé | — |

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
| [D6b](./D6b-verification-diagnostics-parcelle.md) | Voir les diagnostics d'une parcelle, pour vérifier que l'appariement DPE tient | v0.5 | D4 | S | Terminé | — |
| [D7](./D7-sources-territoriales.md) | DS-10 population et DS-11 équipements : les variables qui séparent les marchés | v0.5 | D1 | L | À faire | **prêt** |
| [D8](./D8-historique-dvf-2014.md) | Remonter l'historique DVF à 2014, depuis les publications DGFiP archivées | v0.5 | D1 | L | Terminé | — |

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
| [E8](./E8-liste-exploratoire-terrain.md) | Produire une liste exploratoire de candidats, confrontable à un professionnel | v0.6 | — | M | Terminé | — |
| [E8b](./E8b-usage-du-bati.md) | Distinguer l'usage du bâti, faute de quoi la liste sélectionne des routes et des espaces verts | v0.6 | E8 | M | Terminé | — |
| [E8c](./E8c-divisibilite-geometrique.md) | Mesurer la divisibilité par la forme du terrain libre, pas par sa surface | v0.6 | E8b | M | Terminé | — |
| [E8d](./E8d-seuils-parametrables.md) | Supprimer le plancher de surface et exposer les seuils, à commencer par la largeur du lot | v0.6 | E8c | S | Terminé | — |
| [E8e](./E8e-age-du-bati.md) | L'âge du bâti pèse plus que son implantation, et il manquait au classement | v0.6 | E8d | S | Terminé | — |
| [E8f](./E8f-liste-biens-en-vente.md) | Une seconde liste : les biens probablement en vente, pour que E9 teste deux promesses | v0.6 | E8e | M | Terminé | — |
| [E8g](./E8g-rang-observe-liste-en-vente.md) | Porter dans la liste des biens en vente ce que la courbe de conversion, l'étiquette et la commune disent déjà | v0.6 | E8f | S | Terminé | — |
| [E8h](./E8h-kit-de-session-terrain.md) | Rendre les deux listes présentables : localiser chaque bien, et donner de quoi saisir les verdicts | v0.6 | E8g | M | Terminé | — |
| [E8i](./E8i-exclure-les-zac.md) | Écarter les parcelles en ZAC de la liste de divisibilité, et montrer la signature d'un aménageur | v0.6 | E8h | S | Terminé | — |
| [E9](./E9-test-terrain-deux-professionnels.md) | Confronter la liste à deux professionnels, et mesurer H1, H2 et H5 | v0.6 | E8, E8f, E8g, E8h, E8i | M | À faire | **verrou humain** |

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

### H — Intelligence de marché, puis radar (ADR-016)

| ID | Titre | Version | Dépend de | Taille | État | Disponibilité |
|---|---|---|---|---|---|---|
| [H1](./H1-barometre-marche-35-mesures.md) | Baromètre du marché du 35 : les mesures, reproductibles et recomptées | V5 | A7 | L | Terminé | — |
| [H2](./H2-barometre-document-publiable.md) | Mettre en forme le baromètre : un document publiable par EPCI, hors plateforme | V5 | H1 | M | À faire | **prêt** |
| [H3](./H3-entretiens-professionnels-barometre.md) | Présenter le baromètre à cinq professionnels, et recueillir ce qu'ils paieraient | V5 | H2 | M | À faire | attend H2 |
| [H4](./H4-avis-juridique-donnees.md) | Obtenir un avis juridique écrit sur l'usage des données, préalable au radar | V2 | A7 | S | À faire | **verrou humain** |
| [H5](./H5-radar-mise-en-vente.md) | Radar de mise en vente : un flux hebdomadaire des DPE fraîchement déposés, par secteur | V2 | H3, H4 | L | À faire | attend H3, H4 |
| [H6](./H6-reecrire-spec.md) | Réviser toute la documentation de référence autour d'ADR-016 | transverse | A7 | L | Terminé | — |

**49/81 terminés.** Prêts à démarrer : A6, BUG-02, BUG-08, BUG-11, BUG-13, D7, G6, G7, H2.

### Verrous humains

Ces tickets ne dépendent plus de rien et ne sont pourtant pas à prendre : leur verdict porte sur l'exactitude dans le monde réel ou sur un arbitrage produit. Une boucle de développement s'y arrête et rend la main.

- **D6** — revue humaine · preuve attendue : `docs/data/market-data-manual-review-35.md`
- **E9** — revue humaine · preuve attendue : `docs/data/field-test-results-35.md`
- **H4** — décision humaine · preuve attendue : `docs/decisions/avis-juridique-donnees-2026.md`

### Lots menables de front

Dérivé des chemins déclarés par `**Touche :**`. Deux tickets d'un même lot n'écrivent pas dans les mêmes fichiers ; un ticket sans `Touche` déclaré est supposé entrer en conflit avec tout le monde.

1. A6, BUG-02, BUG-08, D7, G6, H2
2. BUG-11, G7
3. BUG-13

<!-- END:tickets -->

### NICE — après un score publié

Rien ci-dessous ne démarre avant E3. Détail dans [NICE-backlog.md](./NICE-backlog.md).