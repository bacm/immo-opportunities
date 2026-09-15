# Immo Opportunities

Monorepo B2B de détection et qualification de candidats immobiliers off-market en Bretagne
(22, 29, 35, 56).

Le produit aide un **marchand de biens ou investisseur-rénovateur** à classer des actifs à
approfondir selon deux stratégies : division/extension et rénovation-revente.

Ce n'est **pas** une prédiction de vente, **pas** une détection de vacance, **pas** une décision
urbanistique opposable.

**Répondre et documenter en français.**

## État au 15 septembre 2026

Le logiciel MVP est largement écrit — API, Explorer, OIDC, RLS, moteur de score, administration.
**Personne ne l'a vu, aucun score n'est publié, et le moteur de score n'a aucun appelant.**
L'audit du 15 septembre ([`docs/audit-critique-2026-09-15.md`](docs/audit-critique-2026-09-15.md))
établit que la définition initiale n'est pas tenable avec les données autorisées : l'objet
« bien » se réduit à la parcelle, « off-market » suppose un propriétaire exclu par la spec, et la
rénovation-revente est infondée par les données du projet (décote énergétique de 3 à 4 %).

**[ADR-016](docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md) redéfinit le produit :**
une intelligence de marché d'abord (V5, un baromètre du 35 par EPCI, reproductible, sans
plateforme), un radar hebdomadaire de mise en vente ensuite (V2), derrière un avis juridique et
des entretiens. **La plateforme est gelée** : D6, E1 à E7, F1 à F3, G1 à G8 et la dette
transverse sont suspendus, pas abandonnés, jusqu'au verdict de H3.

| Ce qui existe | État |
|---|---|
| v0.1 à v0.5 | Terminées : référentiel spatial 35, adresse réelle, quatre sources métier importées |
| v0.6 à v0.8 | Codées ou spécifiées, **gelées par ADR-016** |
| Sources acceptées | DS-01 Cadastre, DS-02 RNB ; **toutes les autres en `display_only`** |
| Base locale | 29 Go pour le seul 35 ; 1 333 327 unités, 20 M de valeurs de features, 285 k mutations, 208 k DPE |

### Ce que le référentiel a établi, à ne pas redécouvrir

Résultats négatifs mesurés : la relation adresse ↔ parcelle n'est vérifiable par aucune règle
géométrique, ~24 % d'erreur irréductible ; l'unité foncière est dégénérée à une parcelle par unité
(BUG-11) et la contiguïté ne peut y suppléer ; le DPE se rattache au bâtiment à 59 % ; 65 % des
mutations DVF n'ont pas de prix allouable ; aucune zone inondable typée sur le 35.

Résultats positifs mesurés, non recomptés : le dépôt d'un DPE prédit une mutation à douze mois à
35 % contre 3 % de base (lift × 11,8, deux cohortes) ; sur 7 024 paires de reventes, la plus-value
nette est × 1,90 sous 60 % du prix de marché et × 1,01 au prix. Voir
`docs/data/dpe-signal-vente-35.md` et `docs/data/pistes-analyse-marche-35.md`.

### Le chemin critique tient en une phrase

> Produire le baromètre du 35, le mettre entre les mains de cinq professionnels, obtenir un avis
> juridique, puis lancer le radar. Rien d'autre.

Si on demande « le plus important maintenant » : **H1, le baromètre du marché du 35.** Sans lui,
aucun entretien n'a de prétexte et aucun prix ne peut être posé.

## Carte du contexte — à lire avant de charger quoi que ce soit

`SPEC.md` (67 Ko) et `ARCHITECTURE.md` (41 Ko) coûtent ~27 000 tokens à eux deux.
**Ne pas les charger par défaut.**

