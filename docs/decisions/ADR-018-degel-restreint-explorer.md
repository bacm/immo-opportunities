# ADR-018 — Dégel restreint de l'Explorer : un outil local de vérification, sans bouton mort

**Date :** 16 septembre 2026
**Remplacée :** par [ADR-019](./ADR-019-lever-le-gel-de-la-plateforme.md), le 16 septembre 2026. Le dégel restreint n'a plus d'objet ; ce que C4 a fait reste en place.

**Contexte.** ADR-016 gèle la plateforme jusqu'au verdict de H3, et `SPEC.md` §11.3 ne lève le
gel qu'après H3, sur demande chiffrée d'un professionnel. Pourtant l'Explorer n'est pas inerte :
`SPEC.md` §15 le garde servi en local pour vérifier les données, et c'est ce qu'il fait — les
mutations DVF (D6a) et les diagnostics DPE (D6b) par parcelle, la revue B4, les fiches adresse.
Le porteur l'utilise, et le trouve mauvais : des boutons sans effet (« Aide », avatar,
« Paramètres »), d'autres qui échouent en local (« Pilote », « Sauvegarder »), un tiers de l'écran
consacré à une liste de candidats vide par construction, une carte vide à l'ouverture. Un outil
de vérification qui montre des contrôles morts entame la confiance dans ce qu'il vérifie.

**Alternatives écartées.**

- *Attendre H3.* Laisse l'outil dont dépend la vérification des données dans un état que son
  seul utilisateur juge mauvais, pour protéger des écrans qu'aucune donnée n'alimente.
- *Dégel complet et refonte UX de la plateforme.* Revient sur ADR-016 sans le fait nouveau
  qu'exige §11.3 : aucun professionnel n'a demandé de carte ni de fiche.
- *Masquer les écrans gelés derrière un drapeau.* Garde 700 lignes inatteignables et un
  paramètre qui n'a qu'une valeur utile.

**Décision.**

1. **L'Explorer est l'outil local de vérification des données du 35**, et rien d'autre tant que
   H3 n'a pas rendu son verdict. Le dégel porte sur `apps/web/` seul, et sur le ticket
   [C4](../backlog/C4-explorer-outil-de-verification.md) seul.
2. **Ce qui sert la plateforme gelée sort du front** : liste, filtres et fiche candidat,
   recherches sauvegardées, couche des opportunités, panneau d'administration régionale,
   sélecteur de département. L'API, le moteur de score et le backend ne changent pas ; le code
   retiré se récupère dans l'historique au commit de C4, et un dégel complet le reprendra.
3. **Ce qui est gardé** : recherche, carte, fiches adresse, parcelle et bâtiment, mutations,
   diagnostics, couverture, revue B4. Seuls s'y ajoutent les défauts d'`ARCHITECTURE.md` §6.3
   qui touchent ces écrans ; aucune fonctionnalité nouvelle.
4. **Ce que le dégel n'ouvre pas** : aucune ligne dans `backend/src/immo/api/`, le moteur,
   `infra/`, `config/` ni Compose ; aucune dépendance ; aucun déploiement ; aucune reprise de
   l'authentification. La pile reste `App.tsx`, CSS écrite à la main et MapLibre
   (`ARCHITECTURE.md` §6.4).

**Conséquences.**

- `SPEC.md` §6.2 et §11.3 citent cette exception ; `ARCHITECTURE.md` §6 décrit l'outil réduit.
- Un dégel complet, après H3, repart de l'historique et non de l'écran actuel.
- Tout autre changement dans `apps/web/` demande de nouveau une ADR.
