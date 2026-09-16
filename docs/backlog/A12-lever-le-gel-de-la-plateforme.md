# A12 — Lever le gel de la plateforme

**Version :** transverse · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** CLAUDE.md, SPEC.md, ARCHITECTURE.md, README.md, DEPLOYMENT.md, map/README.md, contracts/, docs/decisions/ADR-019-lever-le-gel-de-la-plateforme.md, apps/web/src/
**Dépend de :** C4 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « faisons sauter le gel, ça bloque et je
préfère voir où le produit nous mène » ; décision du porteur du projet.
**DoD :** test sans objet — décision et documentation, aucun comportement ne change ; preuve sans objet — aucun chiffre, l'ADR-019 est le livrable

## Contexte à charger

- [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md), point 3
- [ADR-018](../decisions/ADR-018-degel-restreint-explorer.md)
- `SPEC.md` §1, §6, §9.3, §10, §11, §13.3, §13.5, §15 à §19, §21, §23, §24, §26, §28
- `ARCHITECTURE.md` §1, §3, §6 à §8, §12, §22, §23, §25
- `CLAUDE.md`, section « Garde-fous »

## Choix retenus

- **Décision** : ADR-019 lève le gel ; elle remplace le point 3 d'ADR-016 et ADR-018.
- **Ce qui devient modifiable sous ticket ordinaire** : `apps/web/`, `backend/src/immo/api/`, le
  moteur de score, `infra/`, `config/`, les fichiers Compose. La règle « décision ou
  implémentation » de `CLAUDE.md` s'y applique comme partout : une dépendance, une table ou un
  service restent des décisions.
- **Ce qui ne bouge pas** : V5 reste le premier produit et H3, H4 les verrous du radar ; les
  interdits de `SPEC.md` §13 et §18 ; le hors-périmètre de §6.4 ; aucun score publié sans
  profiling écrit ; pas de ML, de Kubernetes ni de Celery.
- **Deux garde-fous gardés, parce qu'ils ne tenaient pas au gel** : aucun déploiement accessible
  à un tiers avant les conditions d'`ARCHITECTURE.md` §25.2 (renommée « conditions de
  déploiement ») ; aucune fiche de mutations par parcelle montrée à un tiers avant H4
  (`SPEC.md` §18.4).
- **Ordre** : aucun ordre imposé entre baromètre et plateforme ; la disponibilité reste dérivée du
  graphe par `make backlog`. Les tickets suspendus par ADR-016 redeviennent disponibles.
- **Écrans retirés par C4** : ils restent retirés ; ils se reprennent de l'historique, par ticket,
  quand un score publié leur donne quelque chose à montrer.
- **Documents** : les sections « gelées » deviennent descriptives (ce qui existe, ce qui est
  défectueux) ; les tickets clos et l'audit gardent leur texte d'époque ; les versions v0.5 à
  v0.8 passent de `Gelée` à `À faire`.
- **H8** : sa décision reste humaine ; une note datée signale que le gel n'est plus un obstacle,
  §7.5 si.

## Critères d'acceptation

- plus aucune mention d'un gel en vigueur dans `CLAUDE.md`, `SPEC.md`, `ARCHITECTURE.md`,
  `README.md`, `DEPLOYMENT.md`, `docs/backlog/README.md`, `docs/versions/README.md` ;
- les deux garde-fous gardés sont écrits dans `SPEC.md` §11.3 ;
- `make check`, `make backlog-check`, `make ticket-check` verts.
