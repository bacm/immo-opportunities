# Immo Opportunities

Intelligence de marché immobilier sur l'Ille-et-Vilaine, à partir de données publiques.
Produit décidé le 15 septembre 2026 par [ADR-016](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md) :
un **baromètre du marché par EPCI** (V5), puis un **radar hebdomadaire de mise en vente** fondé
sur le dépôt des DPE (V2). La plateforme cartographique écrite avant est **gelée**.

Ce n'est **pas** une prédiction sur un bien, **pas** une détection de vacance, **pas** un accès au
propriétaire, **pas** une estimation de bien non vendu.

**Répondre et documenter en français.**

## État au 15 septembre 2026

Le référentiel spatial du 35 est accepté (1 333 327 parcelles, 514 859 bâtiments physiques), les
quatre sources métier sont importées en `display_only` (285 k mutations DVF sur douze millésimes,
208 k DPE rattachés à 59 %, 21 k zones GPU, 11 k observations Géorisques). La base pèse 29 Go.
**Personne n'a vu le produit, aucun score n'est publié, le moteur de score n'a aucun appelant.**

L'audit du 15 septembre ([`docs/audit-critique-2026-09-15.md`](docs/audit-critique-2026-09-15.md))
établit que la définition initiale n'était pas tenable : l'objet « bien » se réduit à la parcelle,
« off-market » suppose un propriétaire exclu, la rénovation-revente est infondée par les données
du projet (décote énergétique de 3 à 4 %).

| Ce qui existe | État |
|---|---|
| Référentiel spatial 35 (v0.1 à v0.4) | terminé, mesuré, résultats négatifs établis |
| Sources métier 35 (v0.5) | importées, `display_only`, gelées |
| Plateforme (v0.6 à v0.8 : scoring, Explorer, multi-tenant, déploiement) | codée, **gelée par ADR-016** |
| Baromètre et radar (série H) | **en cours** |

### Ce que le référentiel a établi, à ne pas redécouvrir

Négatifs : adresse ↔ parcelle non vérifiable géométriquement, ~24 % d'erreur irréductible ; une
unité foncière par parcelle et la contiguïté ne peut y suppléer (BUG-11) ; DPE rattaché au
bâtiment à 59 % ; 65 % des mutations DVF sans prix allouable ; aucune zone inondable typée sur le
35 ; deux motifs de rejet terrain sans aucune source (sol goudronné, piscine).

Positifs, non recomptés : le dépôt d'un DPE prédit une mutation à douze mois à 35 % contre 3 %
(lift × 11,8, deux cohortes) ; sur 7 024 paires de reventes, plus-value nette × 1,90 sous 60 % du
prix de marché et × 1,01 au prix. Voir `docs/data/dpe-signal-vente-35.md` et
`docs/data/pistes-analyse-marche-35.md`.

### Le chemin critique tient en une phrase

> Produire le baromètre du 35, le mettre entre les mains de cinq professionnels, obtenir un avis
> juridique, puis lancer le radar. Rien d'autre.

Si on demande « le plus important maintenant » : **H1, le baromètre du marché du 35.** Sans lui,
aucun entretien n'a de prétexte et aucun prix ne peut être posé.

## Carte du contexte — à lire avant de charger quoi que ce soit

`SPEC.md` et `ARCHITECTURE.md` ont été réécrits le 15 septembre ; ils font chacun environ 600
lignes. **Ne pas les charger par défaut.** L'audit (1 160 lignes) est de l'historique : on y va
pour une preuve, pas pour s'orienter.

