# Coût, capacité et performance — pilote v0.8

**État au 10 août 2026 :** instrumentation livrée, mesures staging/production absentes.

Le dashboard Grafana `Pilote Bretagne — exploitation` suit disponibilité, âge du dernier backup,
âge du dernier import, nombre de sources actives, mémoire et stockage du VPS via Prometheus et
node-exporter. La facture mensuelle reste une donnée contractuelle de l'hébergeur et doit être
jointe à chaque revue ; aucune valeur de coût n'est inventée dans les métriques.

Le script `scripts/load-test-pilot` mesure p95 carte, liste, API d'administration et tuiles avec un
niveau de concurrence configurable. Exemple staging :

```bash
IMMO_ACCESS_TOKEN=<token-court> LOAD_TEST_REQUESTS=500 LOAD_TEST_CONCURRENCY=20 \
  ./scripts/load-test-pilot https://staging.example.test \
  > docs/data/evidence/load-staging-2026-08-10.json
```

Les cibles de la spec restent p95 < 500 ms pour la carte/liste, < 300 ms pour la fiche hors
services externes et fluidité cartographique perçue. Aucun résultat n'est publié ici : sans
staging régional chargé de données réelles, le script ne fournirait qu'une mesure artificielle.

Avant le go pilote, joindre : prix VPS et backup hors site, stockage PostgreSQL/MinIO, trafic,
CPU/mémoire/disque de pointe, p95 par endpoint, volume de tuiles, durée des imports et projection à
12 mois. Une saturation d'un segment ou département ne peut être masquée par une moyenne régionale.

## Observabilité — G7, 16 septembre 2026

Vérifié sur la pile locale (`compose.observability.yaml`), la plateforme n'étant déployée pour
personne. Mode d'emploi : [`observabilite.md`](../operations/observabilite.md).

- **Les cinq questions ont une réponse**, un rang chacune du tableau de bord *Immo —
  observabilité* : latence API par route, latence des tuiles par couche et zoom, fraîcheur par
  source et territoire, échecs d'import non rattrapés, journaux filtrés par référence
  ([capture](./captures/g7-tableau-de-bord.png)).
- **Corrélation de bout en bout.** L'API arrêtée, la fiche d'un DPE affiche « Recherche
  indisponible » et sa référence ([capture](./captures/g7-reference-panne.png)) ; la même
  référence, rejouée à travers Caddy, y est journalisée avec le statut 502 (rang 5 de la capture
  du tableau de bord). Une requête servie se retrouve dans le journal de l'API par sa référence,
  avec sa route et sa durée ([capture](./captures/g7-journaux-reference.png)). En base, seul
  l'audit des routes d'administration porte la référence.
- **Alertes.** Pendant l'arrêt, le contrôle de santé de Caddy est passé à 0 pour `api:8000` et
  `UpstreamUnhealthy` est passée en attente ; son déclenchement après deux minutes, et ceux des
  deux autres alertes, sont prouvés par `promtool test rules`.
- **Journaux.** Aucun en-tête, aucune chaîne de requête, IP tronquée ; aucune occurrence de
  jeton, mot de passe ou en-tête d'autorisation dans les journaux API, Caddy, web, Martin,
  Keycloak et Dagster des deux dernières heures — la seule correspondance est le nom d'un script
  Keycloak (`passwordVisibility.js`).
- **Défaut corrigé en passant** : le journal `immo.access` n'avait aucun handler ; le
  `request_id` n'avait jamais atteint la sortie du conteneur.
- **Reste à faire** : OpenTelemetry (N6) ; une mesure sous charge réelle, qui attend un
  environnement déployé.

