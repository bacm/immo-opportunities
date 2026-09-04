# Immo Opportunities

Monorepo B2B de détection et qualification de candidats immobiliers off-market en Bretagne
(22, 29, 35, 56).

Le produit aide un **marchand de biens ou investisseur-rénovateur** à classer des actifs à
approfondir selon deux stratégies : division/extension et rénovation-revente.

Ce n'est **pas** une prédiction de vente, **pas** une détection de vacance, **pas** une décision
urbanistique opposable.

**Répondre et documenter en français.**

## État au 4 septembre 2026

Le logiciel MVP est largement écrit — API, Explorer carte/liste/fiche, OIDC, RLS, moteur de score,
administration. **La DoD produit n'est pas atteinte, et le goulot est la donnée réelle, pas l'UI.**

| Version | État |
|---|---|
| v0.1 Foundation | Bloquée — preuve CI GitHub manquante |
| v0.2 Cadastre 35 | Terminée — 1,3 M parcelles |
| **v0.3 Référentiel spatial** | **En cours — seule version active** |
| v0.4 → v0.8 | Bloquées en cascade |

DS-01 accepté (35). DS-02 RNB chargé (35). DS-05 BAN archivé, acceptation débloquée par BUG-03.
DS-03, DS-04, DS-06 à DS-09 : contrats seulement, aucun import réel.
v0.6 : moteur reproductible, définitions en `publication_eligible: false`.
v0.7 : entièrement codé, inutilisable faute de candidats publiés.

### Le chemin critique tient en une phrase

> Débloquer BAN sur le 35, importer DVF+, profiler les distributions réelles, publier un premier
> score. v0.7 est déjà écrit et n'attend que des candidats.

Si on demande « le plus important maintenant » : **BAN + DVF+ sur le 35, puis profiling, puis un
premier score publié.** Tout le reste attend.

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
n'existe.** Une seule version peut être `En cours`.

Les nice-to-have (exports, alertes, collaboration, indice de vacance) ne démarrent pas avant qu'un
top-N réel soit publiable sur le 35 — voir [`docs/backlog/NICE-backlog.md`](docs/backlog/NICE-backlog.md).

## Definition of Done d'une tâche

Terminé **seulement si** :

1. test automatisé ajouté ou étendu ;
2. preuve écrite dans `docs/data/` ou `contracts/` ;
3. `make openapi` régénéré si l'API change ;
4. `make check` vert ;
5. aucune donnée simulée présentée comme réelle ;
6. l'état du ticket est mis à jour **dans son propre fichier**, puis `make backlog`.

## Commandes

```bash
make dev            # infrastructure locale
make check          # lint, typecheck, tests, OpenAPI
make openapi        # régénère le contrat et le client TypeScript
make migrate        # migrations Alembic
make backlog        # régénère le tableau de suivi depuis les en-têtes de tickets
make ban-import     # import BAN   (voir aussi rnb-import, cadastre-fixture)
```

## Suivi du backlog

L'état d'un ticket vit **à un seul endroit** : la ligne `**État :**` de son fichier dans
`docs/backlog/`. Valeurs autorisées : `À faire`, `En cours`, `Terminé`, `Abandonné`.

La colonne « Disponibilité » du README est **dérivée** du graphe de dépendances — ne jamais la
saisir à la main. `make backlog` régénère le tableau après tout changement d'état ;
`make backlog-check` signale s'il est périmé. Volontairement **hors de `make check`** : la
cohérence documentaire ne doit pas bloquer la CI de code.

Les fichiers `docs/versions/` et `docs/data/mvp-dod-traceability.md` ne se mettent à jour qu'à la
clôture d'une **version**, pas d'un ticket.

## Sous-agents

- **Oui** pour la recherche en fan-out (« où est implémenté X ») : on garde la conclusion, pas les
  fichiers.
- **Oui** pour les tickets réellement indépendants — la colonne « Disponibilité » les identifie.
- **Non** sur le chemin critique séquentiel : la continuité y coûte moins cher que la relecture.
- Un sous-agent doit recevoir l'ID du ticket et son bloc « Contexte à charger », sinon il produit
  du hors-sujet.
