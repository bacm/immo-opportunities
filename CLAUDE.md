# Immo Opportunities

Intelligence de marché immobilier sur l'Ille-et-Vilaine, à partir de données publiques.
[ADR-016](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md) : un **baromètre du marché
par EPCI** (V5), puis un **radar hebdomadaire de mise en vente** fondé sur le dépôt des DPE (V2).
La plateforme cartographique antérieure est **gelée**. Ce n'est **pas** une prédiction sur un
bien, une détection de vacance, un accès au propriétaire, ni une estimation de bien non vendu.

**Répondre et documenter en français.**

## État au 16 septembre 2026

Référentiel spatial du 35 accepté ; DVF, DPE, GPU, Géorisques importés en `display_only` ;
plateforme codée mais gelée, sans utilisateur ni score publié. Série H en cours : H1 terminé,
H2 disponible. **Chemin critique :** produire le baromètre du 35, le mettre entre les mains de
cinq professionnels, obtenir un avis juridique, puis lancer le radar. Rien d'autre.

```text
H1 baromètre → H2 document publiable → H3 cinq entretiens ─┬─► H5 radar (après H4 avis juridique)
                                                           └─► ADR de sortie : poursuivre, bifurquer V9, ouvrir V1/V3, dégeler, arrêter
```

Ne pas sauter une étape. Séries D, E, F, G et dette transverse gelées ; E9 disponible hors chemin
critique, protocole à corriger avant usage (audit §3.4). Nice-to-have après un abonné
([`NICE-backlog.md`](docs/backlog/NICE-backlog.md)).

**Acquis à ne pas redécouvrir** (preuves dans `docs/data/`). Négatifs : adresse ↔ parcelle
non vérifiable, ~24 % d'erreur irréductible ; une unité foncière par parcelle, la contiguïté n'y
supplée pas (BUG-11) ; DPE rattaché au bâtiment à 59 % ; 65 % des mutations DVF sans prix
allouable ; aucune zone inondable typée ; sol goudronné et piscine sans source ; décote énergétique
de 3 à 4 %, rénovation-revente infondée. Positifs, non recomptés : un dépôt de DPE prédit une
mutation à douze mois à 35 % contre 3 % (`dpe-signal-vente-35.md`) ; plus-value nette × 1,90 sous
60 % du prix de marché, × 1,01 au prix (`pistes-analyse-marche-35.md`).

## Quoi charger

`SPEC.md` et `ARCHITECTURE.md` (~600 lignes chacun) : **jamais par défaut**. L'audit
(`docs/audit-critique-2026-09-15.md`) est de l'historique : on y va pour une preuve.

| Tâche | Charger |
|---|---|
| Implémenter un ticket | `docs/backlog/<ID>-*.md`, son bloc « Contexte à charger ». Rien d'autre. |
| Savoir quoi faire ensuite | `docs/backlog/README.md`, chemin critique et « Disponibilité » |
| Pourquoi le produit a changé | ADR-016, 80 lignes |
| Périmètre, mesures `BAR-*`, interdits de données | `SPEC.md` §7, §8, §13 seulement |
| Ce qui existe, gelé ou défectueux | `ARCHITECTURE.md`, la section concernée seulement |
| Un chiffre et son filtre | le rapport `docs/data/` qui le porte, jamais un résumé |
| Reconstituer la base | `docs/operations/referentiel-local-35.md` |

Sources de vérité, dans l'ordre : `SPEC.md` → `ARCHITECTURE.md` → `docs/decisions/` →
`contracts/` → `docs/data/`.

## Règles non négociables

- Valeur manquante **reste manquante avec un motif**, jamais zéro. Anomalie sur un attribut →
  attribut manquant avec motif, enregistrement conservé.
- **Jamais un taux sans son effectif**, ni un effectif sans le filtre de sa cohorte écrit dans la
  sortie (leçon de l'écart 14 532 / 9 754).
- **Aucun seuil territorial inventé** : un seuil de support est un paramètre déclaré et affiché.
- **Aucune combinaison de signaux en score** sans profiling écrit ; âge d'un DPE et étiquette
  restent deux lectures indépendantes.
- **Aucune donnée nominative** (parcelle, adresse) dans le baromètre ; **aucune liste par
  adresse** avant l'avis juridique H4.
- **Réforme DPE du 1er janvier 2026** : rupture de série sur les logements électriques, à
  distinguer ou à déclarer.
- Import reproductible : **pas d'alias `latest`**, SHA-256 avant import, clé d'idempotence et
  identifiant de run portent la version de transformation.
- **Données simulées interdites** pour satisfaire un critère « données réelles ».
- Tout pipeline prévoit la variété de sa source avant son premier lot (`ARCHITECTURE.md` §10.6).
- Tout chiffre publié dans `docs/data/` passe par `recompte-preuve` avant clôture du ticket.

**Interdits techniques :** ML en production, Kubernetes, Celery, scoring à la requête, secrets
en clair, nouvelle table pour le baromètre (il lit et écrit des fichiers).

**Plateforme gelée :** aucune ligne dans `apps/web/`, `backend/src/immo/api/`, le moteur de
score, `infra/`, `config/`, les fichiers Compose, tant que H3 n'a pas rendu son verdict et qu'une
ADR n'a pas levé le gel ; un défaut bloquant (audit §7.2) se corrige sous ticket au dégel. L'API
locale reste locale (41 routes sur 45 anonymes). Front au dégel : `apps/web/src/App.tsx` + CSS
custom + MapLibre, aucune bibliothèque sans ADR.

**Hors périmètre :** propriétaire personne physique sous toute forme, fichier des décès, scraping
d'annonces ou d'annuaires, prospection automatisée, prédiction certaine de vente ou de vacance,
indice de vacance, LOVAC ou données à accès restreint, DPE simulés, estimation d'un bien non
vendu, règlement d'urbanisme interprété, France entière, marketplace, API commerciale publique,
extension aux 22, 29 et 56 avant un abonné du 35.

## Toute modification passe par un ticket

Toute demande touchant le code, un schéma, l'infrastructure ou le comportement de l'application
s'ouvre en ticket **avant la première ligne modifiée**, même en cours de conversation, en
`En cours`, avec la demande et **les choix retenus**. Seul `docs/` en est dispensé ; `SPEC.md`,
`ARCHITECTURE.md` et `CLAUDE.md` demandent un ticket. Le critère porte sur les **chemins
touchés**, jamais sur l'importance du changement. Combler un écart déjà tranché n'ouvre pas de
ticket : le commit porte l'identifiant du ticket honoré. Sinon c'est une décision, et elle
s'écrit. `make ticket-check` : sujet du commit avec identifiant (`H1 — …`, `A7, H6 — …`) ou
`ticket-ok: <raison>` dans le corps.

## Definition of Done

Terminé **seulement si** : 1) test automatisé ajouté ou étendu ; 2) preuve dans `docs/data/` ou
`contracts/`, recomptée si elle porte un chiffre ; 3) `make openapi` régénéré si l'API change ;
4) `make check` vert ; 5) aucune donnée simulée présentée comme réelle ; 6) état du ticket mis à
jour **dans son propre fichier**, puis `make backlog` ; 7) dépendances des tickets débloqués
**relues**. `make dod ID=<ticket>` vérifie le mécanisable. Sans test ou preuve légitime, l'en-tête
le déclare : `**DoD :** test sans objet — <raison>` ou `preuve sans objet — <raison>`.

