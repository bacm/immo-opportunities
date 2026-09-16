# ADR-019 — Le gel de la plateforme est levé

**Date :** 16 septembre 2026

**Contexte.** ADR-016 a gelé la plateforme — Explorer, API, moteur de score, workflow,
administration régionale, infrastructure — jusqu'au verdict de H3, et n'en permettait le dégel
qu'après une demande chiffrée d'un professionnel. Le jour même, ADR-018 a dû ouvrir une exception
pour rendre l'Explorer utilisable, et annonçait qu'il en faudrait une nouvelle à chaque
changement. Le porteur du projet tranche le 16 septembre : le gel bloque, et il préfère avancer
sur la plateforme pour voir où le produit mène plutôt qu'attendre les entretiens.

**Alternatives écartées.**

- *Garder le gel jusqu'à H3.* C'était la position d'ADR-016 et la recommandation de l'agent. Le
  porteur l'écarte : H3 dépend de rendez-vous qu'il ne maîtrise pas, et le travail sur la
  plateforme s'arrête d'ici là.
- *Dégeler écran par écran, une ADR à chaque fois.* C'est la voie d'ADR-018. Elle ralentit chaque
  changement sans protéger mieux que les règles de données, qui restent en vigueur.

**Décision.**

1. **Le gel est levé.** `apps/web/`, `backend/src/immo/api/`, le moteur de score, `infra/`,
   `config/` et les fichiers Compose se modifient sous ticket ordinaire. Une dépendance, une
   table, un service ou un contrat publié restent des décisions, comme partout ailleurs.
2. **Les tickets suspendus par ADR-016** (D6, E1 à E7, F1 à F3, G1 à G8, BUG-02, BUG-08, BUG-11,
   BUG-13, D7, A6, G6, G7) redeviennent disponibles selon leurs dépendances. Aucun ordre n'est
   imposé entre le baromètre et la plateforme.
3. **Ce qui ne change pas.** V5 reste le premier produit, H3 et H4 restent les verrous du radar.
   Les interdits de `SPEC.md` §13 et §18 et le hors-périmètre de §6.4 s'appliquent à la
   plateforme comme au baromètre. Aucun score n'est publié sans profiling écrit.
4. **Deux garde-fous restent, parce qu'ils ne tenaient pas au gel.** Aucun déploiement accessible
   à un tiers avant les conditions d'`ARCHITECTURE.md` §25.2 : 41 routes sur 45 sont anonymes et
   l'API se connecte avec le rôle propriétaire. Aucune fiche de mutations par parcelle n'est
   montrée à un tiers avant l'avis de H4 (`SPEC.md` §18.4).
5. **Ce que cette ADR remplace.** Le point 3 d'ADR-016, et ADR-018 en entier. Les points 1, 2 et
   4 d'ADR-016 restent valides. Les écrans retirés par C4 ne reviennent pas d'office : ils se
   reprennent de l'historique, par ticket, quand un score publié leur donne quelque chose à
   montrer.

**Conséquences.**

- **La raison du gel n'est pas levée avec lui.** L'objet « bien » reste inconstructible avec les
  données autorisées (`SPEC.md` §10, BUG-11), et le moteur n'a jamais été appelé. Le premier
  ticket de plateforme qui score une parcelle rencontrera ce mur. C'est un risque assumé, écrit
  ici pour qu'on le reconnaisse le moment venu.
- `CLAUDE.md`, `SPEC.md` et `ARCHITECTURE.md` décrivent la plateforme comme existante et
  défectueuse, plus comme gelée ; §11.3 de la spec porte les deux garde-fous du point 4.
- Le temps passé sur la plateforme n'est pas passé sur H3. La question de §21 — poursuivre,
  bifurquer ou arrêter après H3 — reste ouverte.