| Tâche | Charger |
|---|---|
| Implémenter un ticket | [`docs/backlog/<ID>-*.md`](docs/backlog/) — son bloc « Contexte à charger » liste les 3 à 5 fichiers nécessaires. Rien d'autre. |
| Savoir quoi faire ensuite | [`docs/backlog/README.md`](docs/backlog/README.md), colonne « Disponibilité » |
| Vérifier ce qui est prouvé | [`docs/data/mvp-dod-traceability.md`](docs/data/mvp-dod-traceability.md) |
| Périmètre produit, FR-*, DS-* | `SPEC.md` — **la section concernée seulement** |
| Choix technique, interdits, état courant | `ARCHITECTURE.md` — **la section concernée seulement** |
| Pourquoi une décision a été prise, et contre quoi | [`docs/decisions/`](docs/decisions/) — le fichier de l'ADR concerné, jamais le dossier entier |

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
- **Tout pipeline prévoit la variété de sa source avant son premier lot.** Inventorier sur un
  échantillon dispersé, faire échouer un élément sans faire échouer le lot, distinguer l'échec
  passager du défectueux, temporiser face à un service public. Voir `ARCHITECTURE.md` §10.6.
- **La clé d'idempotence et l'identifiant de run d'un import portent la version de
  transformation.** Sans elle, une release déjà importée est rejouée à vide et un correctif de
  code n'atteint jamais les données — constaté sur BUG-09.

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
H1 baromètre 35 → H2 document publiable → H3 cinq entretiens ─┬─► H5 radar (après H4 avis juridique)
                                                              └─► H6 SPEC.md réécrit
