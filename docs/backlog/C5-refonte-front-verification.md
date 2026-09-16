# C5 — Refondre le front : un socle commun et des fiches de vérification lisibles

**Version :** transverse · **Taille :** L · **État :** Terminé
**Nature :** implémentation · **Touche :** apps/web/
**Dépend de :** C4 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « quid de la refonte du front » ; le porteur
veut le socle commun **et** la refonte du contenu propre à la vérification (fiches détaillées,
ventes DVF, DPE, revue), même si ce contenu ne sert pas au professionnel et ne peut pas lui être
montré avant H4.
**DoD :** preuve sans objet — aucun chiffre publié ; les tests e2e portent la preuve

## Contexte à charger

- `SPEC.md` §11.3, §13.7, §15, §18.4 — ces sections seulement
- `ARCHITECTURE.md` §6
- [ADR-019](../decisions/ADR-019-lever-le-gel-de-la-plateforme.md), [ADR-020](../decisions/ADR-020-unite-analysee-parcelle.md)
- `apps/web/src/`, `apps/web/tests/e2e/`

## Ce qui ne change pas

- Tout reste local : les mutations par parcelle ne sont montrées à aucun tiers avant H4 (§18.4).
- Les règles déjà portées par l'écran : inconnu jamais rendu comme zéro, panne distincte
  d'absence, adresse sans position qui ne recentre pas la carte, appariement ambigu ou rejeté
  visible, aucun prix au m² dérivé, aucune couleur A à G sur les étiquettes DPE, plafond de 50
  diagnostics annoncé, décision du moteur absente de la revue.
- Pile : React, CSS écrite à la main, MapLibre ; aucune dépendance ajoutée ; aucune ligne hors
  `apps/web/`.

## Choix retenus

- **Découpage** : `App.tsx` ne garde que la coquille et l'état de navigation ; recherche,
  bandeau de couverture, fiches, blocs ventes et DPE, revue et utilitaires de format vivent dans
  leurs fichiers.
- **Système visuel** : jetons de couleur, d'espacement et de rayon dans `:root`, composants de
  base partagés (état vide, pastille, onglets, liste de faits).
- **Fiche parcelle** : titre « Section AB · n° 303 » et commune, identifiant complet dessous ;
  chiffres clés (surface calculée, surface déclarée, bâtiments) ; onglets Aperçu, Ventes DVF,
  Diagnostics DPE, Sources, avec leur effectif dès l'ouverture.
- **Ventes et DPE chargés à l'ouverture de la fiche**, plus au clic : un appel local par bloc, et
  l'effectif dans l'onglet évite d'ouvrir pour rien. La fiche est remontée à chaque changement
  d'entité (`key`), ce qui remplace le vidage manuel contre la fuite d'une parcelle à l'autre.
- **Libellés** : un bâtiment cadastral s'affiche « Bâtiment cadastral · 110e15b0 », type PCI
  traduit (01 bâti dur, 02 bâti léger) ; l'identifiant complet reste en infobulle et dans la
  fiche. Les montants et dates sont formatés en français.
- **Fiche adresse** : appariements par décision, avec pastille, confiance en pourcentage, méthode
  et justification lisibles ; la méthode brute reste affichée.
- **Revue B4** : deux colonnes — le cas et ses repères à gauche, le verdict à droite —, barre
  d'avancement ; textes du protocole inchangés.
- **Tests** : les tests existants restent le filet ; ils suivent les onglets (rôle `tab`) au lieu
  des boutons dépliants.

## Critères d'acceptation

- `App.tsx` sous 300 lignes, aucun fichier de composant au-dessus de 400 (203 et 315 au plus) ;
- une fiche parcelle affiche l'effectif de ses ventes et diagnostics sans clic ;
- aucun libellé d'entité liée n'affiche une empreinte de 64 caractères ;
- `pnpm test:e2e` vert sur la base locale ; `make check` vert.

## Vérification — 16 septembre 2026

- `pnpm test:e2e` sur la base locale : 17 réussis, 2 sautés par leur garde (échantillon B4
  entièrement jugé) ; nouveau test : effectifs des onglets sans clic, bâtiments nommés sans
  empreinte, navigation des onglets au clavier ;
- captures relues : fiche parcelle, onglets DPE et ventes, fiche adresse, revue ; la disposition
  en deux colonnes de la revue n'a pas pu être vue sur un cas réel, l'échantillon n'en ayant plus ;
- `make check` vert.
