# Immo Opportunities

Monorepo B2B de détection et qualification de candidats immobiliers off-market en Bretagne
(22, 29, 35, 56).

Le produit aide un **marchand de biens ou investisseur-rénovateur** à classer des actifs à
approfondir selon deux stratégies : division/extension et rénovation-revente.

Ce n'est **pas** une prédiction de vente, **pas** une détection de vacance, **pas** une décision
urbanistique opposable.

**Répondre et documenter en français.**

## État au 13 septembre 2026

Le logiciel MVP est largement écrit — API, Explorer carte/liste/fiche, OIDC, RLS, moteur de score,
administration. **La DoD produit n'est pas atteinte, et le goulot est la donnée réelle, pas l'UI.**

| Version | État |
|---|---|
| v0.1 Foundation | Bloquée — preuve CI GitHub manquante |
| v0.2 Cadastre 35 | Terminée |
| v0.3 Référentiel spatial | Terminée le 13 septembre 2026 |
| **v0.4 Carte réelle** | **En cours — seule version active** |
| v0.5 → v0.8 | En attente |

**Deux releases acceptées** sur le 35 : DS-01 Cadastre et DS-02 RNB. DS-03 BDNB, DS-04 BD TOPO et
DS-05 BAN sont `display_only`. DS-06 à DS-09 : contrats seulement, aucun import réel.

v0.6 : moteur reproductible, définitions en `publication_eligible: false`.
v0.7 : entièrement codé, inutilisable faute de candidats publiés.

### Ce que v0.3 a livré, et ce qu'elle a laissé

Features morphologiques matérialisées sur **1 333 327 unités** — `LAND-001..007` et `LAND-009`
calculées, `LAND-008`, `LAND-010` et `BLD-001..003` absentes avec motif. Bâtiments regroupés en
**514 859 bâtiments physiques** côté RNB, 517 615 côté cadastre.