```

Ne pas sauter une étape. **Aucune ligne dans le front, l'API, l'infrastructure ni le moteur de
score tant que H3 n'a pas rendu son verdict.** Les tickets des séries D, E, F, G et la dette
transverse sont gelés par ADR-016 ; E9 reste disponible mais hors chemin critique, et son
protocole doit être corrigé avant usage (audit §3.4).

Les nice-to-have ne démarrent pas avant qu'un abonné du 35 existe — voir
[`docs/backlog/NICE-backlog.md`](docs/backlog/NICE-backlog.md).

## Toute modification passe par un ticket

Une demande qui touche le code, un schéma, l'infrastructure ou le comportement de l'application
s'ouvre en ticket **avant la première ligne modifiée** — y compris une demande directe en cours de
conversation. Le ticket peut être minimal ; ce qu'il doit porter, c'est la demande et **les choix
retenus**. C'est lui qui réserve les chemins, qui rend `make dod` applicable, et qui fait qu'une
décision est retrouvable ailleurs que dans un message de commit.

Seul `docs/` en est dispensé : le backlog, les preuves, les versions et les décisions sont la
sortie du processus, pas son objet — ouvrir un ticket ne peut pas demander un ticket. `SPEC.md`,
`ARCHITECTURE.md` et `CLAUDE.md` en demandent un.

Le critère porte sur les **chemins touchés**, jamais sur l'importance qu'on prête au changement :
juger « c'est trop petit pour un ticket » est une appréciation portée par celui-là même que la
règle contraint, sous pression d'achèvement. `make ticket-check` le vérifie — le sujet du commit
porte un identifiant connu du backlog, `D5 — …`, `D1, D6a — …`, selon la convention dont `make dod`
dépend déjà. Échappatoire explicite `ticket-ok: <raison>` dans le corps du message.

**Un manque n'est pas une décision.** Combler un écart qu'un ticket a déjà tranché — un critère
d'acceptation écrit mais non câblé, un contrôle outillé mais branché nulle part — n'ouvre pas de
ticket : le commit porte l'identifiant de **ce** ticket-là, et reste donc attribué, visible de
`make dod` et de `make ticket-check`.

Le test n'est pas « est-ce petit ? » mais : *puis-je désigner le ticket, l'ADR ou le critère que ce
changement se contente d'honorer ?* Si oui, c'est un manque — il est déjà écrit, on ne fait que le
rendre vrai. Sinon, c'est une décision, et une décision que personne n'a écrite ne se retrouve
nulle part.

## Definition of Done d'une tâche

Terminé **seulement si** :

1. test automatisé ajouté ou étendu ;
2. preuve écrite dans `docs/data/` ou `contracts/` ;
3. `make openapi` régénéré si l'API change ;
4. `make check` vert ;
5. aucune donnée simulée présentée comme réelle ;
6. l'état du ticket est mis à jour **dans son propre fichier**, puis `make backlog` ;
7. les dépendances des tickets que celui-ci débloque sont **relues** : une dépendance qui n'a plus
   d'objet se retire, sans quoi elle allonge le chemin critique indéfiniment.

`make dod ID=<ticket>` vérifie ce qui est mécanisable de ces sept points sur le diff du ticket, et
dit lesquels il ne peut pas vérifier plutôt que de les déclarer verts. Le point 7 n'est pas
mécanisable : le script affiche les tickets débloqués, il ne les juge pas.

Un ticket qui n'a légitimement ni test ni preuve — documentation pure — le déclare dans son en-tête
par `**DoD :** test sans objet — <raison>` ou `preuve sans objet — <raison>`. Une dérogation écrite
dans le ticket, pas une case décochée en silence.

## Boucle de développement et verrous

Trois natures de contrôle, distinctes et non interchangeables. Un agent validateur après chaque
étape n'en est pas une : relire un diff avec le même contexte que son auteur valide la cohérence
interne, ce que `make check` fait déjà, en reproductible.

| Nature | Quoi | Quand |
|---|---|---|
| Déterministe | `make check` — qui inclut `make invariants` —, `make backlog-check`, `make dod` | à chaque étape |
| Adversarial | compétence `recompte-preuve` : recalculer depuis les sources, **sans lire le code** qui a produit le chiffre | quand l'étape écrit une volumétrie ou un taux dans `docs/data/` ou `contracts/` |
| Humain | les tickets de `**Nature :**` humaine | verdict sur l'exactitude dans le monde réel, ou arbitrage produit |

`make invariants` vérifie les interdits ci-dessus sur les **lignes ajoutées** du diff : valeur
manquante convertie en zéro, alias `latest`, seuil littéral dans le moteur, donnée simulée, test
désactivé ou assertion supprimée. Le mode d'échec d'une boucle autonome n'est pas l'erreur, c'est
l'arrangement. Une ligne légitimement signalée se justifie sur place : `invariant-ok: <raison>`.

**La boucle s'arrête** — et rend la main plutôt que de contourner — sur :

- un ticket de nature humaine, annoncé **verrou humain** et jamais « prêt » ;
- deux échecs consécutifs du même gate sur le même ticket : au troisième essai, on ne corrige plus,
  on contourne ;
- une décision que `SPEC.md` ne tranche pas ;
- une source externe indisponible ou un quota atteint — temporiser, jamais substituer une fixture ;
- une contradiction entre deux sources de vérité.

L'arrêt est explicite et bruyant. Une boucle qui s'arrête en silence ressemble à une boucle qui
travaille.

## Commandes

```bash
make dev                  # infrastructure locale
make rebuild              # reconstruit les images — obligatoire après tout changement backend
make check                # lint, typecheck, tests, OpenAPI
make openapi              # régénère le contrat et le client TypeScript
make migrate              # migrations Alembic
make backlog              # régénère le tableau de suivi depuis les en-têtes de tickets
make invariants           # interdits vérifiés sur les lignes ajoutées du diff — BASE=<ref>
make doc-budget           # plafond de lignes des documents de référence
make dod ID=<ticket>      # ce qui est mécanisable des sept points de la DoD
make ban-import           # import BAN   (voir aussi rnb-import, cadastre-fixture)
make physical-buildings   # regroupe les enregistrements en bâtiments physiques
make morphology-features  # matérialise LAND-*/BLD-* sur les releases acceptées
```

**`make rebuild` recrée PostgreSQL et coupe tout travail en cours.** Un import qui tourne est
interrompu par un `rebuild` lancé pour un autre ticket — la contention entre travaux parallèles ne
porte pas que sur les fichiers. Vérifier qu'aucun import n'est en cours avant de reconstruire.

**Le front servi n'est pas celui que Playwright teste.** Les tests e2e tournent contre un serveur
Vite lancé depuis le dépôt ; le navigateur, lui, reçoit un bundle figé au build du conteneur `web`.
Un test vert ne prouve donc rien sur ce que voit l'utilisateur. Après un changement de front :
`docker compose … up -d --build web`, puis vérifier sur `http://localhost:8080` — **avec ce nom
d'hôte**, Caddy ne répondant pas sur `127.0.0.1`.