| Tâche | Charger |
|---|---|
| Implémenter un ticket | [`docs/backlog/<ID>-*.md`](docs/backlog/) — son bloc « Contexte à charger ». Rien d'autre. |
| Savoir quoi faire ensuite | [`docs/backlog/README.md`](docs/backlog/README.md), chemin critique et colonne « Disponibilité » |
| Pourquoi le produit a changé | [`docs/decisions/ADR-016-…`](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md), 80 lignes |
| Périmètre, mesures `BAR-*`, interdits de données | `SPEC.md` — **la section concernée seulement** (§7, §8, §13) |
| Ce qui existe, ce qui est gelé, ce qui est défectueux | `ARCHITECTURE.md` — **la section concernée seulement** |
| Un chiffre et son filtre | le rapport de `docs/data/` qui le porte, jamais un résumé |
| Reconstituer la base | [`docs/operations/referentiel-local-35.md`](docs/operations/referentiel-local-35.md) |

Sources de vérité, dans cet ordre : `SPEC.md` → `ARCHITECTURE.md` → `docs/decisions/` →
`contracts/` → `docs/data/`.

## Règles non négociables

- Une valeur manquante **reste manquante avec un motif**. Jamais convertie en zéro.
- **Un taux ne paraît jamais sans son effectif**, et le filtre de sa cohorte est écrit dans la
  sortie. Un effectif sans filtre n'est pas reproductible — leçon de l'écart 14 532 / 9 754.
- **Aucun seuil territorial inventé.** Un seuil de support est un paramètre déclaré et affiché.
- **Aucune combinaison de signaux en score** sans profiling écrit. Âge d'un DPE et étiquette
  restent deux lectures indépendantes.
- **Aucune donnée nominative** (parcelle, adresse) dans le baromètre. **Aucune liste nominative
  par adresse** avant l'avis juridique H4.
- **Réforme DPE du 1er janvier 2026** : rupture de série sur les logements électriques, à
  distinguer ou à déclarer.
- **Pas d'alias `latest`** pour un import reproductible. Checksum SHA-256 avant import. La clé
  d'idempotence et l'identifiant de run portent la version de transformation.
- **Données simulées interdites** pour satisfaire un critère « données réelles ».
- Anomalie sur un attribut → l'attribut devient manquant avec motif, l'enregistrement est conservé.
- **Tout pipeline prévoit la variété de sa source avant son premier lot.** Voir
  `ARCHITECTURE.md` §10.6.
- **Tout chiffre publié dans `docs/data/` passe par `recompte-preuve`** avant que le ticket soit
  terminé.

## Interdits techniques

Pas de ML en production. Pas de Kubernetes. Pas de Celery. Pas de scoring à la requête. Pas de
secrets en clair. Pas de nouvelle table pour le baromètre : il lit et écrit des fichiers.

**Plateforme gelée :** aucune ligne dans `apps/web/`, `backend/src/immo/api/`, le moteur de
score, `infra/`, `config/`, les fichiers Compose, tant que H3 n'a pas rendu son verdict et qu'une
ADR n'a pas levé le gel. Un défaut bloquant (audit §7.2) se corrige sous ticket au moment du dégel,
pas avant. Si l'API locale sert à vérifier une donnée, elle reste locale : 41 routes sur 45 sont
anonymes.

**Frontend, si dégel :** `apps/web/src/App.tsx` + CSS custom + MapLibre. Ne pas introduire de
bibliothèque sans ADR.

## Hors périmètre — ne pas faire

Propriétaire personne physique sous toute forme, fichier des décès, scraping d'annonces ou
d'annuaires, prospection automatisée, prédiction certaine de vente ou de vacance, indice de vacance,
LOVAC ou données à accès restreint, DPE simulés, estimation d'un bien non vendu, règlement
d'urbanisme interprété, France entière, marketplace, API commerciale publique, extension aux 22,
29 et 56 avant un abonné du 35.

## Ordre d'exécution

```text
H1 baromètre 35 → H2 document publiable → H3 cinq entretiens ─┬─► H5 radar (après H4 avis juridique)
                                                              └─► ADR de sortie : poursuivre, bifurquer V9 (vision), ouvrir V1/V3, dégeler, arrêter
```

