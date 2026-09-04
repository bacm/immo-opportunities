# Nice to have — après un score publié

**État :** aucun de ces items ne démarre avant [E3](./E3-publier-snapshots.md), c'est-à-dire avant
qu'un top-N réel soit publiable sur le 35.

La raison n'est pas dogmatique : chacun de ces items suppose connu quelque chose qui ne l'est pas
encore. Un export sert à exporter un classement qui n'existe pas ; une alerte prévient d'un
changement de score qui n'est jamais calculé ; une collaboration organise le travail sur des
candidats absents. Les construire avant reviendrait à figer des choix sur des hypothèses.

## Should — valeur pour le pilote, hors DoD stricte

### N1 — FR-013 Export CSV / PDF d'une sélection filtrée

Export autorisé et audité d'une sélection. **C'est le déclencheur de Celery** : jusqu'ici, aucune
tâche longue ne le justifiait, l'interdit tombe ici et pas avant.

À cadrer : périmètre exportable selon les droits, audit de qui exporte quoi, mentions de source et
de fraîcheur sur l'export lui-même — un CSV qui circule sans sa provenance devient une donnée
orpheline.

### N2 — FR-014 Alertes nouveau candidat ou changement de score

Alertes par territoire, stratégie et fréquence. Suppose une publication régulière de snapshots, donc
au moins deux publications successives pour que « changement » ait un sens.

Point délicat : un changement de score dû à un changement de **définition** n'est pas un changement
dû à un changement de **donnée**. Les confondre produirait des alertes ininterprétables.

### N3 — FR-015 Collaboration d'équipe

Au-delà des organisations et de la RLS déjà en place : partage de notes et de statuts, rôles
`analyst` et `viewer`. À reprendre après [F3](./F3-isolation-organisations.md), dont il étend le modèle.

### N4 — Orthophoto IGN en qualification

Le fond est déjà basculable. S'il sert à qualifier un bien, il faut tracer date, saison, résolution
et droits d'usage : une photo d'hiver et une photo d'été ne montrent pas le même bâti, et une
qualification fondée sur une image sans date n'est pas reproductible.

### N5 — Frontend mobile minimal

Consultation, changement de statut et prise de note sur le terrain. Mentionné dans v0.7. Utile
pendant [G8](./G8-pilote-trois-professionnels.md) si les professionnels visitent des biens.

### N6 — Instrumentation OpenTelemetry

API, psycopg, frontend carte. Explicitement non bloquant pour le pilote : voir
[G7](./G7-observabilite-minimale.md), qui se contente de Prometheus, des journaux et du `request_id`.
À faire une fois le système en conditions réelles, quand on sait quelles traces sont utiles.

### N7 — Promouvoir RNB, BAN et marché en assets Dagster

Suppression des scripts one-shot. Traité comme dette identifiée dans
[BUG-02](./BUG-02-scripts-import-hors-dagster.md), à faire **avant** [G1](./G1-extension-22-29-56.md)
plutôt qu'après : l'extension régionale sans pipelines partitionnés est ingérable.

### N8 — ADR sur le frontend

Décider explicitement : conserver le CSS actuel, ou converger vers MUI / TanStack Query / Zustand.
**Pas les deux.** Tant que la décision n'est pas prise, la règle reste : rester cohérent avec
l'existant (`App.tsx`, CSS custom, MapLibre) et n'introduire aucune bibliothèque pendant le chemin
critique données.

## Could — hors chemin critique, derrière feature flags

### N9 — FR-016 Indice expérimental de vacance

Isolé, désactivable, hors du score principal, **jamais présenté comme une certitude**. Le produit ne
prédit pas la vacance : c'est un interdit explicite. Un indice expérimental ne peut exister que
clairement séparé, et son absence de fiabilité doit être visible par l'utilisateur.

### N10 — Comparaison temporelle d'orthophotos

Dépend de N4 pour la traçabilité des millésimes.

### N11 — Détection visuelle assistée

Vision, PyTorch. `ARCHITECTURE.md` §21, hors MVP. Rappel : pas de ML en production au MVP.

### N12 — Intégration CRM

À n'envisager qu'après une intention de payer confirmée en [G8](./G8-pilote-trois-professionnels.md)
(H5), et selon les outils réellement utilisés par les professionnels du pilote.

### N13 — Elasticsearch / OpenSearch

**Seulement si** PostgreSQL et `pg_trgm` ne suffisent plus, et seulement sur mesure. La recherche
d'adresse de [C1](./C1-recherche-adresse-reelle.md) doit être mesurée sur les 437 441 adresses du 35
avant que la question se pose. Introduire un moteur de recherche sans cette mesure serait une
complexité non justifiée.

## Hors périmètre — ne pas faire

France entière, marketplace, API commerciale publique, scraping de propriétaires, prospection
automatisée, recommandation d'achat autonome, PLU opposable, prédiction certaine de vente ou de
vacance, LOVAC ou données propriétaires sans droit, DPE simulés, ML en production, Kubernetes,
scoring à la requête, GeoJSON régional dans MapLibre, secrets en clair.