**Les conteneurs embarquent une copie du code figée au build.** `compose.dev.yaml` ne monte pas
les sources : un changement backend demande `make rebuild`, pas un `docker compose restart`. Et
`docker compose` sans les trois `-f` recrée les conteneurs hors configuration de développement.

## Suivi du backlog

L'état d'un ticket vit **à un seul endroit** : la ligne `**État :**` de son fichier dans
`docs/backlog/`. Valeurs autorisées : `À faire`, `En cours`, `Terminé`, `Abandonné`.

`**Nature :**` vaut `implémentation` (défaut), `revue humaine` ou `décision humaine`. Les deux
dernières sont des **verrous** : le ticket n'est jamais annoncé « prêt », il sort des lots menables
de front, et il déclare par `**Preuve :**` le chemin du rapport ou de la décision attendue — fichier
qui doit exister pour que `Terminé` soit accepté.

Le verrou est une propriété **déclarée** du ticket, jamais une appréciation portée en cours de
route : demander à un agent s'il a besoin d'un humain revient à lui demander de s'interrompre alors
qu'il est sous pression d'achèvement. Il répondra non.

La colonne « Disponibilité » du README est **dérivée** du graphe de dépendances — ne jamais la
saisir à la main. `make backlog` régénère le tableau après tout changement d'état ;
`make backlog-check` signale s'il est périmé. Volontairement **hors de `make check`** : la
cohérence documentaire ne doit pas bloquer la CI de code.

Les fichiers `docs/versions/` et `docs/data/mvp-dod-traceability.md` ne se mettent à jour qu'à la
clôture d'une **version**, pas d'un ticket.

## Sous-agents et parallélisation

- **Oui** pour la recherche en fan-out (« où est implémenté X ») : on garde la conclusion, pas les
  fichiers.
- **Oui** pour les tickets d'un même **lot menable de front** — section générée en bas de
  [`docs/backlog/README.md`](docs/backlog/README.md).
- **Non** sur le chemin critique séquentiel : la continuité y coûte moins cher que la relecture.
- Un sous-agent doit recevoir l'ID du ticket et son bloc « Contexte à charger », sinon il produit
  du hors-sujet.

### « Disponible » ne veut pas dire « parallélisable »

La colonne « Disponibilité » dérive du graphe de dépendances : elle dit ce qui *peut commencer*.
Elle ne dit pas ce qui peut commencer **ensemble** — deux tickets sans lien de dépendance peuvent
très bien écrire dans le même fichier.

D'où le champ `**Touche :**` dans l'en-tête de chaque ticket : les chemins qu'il va **écrire**,
distincts de « Contexte à charger » qui dit ce qu'il faut lire. `make backlog` en dérive :

- les **lots menables de front**, dont les tickets n'ont aucun chemin commun ;
- les tickets **déjà démarrés**, qui occupent leurs chemins ;
- les tickets prêts mais **retenus** par un travail en cours.

Un ticket sans `Touche` déclaré est isolé par précaution et signalé — l'oubli coûte de la
parallélisation, il ne produit pas de collision.

### Deux disciplines sans lesquelles rien de tout cela ne tient

1. **Passer un ticket à `En cours` en le commençant**, pas en le finissant. C'est ce qui réserve
   ses chemins ; un ticket travaillé mais resté `À faire` est invisible et un second agent ira
   écrire au même endroit.
2. **À la clôture d'un ticket, réexaminer ce qu'il débloque.** Une dépendance héritée de l'ordre
   de rédaction survit tant que personne ne la relit — `D3` attendait `D2` pour un module déjà
   livré, `D4` attendait `D3` sans qu'aucune ligne ne le justifie. Les deux allongeaient le chemin
   critique pour rien.