Ne pas sauter une étape. Les séries D, E, F, G et la dette transverse sont gelées ; E9 reste
disponible hors chemin critique, et son protocole doit être corrigé avant usage (audit §3.4). Les
nice-to-have ne démarrent pas avant un abonné — voir
[`docs/backlog/NICE-backlog.md`](docs/backlog/NICE-backlog.md).

## Toute modification passe par un ticket

Une demande qui touche le code, un schéma, l'infrastructure ou le comportement de l'application
s'ouvre en ticket **avant la première ligne modifiée** — y compris une demande directe en cours de
conversation. Le ticket porte la demande et **les choix retenus**. C'est lui qui réserve les
chemins, qui rend `make dod` applicable, et qui fait qu'une décision est retrouvable ailleurs que
dans un message de commit.

Seul `docs/` en est dispensé : le backlog, les preuves, les décisions sont la sortie du processus.
`SPEC.md`, `ARCHITECTURE.md` et `CLAUDE.md` demandent un ticket.

Le critère porte sur les **chemins touchés**, jamais sur l'importance qu'on prête au changement.
`make ticket-check` le vérifie : le sujet du commit porte un identifiant du backlog, `H1 — …`,
`A7, H6 — …`. Échappatoire explicite `ticket-ok: <raison>` dans le corps.

**Un manque n'est pas une décision.** Combler un écart qu'un ticket a déjà tranché n'ouvre pas de
ticket : le commit porte l'identifiant de ce ticket-là. Le test : *puis-je désigner le ticket,
l'ADR ou le critère que ce changement se contente d'honorer ?* Sinon, c'est une décision, et elle
s'écrit.

L'audit a constaté que six tickets sur neuf de la série E8 ont été écrits dans le même commit que
leur code, état `Terminé` inclus. Un ticket écrit après coup est une copie du message de commit.
Le ticket s'ouvre avant, en `En cours`, même s'il tient en dix lignes.

## Definition of Done d'une tâche

Terminé **seulement si** :

1. test automatisé ajouté ou étendu ;
2. preuve écrite dans `docs/data/` ou `contracts/`, recomptée si elle porte un chiffre ;
3. `make openapi` régénéré si l'API change ;
4. `make check` vert ;
5. aucune donnée simulée présentée comme réelle ;
6. l'état du ticket est mis à jour **dans son propre fichier**, puis `make backlog` ;
7. les dépendances des tickets que celui-ci débloque sont **relues**.

`make dod ID=<ticket>` vérifie ce qui est mécanisable, et dit ce qu'il ne peut pas vérifier. Un
ticket qui n'a légitimement ni test ni preuve le déclare dans son en-tête par
`**DoD :** test sans objet — <raison>` ou `preuve sans objet — <raison>`.

## Boucle de développement et verrous

Trois natures de contrôle, distinctes et non interchangeables ([ADR-015](docs/decisions/ADR-015-boucle-autonome.md)).

| Nature | Quoi | Quand |
|---|---|---|
| Déterministe | `make check` (inclut `make invariants`), `make backlog-check`, `make dod` | à chaque étape |
| Adversarial | compétence `recompte-preuve` : recalculer depuis les sources, **sans lire le code** | quand l'étape écrit un chiffre dans `docs/data/` |
| Humain | tickets de `**Nature :**` humaine — H3, H4, D6, E9 | verdict sur le monde réel ou arbitrage produit |

`make invariants` vérifie les interdits sur les **lignes ajoutées** du diff. L'audit a montré ses
limites : ses motifs sont calibrés à zéro détection sur l'historique, et la règle `seuil-invente`
ne regarde pas `pipelines/scripts/`. Il attrape l'arrangement grossier, pas le défaut de donnée ;
seul le recompte attrape celui-là. Une ligne légitimement signalée se justifie sur place :
`invariant-ok: <raison>`.

**La boucle s'arrête** — et rend la main plutôt que de contourner — sur :