La revue manuelle B4 a produit une acceptation — l'identité BD TOPO ↔ RNB, 60 cas sur 60 — et
**trois défauts structurels qu'aucun contrôle automatique n'avait vus**, tous corrigés : BUG-09
(1,24 M de relations bâtiment ↔ parcelle toutes déclarées certaines), BUG-10 (personne ne pouvait
se connecter), BUG-12 (comptage d'enregistrements, faux de 44 %).

Elle a aussi établi un **résultat négatif** à ne pas redécouvrir : la relation adresse ↔ parcelle
n'est vérifiable par aucune règle géométrique — ni containment, ni proximité, ni distance. Son
taux d'erreur d'environ 24 % est réel et irréductible avec les sources disponibles.

### Le chemin critique tient en une phrase

> Importer DVF+, profiler les distributions réelles, publier un premier score. v0.7 est déjà
> écrit et n'attend que des candidats.

Si on demande « le plus important maintenant » : **D1, l'import DVF+ sur le 35.** Sans
transactions, pas de comparables, pas de valorisation, et le classement n'a rien à classer.

## Carte du contexte — à lire avant de charger quoi que ce soit

`SPEC.md` (67 Ko) et `ARCHITECTURE.md` (41 Ko) coûtent ~27 000 tokens à eux deux.
**Ne pas les charger par défaut.**

| Tâche | Charger |
|---|---|
| Implémenter un ticket | [`docs/backlog/<ID>-*.md`](docs/backlog/) — son bloc « Contexte à charger » liste les 3 à 5 fichiers nécessaires. Rien d'autre. |
| Savoir quoi faire ensuite | [`docs/backlog/README.md`](docs/backlog/README.md), colonne « Disponibilité » |
| Vérifier ce qui est prouvé | [`docs/data/mvp-dod-traceability.md`](docs/data/mvp-dod-traceability.md) |
| Périmètre produit, FR-*, DS-* | `SPEC.md` — **la section concernée seulement** |
| Choix technique, ADR, interdits | `ARCHITECTURE.md` — **la section concernée seulement** |

Sources de vérité, dans cet ordre : `SPEC.md` → `ARCHITECTURE.md` → `docs/versions/` →
`contracts/` → `docs/data/mvp-dod-traceability.md`.

## Règles non négociables

- Une valeur manquante **reste manquante avec un motif**. Jamais convertie en zéro.
- **Aucun seuil territorial inventé.** Les percentiles et profils viennent du profiling observé.
- Snapshots de score **immuables**. La publication déplace un pointeur, elle ne réécrit pas
  l'historique.
- **Pas d'alias `latest`** pour un import reproductible. Checksum SHA-256 avant import.
- Pipelines via **Dagster** (assets, partitions dataset × release × département). Les scripts
  d'import sont une dette à résorber, pas le chemin cible.
- Martin / tuiles : **attributs de rendu seulement**. Notes, statuts, scénarios passent par l'API
  privée sous RLS.
- **Données simulées interdites** pour satisfaire un critère « données réelles ».
- Anomalie sur un attribut → l'attribut devient manquant avec motif, l'enregistrement est conservé
  (décision BUG-03, réutilisée par D1 à D4).
- **Tout pipeline prévoit la variété de sa source avant son premier lot.** Inventorier sur un
  échantillon dispersé, faire échouer un élément sans faire échouer le lot, distinguer l'échec
  passager du défectueux, temporiser face à un service public. Voir `ARCHITECTURE.md` §10.6.
- **La clé d'idempotence et l'identifiant de run d'un import portent la version de
  transformation.** Sans elle, une release déjà importée est rejouée à vide et un correctif de
  code n'atteint jamais les données — constaté sur BUG-09.

## Interdits techniques

Pas de Celery tant qu'il n'y a ni export ni alerte. Pas de ML en production. Pas de Kubernetes.
Pas de scoring à la requête. Pas de GeoJSON régional dans MapLibre. Pas de secrets en clair.

**Frontend :** `apps/web/src/App.tsx` + CSS custom + MapLibre. Ne pas introduire MUI, TanStack
Query ou Zustand pendant le chemin critique données. Si tu touches le front, reste cohérent avec
l'existant.

## Hors périmètre — ne pas faire

France entière, marketplace, API commerciale publique, scraping de propriétaires, prospection
automatisée, recommandation d'achat autonome, PLU opposable, prédiction certaine de vente ou de
vacance, LOVAC ou données propriétaires sans droit, DPE simulés.

## Ordre d'exécution

```text
v0.1 preuve CI → v0.3 données spatiales 35 → v0.4 adresse réelle → v0.5 imports métier 35
→ profiling → v0.6 publication score → activation v0.7 → v0.8 extension 22/29/56 + pilote
```

Ne pas sauter une étape. **Ne pas enrichir l'UI tant qu'aucun `OpportunitySnapshot` publié
n'existe.** Plusieurs versions peuvent être `En cours` si aucune ne dépend de l'autre — la
contrainte est le graphe de dépendances, pas un décompte.

Les nice-to-have (exports, alertes, collaboration, indice de vacance) ne démarrent pas avant qu'un
top-N réel soit publiable sur le 35 — voir [`docs/backlog/NICE-backlog.md`](docs/backlog/NICE-backlog.md).

## Definition of Done d'une tâche

Terminé **seulement si** :

1. test automatisé ajouté ou étendu ;
2. preuve écrite dans `docs/data/` ou `contracts/` ;
3. `make openapi` régénéré si l'API change ;
4. `make check` vert ;
5. aucune donnée simulée présentée comme réelle ;
6. l'état du ticket est mis à jour **dans son propre fichier**, puis `make backlog` ;
7. les dépendances des tickets que celui-ci débloque sont **relues** : une dépendance qui n'a plus
   d'objet se retire, sans quoi elle allonge le chemin critique indéfiniment.

## Commandes

```bash
make dev                  # infrastructure locale
make rebuild              # reconstruit les images — obligatoire après tout changement backend
make check                # lint, typecheck, tests, OpenAPI
make openapi              # régénère le contrat et le client TypeScript
make migrate              # migrations Alembic
make backlog              # régénère le tableau de suivi depuis les en-têtes de tickets
make ban-import           # import BAN   (voir aussi rnb-import, cadastre-fixture)
make physical-buildings   # regroupe les enregistrements en bâtiments physiques
make morphology-features  # matérialise LAND-*/BLD-* sur les releases acceptées
```

**`make rebuild` recrée PostgreSQL et coupe tout travail en cours.** Un import qui tourne est
interrompu par un `rebuild` lancé pour un autre ticket — la contention entre travaux parallèles ne
porte pas que sur les fichiers. Vérifier qu'aucun import n'est en cours avant de reconstruire.

**Les conteneurs embarquent une copie du code figée au build.** `compose.dev.yaml` ne monte pas
les sources : un changement backend demande `make rebuild`, pas un `docker compose restart`. Et
`docker compose` sans les trois `-f` recrée les conteneurs hors configuration de développement.

## Suivi du backlog

L'état d'un ticket vit **à un seul endroit** : la ligne `**État :**` de son fichier dans
`docs/backlog/`. Valeurs autorisées : `À faire`, `En cours`, `Terminé`, `Abandonné`.

La colonne « Disponibilité » du README est **dérivée** du graphe de dépendances — ne jamais la
saisir à la main. `make backlog` régénère le tableau après tout changement d'état ;
`make backlog-check` signale s'il est périmé. Volontairement **hors de `make check`** : la
cohérence documentaire ne doit pas bloquer la CI de code.

Les fichiers `docs/versions/` et `docs/data/mvp-dod-traceability.md` ne se mettent à jour qu'à la
clôture d'une **version**, pas d'un ticket.

## Sous-agents et parallélisation

- **Oui** pour la recherche en fan-out (« où est implémenté X ») : on garde la conclusion, pas les
  fichiers.
- **Oui** pour les tickets d'un même **lot menable de front** — section générée en bas de
  [`docs/backlog/README.md`](docs/backlog/README.md).
- **Non** sur le chemin critique séquentiel : la continuité y coûte moins cher que la relecture.
- Un sous-agent doit recevoir l'ID du ticket et son bloc « Contexte à charger », sinon il produit
  du hors-sujet.

### « Disponible » ne veut pas dire « parallélisable »

La colonne « Disponibilité » dérive du graphe de dépendances : elle dit ce qui *peut commencer*.
Elle ne dit pas ce qui peut commencer **ensemble** — deux tickets sans lien de dépendance peuvent
très bien écrire dans le même fichier.

D'où le champ `**Touche :**` dans l'en-tête de chaque ticket : les chemins qu'il va **écrire**,
distincts de « Contexte à charger » qui dit ce qu'il faut lire. `make backlog` en dérive :

- les **lots menables de front**, dont les tickets n'ont aucun chemin commun ;
- les tickets **déjà démarrés**, qui occupent leurs chemins ;
- les tickets prêts mais **retenus** par un travail en cours.

Un ticket sans `Touche` déclaré est isolé par précaution et signalé — l'oubli coûte de la
parallélisation, il ne produit pas de collision.

### Deux disciplines sans lesquelles rien de tout cela ne tient

1. **Passer un ticket à `En cours` en le commençant**, pas en le finissant. C'est ce qui réserve
   ses chemins ; un ticket travaillé mais resté `À faire` est invisible et un second agent ira
   écrire au même endroit.
2. **À la clôture d'un ticket, réexaminer ce qu'il débloque.** Une dépendance héritée de l'ordre
   de rédaction survit tant que personne ne la relit — `D3` attendait `D2` pour un module déjà
   livré, `D4` attendait `D3` sans qu'aucune ligne ne le justifie. Les deux allongeaient le chemin
   critique pour rien.
