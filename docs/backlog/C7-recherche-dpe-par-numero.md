# C7 — Retrouver un DPE par son numéro, y compris écarté, avec son motif

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** backend/src/immo/, backend/tests/, contracts/openapi/, apps/web/
**Dépend de :** D9 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — le porteur cherchait un DPE neuf de 2022
absent de sa parcelle ; il était dans l'extrait, en quarantaine faute d'identifiant rattachable.
Rien à l'écran ne permettait de le voir.
**DoD :** preuve sans objet — aucun chiffre publié ; les tests backend et e2e portent la preuve

## Contexte à charger

- `SPEC.md` §13.7 (valeur manquante avec motif), §15 — ces sections seulement
- [ADR-021](../decisions/ADR-021-dpe-logements-neufs.md)
- `backend/src/immo/explorer.py`, `backend/src/immo/api/routes/explorer.py`
- `apps/web/src/Search.tsx`, `apps/web/src/sheets/`

## Choix retenus

- **Route** `GET /api/v1/energy-assessments/{dpe_number}` : les diagnostics conservés sous ce
  numéro (release, source, bâtiment, adresse, parcelles par le pont bâtiment ↔ parcelle) et les
  écarts consignés dans `meta.attribute_quarantine` (release, source, attribut, motif,
  identifiants déclarés). Numéro validé par motif (13 caractères) ; 404 si rien n'est connu.
- **Pas d'index** : la recherche par suffixe d'identifiant sur la quarantaine prend 21 ms.
- **Recherche** : une saisie au format d'un numéro de DPE propose « Diagnostic DPE … » en tête
  des résultats, sans appel supplémentaire ; le choisir ouvre une fiche DPE, partageable par le
  paramètre d'URL `dpe`.
- **Fiche DPE** : pour chaque source, l'état — conservé et rattaché, ou écarté — et, s'il est
  écarté, le motif en clair et les identifiants que la source déclarait ; les parcelles liées
  s'ouvrent d'un clic. Local seulement, comme le reste de l'outil.
- **Tests** : numéros sans lien avec le porteur — `2135N0105211H` (écarté) et `2135E0000072D`
  (rattaché à `35238000KO0295`).

## Critères d'acceptation

- un DPE écarté s'affiche avec son motif et ses identifiants déclarés ;
- un DPE conservé mène à sa parcelle ;
- un numéro inconnu dit qu'il est inconnu, sans erreur ;
- `make openapi` régénéré, `make check` et `pnpm test:e2e` verts.

## Vérification — 16 septembre 2026

- route vérifiée sur la base locale : écarté (`2135N0105211H`), conservé (`2135E0000072D` →
  `35238000KO0295`), inconnu (404) ; tests backend : motif et identifiant absent restés nuls,
  404, numéro malformé refusé ;
- `pnpm test:e2e` : 22 réussis, 2 sautés par leur garde ; la fiche distingue inconnu et panne
  (`ApiError` porte le statut) ; un identifiant BAN à deux segments est signalé comme une voie ;
- `make openapi` régénéré, `make check` vert.
