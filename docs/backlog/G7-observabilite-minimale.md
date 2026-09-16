# G7 — Observabilité minimale mesurable

**Version :** v0.8 · **Taille :** M · **État :** Terminé
**Dépend de :** — (parallélisable) · **Bloque :** clôture de v0.8
**Touche :** config/grafana/, config/prometheus/, config/alloy/, config/caddy/, backend/src/immo/api/middleware.py, backend/src/immo/main.py, backend/tests/, docker/api/Dockerfile, apps/web/src/, apps/web/tests/e2e/real-map.spec.ts, scripts/export-pilot-metrics, scripts/tests/, Makefile, docs/operations/observabilite.md, docs/data/pilot-operations-v0.8-report.md, docs/data/mvp-dod-traceability.md, docs/data/captures/
**Nature :** implémentation
**DoD :** preuve dans `docs/data/pilot-operations-v0.8-report.md`

## Contexte à charger

- `compose.observability.yaml`
- `backend/src/immo/api/middleware.py` (request_id)
- `docs/data/pilot-operations-v0.8-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

État actuel : « Traces, métriques, logs corrélés — request ID, Prometheus, Loki, dashboard —
**partiel** ».

**Cadrage explicite :** OpenTelemetry n'est pas bloquant pour le pilote. Si Prometheus, les
journaux et le `request_id` suffisent à répondre aux questions ci-dessous, c'est suffisant.
L'instrumentation OTel complète est un [nice-to-have](./NICE-backlog.md) (N6), à faire après le
pilote et non avant.

## Choix retenus — 16 septembre 2026

Pris par l'agent sur délégation du porteur (« enchaîne en prenant les meilleures décisions »).
Mené en local : la plateforme n'est déployée pour personne (`ARCHITECTURE.md` §25.2) ; la preuve
est celle de la pile `compose.observability.yaml` sur le poste.

- **Aucun service ni bibliothèque ajouté.** Les métriques de latence sont tirées des journaux par
  Alloy, déjà en place (`loki.process`, `stage.metrics`), et Prometheus scrape Alloy. Un client
  Prometheus dans l'API aurait demandé une ADR pour une dépendance ; un exportateur blackbox, un
  service de plus.
- **Latence API par route** : le journal `request_completed` porte le gabarit de route
  (`/api/v1/parcels/{parcel_id}`), jamais le chemin concret — cardinalité bornée, aucun
  identifiant en étiquette. Histogramme `immo_api_request_duration_milliseconds{route, status_class}` (Alloy ne convertit pas l'unité).
- **Latence des tuiles par zoom** : journal d'accès Caddy en JSON, sans en-têtes ni chaîne de
  requête, IP tronquée ; Alloy en tire `immo_tile_request_duration_seconds{layer, zoom}`.
- **Disponibilité de l'API** : contrôle actif de Caddy sur `/health/ready`, qui expose
  `caddy_reverse_proxy_upstreams_healthy`. Idem pour Martin.
- **Fraîcheur et échecs d'import** : `scripts/export-pilot-metrics` écrit, par source et
  territoire, le dernier import réussi et le dernier échec ; le motif reste en base
  (`meta.import_run.error_message`) et dans l'API d'administration, jamais en étiquette. Le script
  accepte les fichiers Compose du poste (`make pilot-metrics`).
- **Alertes, trois** : import en échec non rattrapé ; API ou Martin indisponible ; p95 de l'API
  sur 10 min supérieur à trois fois son p95 sur 24 h. Le facteur 3 est un paramètre déclaré dans
  `alerts.yml`, pas une cible produit : `SPEC.md` n'en fixe aucune.
- **Corrélation** : le client web envoie son propre `X-Request-ID` et l'affiche dans le message
  d'erreur ; l'API le reprend, le journalise avec la route et, en cas d'exception, avec la trace ;
  en base, le `request_id` n'est écrit que par le journal d'audit des routes d'administration.
  Instrumenter psycopg reste N6.

## Questions auxquelles l'observabilité doit répondre

C'est le critère d'acceptation réel : ce ne sont pas des métriques qu'il faut, ce sont des réponses.

| Question | Métrique nécessaire |
|---|---|
| L'application est-elle lente pour un utilisateur du pilote ? | latence API par endpoint, percentiles |
| La carte est-elle lente ? | latence de génération des tuiles Martin, par niveau de zoom |
| Les données sont-elles à jour ? | fraîcheur par source et par département |
| Un import a-t-il échoué ? | échecs d'import, avec dataset, département et motif |
| Que s'est-il passé pour cet utilisateur à ce moment ? | corrélation par `request_id` entre journaux et erreurs |

## Travail à réaliser

1. Vérifier que chaque question ci-dessus trouve une réponse dans l'outillage existant. Ne combler
   que les manques constatés.
2. Exposer la fraîcheur des sources comme métrique, pas seulement comme colonne en base.
3. Définir des alertes sur les seuls événements qui appellent une action pendant le pilote :
   échec d'import, indisponibilité de l'API, dégradation marquée de latence.
4. Vérifier la corrélation `request_id` de bout en bout : frontend → API → base.
5. Vérifier qu'aucun secret ni donnée privée d'organisation n'apparaît dans les journaux.

## Points de vigilance

- Une alerte qui se déclenche sans action associée sera ignorée dès la deuxième occurrence. En
  définir peu.
- Pendant le pilote, la question la plus probable sera « pourquoi ce professionnel a-t-il vu cela
  à ce moment ? » : la corrélation par `request_id` compte plus que le volume de métriques.
- Ne pas instrumenter psycopg et le frontend carte pour ce ticket : c'est N6, après le pilote.

## Critères d'acceptation

- les cinq questions trouvent une réponse démontrée, capture à l'appui ;
- alertes en place sur les événements actionnables ;
- corrélation `request_id` vérifiée de bout en bout ;
- aucun secret ni donnée privée dans les journaux ;
- la ligne « Traces, métriques, logs corrélés » de la traçabilité passe à validé pour le périmètre
  pilote, avec la mention explicite qu'OTel reste à faire.

## Preuve à produire

Section observabilité de [`pilot-operations-v0.8-report.md`](../data/pilot-operations-v0.8-report.md),
avec captures du tableau de bord répondant aux cinq questions.

## Résultat — 16 septembre 2026

- Les cinq questions ont une réponse, un rang chacune du tableau de bord *Immo — observabilité* ;
  preuve et captures dans [`pilot-operations-v0.8-report.md`](../data/pilot-operations-v0.8-report.md),
  mode d'emploi dans [`observabilite.md`](../operations/observabilite.md).
- **Défaut trouvé** : `immo.access` n'avait pas de handler, le `request_id` ne sortait jamais du
  conteneur ; et le journal d'uvicorn écrivait la chaîne de requête (adresses recherchées). Les
  deux sont corrigés (`configure_logging`, `--no-access-log`). Une exception est journalisée avec
  sa référence et sa trace.
- Client web : `X-Request-ID` par requête, référence affichée dans chaque panne ; test e2e.
- Caddy : journal d'accès filtré (ni en-têtes, ni chaîne de requête, IP /16), `request_id`
  ajouté, contrôles de santé API et Martin. Alloy tire deux histogrammes des journaux ; Prometheus
  le scrape.
- `scripts/export-pilot-metrics` : fraîcheur (publication du producteur, dernier import) et
  dernier échec par source et territoire ; `make pilot-metrics` sur un poste ; tests.
- Trois alertes, testées par `promtool` (`make observability-check`) ; `UpstreamUnhealthy` vue en
  attente pendant un arrêt réel de l'API.
- Écart : un arrêt de l'API a d'abord laissé le service à terre trois minutes, `docker compose
  start` relançant un ancien conteneur de migration sans la révision 0028 ; `up` le recrée.
- DoD, point 3 : `make dod` le marque en échec parce que le middleware change ; aucune route ne
  change, `make openapi` ne produit aucune différence et `openapi-check` est vert.
- Reste à faire : OpenTelemetry (N6) ; une mesure sous charge, qui attend un déploiement ;
  distinguer les tuiles absentes (404) dans la latence.

