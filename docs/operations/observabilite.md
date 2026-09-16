# Observabilité — ce qui répond à quoi

Ticket [G7](../backlog/G7-observabilite-minimale.md). Pile : `compose.observability.yaml`
(Prometheus, Loki, Alloy, Grafana, node-exporter). Aucun service ni bibliothèque de plus.
Tableau de bord Grafana **Immo — observabilité** (`immo-observabilite`), un rang par question.

| Question | Où regarder | D'où vient la donnée |
|---|---|---|
| L'application est-elle lente ? | rang 1 : p95 par route, p50/p95 cumulés, réponses 5xx | journal `immo.access` de l'API → Alloy → `immo_api_request_duration_milliseconds{route, status_class}` |
| La carte est-elle lente ? | rang 2 : p95 par couche et zoom | journal d'accès Caddy → Alloy → `immo_tile_request_duration_seconds{layer, zoom}` |
| Les données sont-elles à jour ? | rang 3 : jours depuis la publication du producteur et depuis l'import | `make pilot-metrics` → collecteur textfile → `immo_source_release_published_timestamp_seconds`, `immo_source_last_import_success_timestamp_seconds` |
| Un import a-t-il échoué ? | rang 4 : échecs non rattrapés, alertes actives | `immo_source_last_import_failure_timestamp_seconds` ; le motif est dans `meta.import_run.error_message` et `GET /api/v1/admin/import-runs` |
| Que s'est-il passé pour cet utilisateur ? | rang 5 : journaux API et Caddy filtrés par la référence | `X-Request-ID` émis par le client web, affiché dans tout message de panne |

## La référence d'une requête

1. Le client web tire un identifiant par requête et l'envoie en `X-Request-ID`. Une panne affiche
   « Référence : … » : c'est ce que l'utilisateur cite.
2. Caddy l'ajoute à son journal d'accès (`request_id`), même quand l'API ne répond pas.
3. L'API le reprend (ou en tire un si l'en-tête est absent ou invalide), le renvoie, l'écrit dans
   `request_completed` avec la route et, en cas d'exception, dans `request_failed` avec la trace.
   Les erreurs JSON le portent (`error.request_id`).
4. En base, seul le journal d'audit des routes d'administration l'écrit
   (`audit.sensitive_access_event.request_id`). Les lectures publiques ne laissent rien en base :
   instrumenter psycopg est N6, après le pilote.

Dans Grafana, coller la référence dans le champ **Référence (X-Request-ID)**.

## Alertes (`config/prometheus/alerts.yml`)

| Alerte | Déclenchement | Action |
|---|---|---|
| `ImportFailedNotRecovered` | dernier échec plus récent que la dernière réussite, source × territoire, 5 min | lire le motif, relancer l'import |
| `UpstreamUnhealthy` | contrôle de santé Caddy à 0 pendant 2 min (API : `/health/ready`, Martin : `/health`) | redémarrer le service, lire ses journaux |
| `ApiLatencyDegraded` | p95 sur 10 min > 3 × p95 sur 24 h, pendant 15 min | chercher la route en cause au rang 1 |

Le facteur 3 est un paramètre déclaré, pas une cible produit. Les alertes antérieures (sauvegarde,
import global, sources publiées, cible Prometheus à 0) sont inchangées. **Sur un poste, deux
d'entre elles sont vraies** : aucune sauvegarde n'existe (G6), et moins de neuf sources ont une
release active. `make observability-check` valide la configuration et rejoue les tests
`config/prometheus/alerts.test.yml`.

## Ce que les journaux ne contiennent pas

- Caddy : ni en-têtes, ni chaîne de requête (une recherche porte une adresse, un retour OIDC porte
  un code), IP tronquée à /16.
- API : le journal d'accès d'uvicorn, qui écrivait la chaîne de requête, est coupé
  (`--no-access-log`) ; `immo.access` écrit la route et le chemin, jamais la chaîne de requête ni
  les en-têtes.
- Les métriques ne portent aucun identifiant : gabarit de route, classe de statut, couche, zoom,
  source, territoire.

## Sur un poste

```bash
make observability-check      # promtool, tests d'alertes, Alloy, Caddy
make pilot-metrics            # fraîcheur et échecs d'import ; à relancer après un import
```

Le serveur de développement Vite (`pnpm dev`) contourne Caddy : ses requêtes n'apparaissent que
dans le journal de l'API. En production, `scripts/export-pilot-metrics` tourne par minuterie avec
ses chemins par défaut.

**Limites.** OpenTelemetry (N6) reste à faire. Les latences de tuiles ne distinguent pas une tuile
absente (404, sous le zoom minimal) d'une tuile servie. Aucune mesure n'a été prise sur un
environnement chargé : la pile n'est déployée pour personne.
