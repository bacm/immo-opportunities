# G7 — Observabilité minimale mesurable

**Version :** v0.8 · **Taille :** M · **État :** À faire
**Dépend de :** — (parallélisable) · **Bloque :** clôture de v0.8

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