- un ticket de nature humaine, annoncé **verrou humain** et jamais « prêt » ;
- deux échecs consécutifs du même gate sur le même ticket ;
- une décision que `SPEC.md` ne tranche pas ;
- une source externe indisponible ou un quota atteint — temporiser, jamais substituer une fixture ;
- une contradiction entre deux sources de vérité.

L'arrêt est explicite et bruyant.

## Commandes

```bash
make dev                  # démarre les 20 services ; la base part vide
make rebuild              # reconstruit les images — recrée PostgreSQL, vérifier qu'aucun lot ne tourne
make check                # lint, typecheck, tests (sans base), OpenAPI, Compose, invariants, budget doc
make backlog              # régénère le tableau de suivi ; make backlog-check le vérifie
make dod ID=<ticket>      # ce qui est mécanisable de la DoD
make invariants           # interdits sur les lignes ajoutées — BASE=<ref>
make ticket-check         # tout commit hors docs/ porte un identifiant de ticket
make dvf-import           # imports : rnb-, ban-, bdnb-, bdtopo-, dvf-, dpe-, gpu-, georisques-import
make physical-buildings SOURCE=rnb DEPARTMENT=35
make morphology-features  # LAND-*/BLD-* ; make urban-features pour URB-*
make exploratory-candidates COMMUNE=35051   # liste E8 ; make biens-en-vente pour E8f
make field-test-kit COMMUNE=35051
```

Les cibles du baromètre (`market-barometer`, `market-barometer-kit`) arrivent avec H1 et H2.

**`make rebuild` recrée PostgreSQL et coupe tout travail en cours.** `check-no-batch` refuse si un
import tourne ; `FORCE_REBUILD=1` pour passer outre en connaissance de cause.

**Les conteneurs embarquent une copie du code figée au build.** `compose.dev.yaml` ne monte pas
les sources : un changement de pipeline ou de contrat demande `make rebuild`. `docker compose`
sans les trois `-f` recrée les conteneurs hors configuration de développement.

**Le front servi n'est pas celui que Playwright teste** (serveur Vite sans OIDC contre bundle
nginx derrière Caddy). Sans objet tant que le front est gelé ; à retenir au dégel. Le navigateur
utilise `http://localhost:8080`, Caddy ne répond pas sur `127.0.0.1`.

## Suivi du backlog

L'état d'un ticket vit **à un seul endroit** : la ligne `**État :**` de son fichier. Valeurs :
`À faire`, `En cours`, `Terminé`, `Abandonné`. `**Nature :**` vaut `implémentation` (défaut),
`revue humaine` ou `décision humaine` ; les deux dernières sont des **verrous** qui déclarent par
`**Preuve :**` le fichier attendu. Le verrou est une propriété déclarée, jamais une appréciation
en cours de route.

La colonne « Disponibilité » est **dérivée** du graphe de dépendances par `make backlog`. Les
séries A à H sont reconnues ; une nouvelle lettre demande un ticket (A7 en est le modèle).
`make backlog-check` est volontairement hors de `make check`.

Un ticket gelé par ADR-016 reste `À faire` avec sa disponibilité dérivée ; le gel est écrit dans
le chemin critique du README, pas dans chaque ticket.

## Sous-agents et parallélisation

- **Oui** pour la recherche en fan-out : on garde la conclusion, pas les fichiers.
- **Oui** pour les tickets d'un même **lot menable de front**, dérivé du champ `**Touche :**`.
- **Non** sur le chemin critique H1 → H2 → H3 : la continuité y coûte moins que la relecture.
- Un sous-agent reçoit l'ID du ticket et son bloc « Contexte à charger », sinon il produit du
  hors-sujet.

Un ticket sans `Touche` déclaré est isolé par précaution. **Passer un ticket à `En cours` en le
commençant**, pas en le finissant. **À la clôture, réexaminer ce qu'il débloque.**