## Boucle et verrous ([ADR-015](docs/decisions/ADR-015-boucle-autonome.md))

| Nature | Quoi | Quand |
|---|---|---|
| Déterministe | `make check` (inclut `make invariants`), `make backlog-check`, `make dod` | à chaque étape |
| Adversarial | `recompte-preuve` : recalculer depuis les sources, **sans lire le code** | dès qu'un chiffre entre dans `docs/data/` |
| Humain | tickets de `**Nature :**` humaine — H3, H4, D6, E9 | verdict sur le monde réel ou arbitrage produit |

`make invariants` contrôle les interdits sur les **lignes ajoutées** ; il attrape l'arrangement
grossier, pas le défaut de donnée (`seuil-invente` ignore `pipelines/scripts/`). Ligne légitime
signalée : `invariant-ok: <raison>` sur place.

**La boucle s'arrête**, explicitement, sur : un ticket de nature humaine (annoncé **verrou
humain**, jamais « prêt ») ; deux échecs consécutifs du même gate sur le même ticket ; une
décision que `SPEC.md` ne tranche pas ; une source externe indisponible ou un quota atteint
(temporiser, jamais une fixture) ; une contradiction entre deux sources de vérité.

## Commandes

```bash
make dev                  # 20 services ; la base part vide
make rebuild              # reconstruit les images, recrée PostgreSQL et coupe tout lot en cours
make check                # lint, typecheck, tests (sans base), OpenAPI, Compose, invariants, budget doc
make backlog              # régénère le tableau ; make backlog-check le vérifie (hors make check)
make dod ID=<ticket>      # ce qui est mécanisable de la DoD
make invariants           # interdits sur les lignes ajoutées — BASE=<ref>
make ticket-check         # tout commit hors docs/ porte un identifiant de ticket
make dvf-import           # imports : rnb-, ban-, bdnb-, bdtopo-, dvf-, dpe-, gpu-, georisques-import
make physical-buildings SOURCE=rnb DEPARTMENT=35
make morphology-features  # LAND-*/BLD-* ; make urban-features pour URB-*
make market-barometer     # H1 ; market-barometer-kit arrive avec H2
make exploratory-candidates COMMUNE=35051   # E8 ; make biens-en-vente pour E8f
make field-test-kit COMMUNE=35051
```

`check-no-batch` refuse `make rebuild` si un import tourne (`FORCE_REBUILD=1` passe outre). Les
conteneurs embarquent le code figé au build : un changement de pipeline ou de contrat demande
`make rebuild` ; `docker compose` sans les trois `-f` sort de la configuration de développement.
Au dégel du front : le front servi (nginx derrière Caddy) n'est pas celui testé par Playwright
(Vite sans OIDC) ; navigateur sur `http://localhost:8080`, pas `127.0.0.1`.

## Backlog et sous-agents

L'état d'un ticket vit à **un seul endroit**, la ligne `**État :**` de son fichier : `À faire`,
`En cours`, `Terminé`, `Abandonné`. `**Nature :**` vaut `implémentation` (défaut), `revue humaine`
ou `décision humaine` ; ces deux dernières sont des **verrous** déclarés, avec `**Preuve :**` le
fichier attendu. « Disponibilité » est dérivée du graphe par `make backlog`. Séries A à H
reconnues ; une nouvelle lettre demande un ticket (modèle : A7). Un ticket gelé reste `À faire`, le gel étant écrit dans le README du backlog.
**Passer un ticket à `En cours` en le commençant** ; à la clôture, réexaminer ce qu'il débloque.

Sous-agents : **oui** pour la recherche en fan-out (garder la conclusion) et pour les tickets d'un
même lot menable de front (champ `**Touche :**` ; sans `Touche`, ticket isolé) ; **non** sur le
chemin critique H1 → H2 → H3. Un sous-agent reçoit l'ID du ticket et son bloc « Contexte à
charger », sinon il produit du hors-sujet.
