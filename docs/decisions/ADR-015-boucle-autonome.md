# ADR-015 — Ce qui arrête une boucle de développement autonome

**Date :** 15 septembre 2026

**Contexte.** Les tickets sont de plus en plus souvent menés de bout en bout par un agent. La
question n'est pas s'il peut écrire le code — il le fait — mais à quoi il s'arrête. Les trois
défauts structurels de v0.3 donnent la mesure du problème : BUG-09, 1,24 M de relations toutes
déclarées certaines ; BUG-10, plus personne ne pouvait se connecter ; BUG-12, un comptage faux de
44 % publié dans un rapport cohérent avec lui-même. Aucun n'a été vu par les tests. Tous ont été
vus par B4, une revue menée contre les sources.

**Alternatives écartées.**

- *Un agent validateur après chaque étape.* Un relecteur qui dispose du même contexte que le
  producteur valide la cohérence interne — ce que `make check` fait déjà, en reproductible et pour
  rien. Pire, il délivre une assurance qui décourage le contrôle qui, lui, attrape quelque chose.
- *Faire juger à l'agent s'il a besoin d'un humain.* Demander à un agent sous pression
  d'achèvement s'il doit s'interrompre, c'est obtenir non.
- *Une revue humaine à chaque étape.* Le coût rendrait la boucle sans objet, et diluerait
  l'attention là où elle est irremplaçable.

**Décision.** Trois natures de contrôle, distinctes et non interchangeables.

1. **Déterministe**, à chaque étape : `make check` — qui inclut `make invariants`, les interdits de
   `CLAUDE.md` vérifiés sur les lignes ajoutées du diff —, `make backlog-check`, `make dod`. Le
   mode d'échec d'une boucle autonome n'est pas l'erreur, c'est l'arrangement : assouplir un test
   plutôt que corriger, convertir une valeur manquante en zéro, figer un alias `latest`. Chacun de
   ces gestes produit un `make check` vert et une donnée fausse.
2. **Adversarial**, quand l'étape publie un chiffre : un agent **recalcule depuis les sources sans
   lire le code** qui a produit le chiffre. L'isolement est la décision, pas le second regard : un
   relecteur qui lit le code du producteur refait son raisonnement et retrouve son erreur.
3. **Humain**, quand le verdict porte sur l'exactitude dans le monde réel ou sur un arbitrage
   produit. Le verrou est **déclaré dans le ticket** — `**Nature :**`, `**Preuve :**` — et dérivé
   comme l'est déjà la disponibilité. Un ticket verrouillé n'est jamais annoncé « prêt », sort des
   lots menables de front, et ne se clôt pas sans le document qui porte son verdict.

**Conséquences.**

- Le verrou est une propriété de la donnée du backlog, jamais une appréciation portée en cours de
  route. Il survit donc à l'agent qui le rencontre.
- Tout contrôle automatique porte une échappatoire explicite — `invariant-ok: <raison>`,
  `**DoD :** … sans objet` — et des motifs calibrés à zéro signalement sur l'historique. Un
  contrôle bruyant est un contrôle désactivé au premier faux positif.
- Ce qui n'est pas mécanisable est affiché comme tel plutôt que déclaré vert : `make dod` ne juge
  pas le point 7 de la DoD, il liste les tickets débloqués à relire.
- Rien de tout cela ne remplace A1. Ces contrôles tournent en local ; tant qu'un run GitHub n'est
  pas attaché, la boucle n'a que son propre témoignage.
