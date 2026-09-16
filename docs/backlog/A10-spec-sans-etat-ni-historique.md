# A10 — `SPEC.md` ne porte ni état réel, ni résultat mesuré, ni décision : une règle de propriété et son application

**Version :** transverse · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** SPEC.md, ARCHITECTURE.md, docs/data/README.md, docs/backlog/README.md, CLAUDE.md
**Dépend de :** A9 · **Bloque :** —
**DoD :** test sans objet — documents de référence · preuve sans objet — aucun chiffre nouveau, les tableaux déplacés sont recopiés à l'identique
**Demandé par :** conversation du 16 septembre 2026

## Contexte à charger

- `SPEC.md` en-tête, §10, §11, §13.1, §13.11, §24, §25, §26
- `ARCHITECTURE.md` §3.2, §10, §23, §25 (ce qui y est déjà)
- `docs/data/README.md`, `docs/backlog/README.md` (points d'accueil)
- `scripts/check-doc-budget` : plafond d'`ARCHITECTURE.md`, 1 300 lignes, à ne pas dépasser

## Pourquoi ce ticket existe

`SPEC.md` fait 691 lignes et a été réécrit deux fois en douze jours. Le volume qui périme n'est
pas dans les exigences (§6 à §9, stables) mais dans ce qui décrit l'état réel, les résultats
mesurés, les décisions et les questions ouvertes : tout cela a déjà un propriétaire ailleurs et
change à chaque import ou ticket terminé. Sans règle de propriété, la spec grossit d'un paragraphe
à la fois, comme `ARCHITECTURE.md` avant son plafond.

## Choix retenus

- **Pas de plafond de lignes** pour `SPEC.md` pour l'instant (refusé par l'auteur).
- **Règle écrite en tête de `SPEC.md`** : la spec dit ce que le produit doit faire et ne pas faire.
  Un résultat mesuré va dans `docs/data/`, un état dans `ARCHITECTURE.md`, une décision dans
  `docs/decisions/`, une question ouverte dans le backlog. La spec n'en garde que la conclusion
  qui devient une contrainte, avec un lien.
- **Numérotation des sections conservée** : chaque section vidée garde son numéro et un renvoi,
  pour que `CLAUDE.md`, les tickets, l'audit et les ADR qui citent « §13 » ou « §25 » restent
  justes.
- Déplacements : tableaux de §10 → `docs/data/README.md` ; état des sources de §13.1 →
  `ARCHITECTURE.md` §10.7 ; questions de §25 → `docs/backlog/README.md` ; §11.1, §24, §26 →
  renvois vers `ARCHITECTURE.md`, `docs/decisions/`, les tickets H.
- §13.11 est une contrainte produit (rattachement par identifiant, agrégation à la commune) : elle
  reste, débarrassée de la mention « état réel ».

- Appliqué en passant, au titre de la même règle : §14 renvoie à `ARCHITECTURE.md` §9 pour les
  schémas et tables vides ; §21 ne porte plus « H6 (ce ticket) » ni l'avancement.

## Critères d'acceptation

- aucune date d'état, aucun effectif de source, aucune liste de décisions dans `SPEC.md` hors
  contraintes ;
- chaque contenu déplacé est retrouvable par le renvoi laissé dans sa section d'origine ;
- `make doc-budget`, `make backlog-check`, `make invariants`, `make ticket-check` verts.
