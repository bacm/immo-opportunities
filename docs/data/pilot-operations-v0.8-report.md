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
