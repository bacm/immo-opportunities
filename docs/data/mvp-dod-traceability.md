# Traçabilité de la Definition of Done MVP

**Date :** 10 août 2026  
**Verdict global :** non atteinte. Les preuves techniques ne remplacent ni les imports régionaux,
ni les mesures sur cas réels.

| Exigence `SPEC.md` §26 | Preuve actuelle | État |
|---|---|---|
| Sources critiques des 4 départements importées/versionnées/auditées | matrice Bretagne | bloqué |
| Rapport DS-01 à DS-09 | rapports 35 partiels | bloqué |
| Mapping/formule/manquant par feature activée | contrats features/scoring, tests | technique validée |
| Couverture département/EPCI/commune | table versionnée et rapport vide | mesure réelle absente |
| Carte Bretagne et zones non publiables | sélecteur 22/29/35/56, gate régional | technique validée, données absentes |
| Métriques de résolution des entités | rapport spatial 35 | régional absent |
| Deux scores reproductibles/versionnés/explicables | rapport v0.6 | moteur validé, paramètres bloqués |
| Baseline | moteur et métriques top 10/20/50 | données réelles absentes |
| Performance par segment | protocole 5 segments | données réelles absentes |
| Carte/liste/fiche synchronisées | rapport v0.7, Playwright | validé sur parcours technique |
| Scénarios transparents/modifiables | API, UI, tests | technique validée |
| Qualification de bout en bout | espace privé et résultats successifs | technique validée, cas réel absent |
| Inconnus et avertissements visibles | UI et tests | validé |
| Parcours critiques testés | suites backend/pipeline/front | partiel : charge prod absente |
| Sauvegarde/sécurité/observabilité | scripts, RLS, alertes, dashboard | restauration réelle absente |
| Redéploiement et restauration VPS vierge | GitHub Actions/Ansible + runbook | exercice externe absent |
| 3 professionnels sur cas réels | aucun résultat enregistré | bloqué |
| Décision poursuivre/pivoter/arrêter | no-go technique provisoire | décision finale bloquée |

FR-001 à FR-012 sont tracées dans le rapport v0.7. FR-013 et FR-014 restent des `Should`; FR-015
est partiellement couvert par les organisations et RLS; FR-016 reste explicitement hors v0.8.

## DoD architecture `ARCHITECTURE.md` §25

| Exigence | Preuve actuelle | État |
|---|---|---|
| Local reproductible, runtime Docker | Compose dev/prod, `make dev` | validé |
| VPS vierge par GitHub Actions/Ansible | workflows et playbooks | syntaxe validée, exécution externe absente |
| PostgreSQL/PostGIS migré automatiquement | service migrate, test réel 0001→0015 | validé |
| Rôles et isolation organisations | RLS forcé, tests v0.7 | local validé, production absent |
| Release importée/validée/publiée/annulée | fonctions source et bundle régional | technique validée, région réelle absente |
| Pipelines partitionnés 22/29/35/56 | partitions Dagster statiques | validé pour Cadastre; manifests autres sources absents |
| Score publié reproductible | snapshots immuables | moteur validé, score réel non publié |
| Martin limité aux vues autorisées | rôle `tiles_ro`, fonctions MVT | validé |
| MVT sans GeoJSON régional | MapLibre/Martin | validé |
| OpenAPI génère le client TypeScript | contrat et client généré | validé |
| Tâches longues hors processus web | Dagster pour imports | validé pour imports; Celery non requis au parcours livré |
| Backup, réplication, restauration vierge | scripts/timers/runbook | test réel absent |
| Traces, métriques, logs corrélés | request ID, Prometheus, Loki, dashboard | partiel |
| Parcours critiques en CI | workflow CI et tests | nouveaux tests locaux; exécution GitHub absente |
| Staging et rollback automatisés | workflow multi-environnement, fonctions rollback | exécution externe absente |
| Backup et clé de reprise hors cible | réplication configurable | cible/clé externes absentes |
| Aucun ML/Kubernetes requis | stack Compose | validé |
