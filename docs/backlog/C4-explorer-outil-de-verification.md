# C4 — L'Explorer devient l'outil local de vérification des données, sans bouton mort

**Version :** transverse · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** apps/web/, SPEC.md, ARCHITECTURE.md, docs/decisions/ADR-018-degel-restreint-explorer.md
**Dépend de :** — · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « revoir complètement l'interface car on a
des boutons morts et surtout une UX qui est vraiment pas terrible » ; voie retenue par le porteur :
dégel restreint par ADR.
**DoD :** preuve sans objet — aucun chiffre publié ; l'ADR-018 et les tests e2e portent la preuve

## Contexte à charger

- `SPEC.md` §6.2, §6.4, §11.3, §13.7, §15 — ces sections seulement
- `ARCHITECTURE.md` §6
- [ADR-018](../decisions/ADR-018-degel-restreint-explorer.md)
- `apps/web/src/App.tsx`, `apps/web/src/RealMap.tsx`, `apps/web/tests/e2e/`

## Constat, capturé le 16 septembre 2026 sur la base locale

- **Boutons sans effet** : « Aide », l'avatar de la barre latérale, « Paramètres », le bouton de
  profil (sa déconnexion ne fait rien quand l'authentification est désactivée en local).
- **Boutons qui échouent** : « Pilote » répond « Authentication required » ; « Sauvegarder » une
  recherche répond 401.
- **Un tiers de l'écran toujours vide** : la liste de candidats et ses filtres (stratégie, score,
  confiance), faute de score publié ; le panneau de droite invite à « sélectionner un candidat »
  qui n'existe pas.
- **Carte vide à l'ouverture** : une URL sans `lon`/`lat`/`z` ouvre la carte à 0, 0
  (`Number(null) === 0`) ; et sous le zoom 13, où les parcelles ne sont pas servies, rien ne le
  dit.
- **Sélecteur de département** 22, 29, 56 : rien n'y est importé, et l'extension est hors
  périmètre (`SPEC.md` §6.4).
- Défauts connus d'`ARCHITECTURE.md` §6.3.

## Choix retenus

- **Décision** : ADR-018, dégel restreint de `apps/web/` à ce ticket ; `SPEC.md` §6.2 et §11.3
  et `ARCHITECTURE.md` §6 et §23 amendés en conséquence.
- **Retiré du front** (API, moteur et backend intacts, code récupérable par ce commit) : liste,
  filtres et fiche candidat, recherches sauvegardées, couche `opportunities`, panneau « Pilote »,
  sélecteur de département, « Aide », avatar, « Paramètres », libellé « Données réelles ».
- **Gardé** : recherche, carte parcelles et bâtiments avec orthophoto, fiches adresse, parcelle
  et bâtiment, mutations DVF, diagnostics DPE, bannière de couverture, revue B4.
- **Mise en page** : deux colonnes, carte et fiche ; la fiche vide explique quoi faire (chercher
  ou cliquer une parcelle). Barre latérale réduite à deux vues, « Carte » et « Revue ».
- **Déconnexion** : affichée seulement quand l'authentification OIDC est active ; en local elle
  n'existe pas, le bouton ne s'affiche donc pas.
- **Carte vide sous le zoom 13** : un bandeau le dit et propose de zoomer, au lieu d'un fond uni.
- **Vue initiale** : un paramètre `lon`, `lat` ou `z` absent ou vide retombe sur Rennes, jamais
  sur 0 (`Number(null) === 0`).
- **Mutations et diagnostics** : une réponse en erreur s'affiche « service indisponible », plus
  « aucune mutation » ; les deux blocs passent par le client `api.ts`.
- **Typographie** : aucun texte sous 12 px.
- **Revue B4** : `<dialog>` natif ouvert par `showModal()`, qui gère le piège de focus et la
  touche Échap sans bibliothèque.
- **Bannière de couverture** : textes réécrits pour la vérification (« une absence dans une
  fiche signifie… »), plus de « candidat ».
- **Hors ticket** : renouvellement OIDC silencieux (§6.3), aucun code hors `apps/web/`, aucune
  dépendance ajoutée, captures C3 de `docs/data/captures/` laissées telles quelles comme preuve
  datée de v0.4.

## Critères d'acceptation

- aucun bouton visible sans effet, test e2e à l'appui ;
- aucun appel réseau vers `/api/v1/opportunities`, `/api/v1/admin/*` ou `/api/v1/saved-searches`
  au chargement ;
- la vue initiale sans paramètre est Rennes, et la carte sous zoom 13 l'annonce ;
- un 500 sur les mutations s'affiche comme une indisponibilité, pas comme une absence ;
- la revue se ferme par Échap ;
- `make check` vert, `pnpm test:e2e` vert sur la base locale.

## Vérification — 16 septembre 2026

- `pnpm test:e2e` sur la base locale : 15 réussis, 2 sautés par leur garde (« échantillon
  entièrement jugé », l'échantillon B4 n'a plus de cas ouvert) ;
- nouveaux tests : inventaire exhaustif des boutons de l'écran d'accueil et effet de chacun,
  absence d'appel à la plateforme gelée, vue initiale, bandeau de zoom, panne distincte d'une
  absence, fermeture de la revue par Échap ;
- `make check` vert ; `make dod ID=C4` sans échec.
