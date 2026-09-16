# H8 — Décider si le baromètre porte une carte par commune

**Version :** V5 · baromètre · **Taille :** S · **État :** À faire
**Nature :** décision humaine · **Preuve :** docs/decisions/ADR-017-carte-communale-barometre.md
**Dépend de :** H2 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « heat maps de DPE, prix m², etc. »
**DoD :** test sans objet — décision, aucun code ; preuve sans objet — l'ADR est le livrable

## Contexte à charger

- `SPEC.md` §6.2, §7.3, §7.4, §7.5, §11.3, §13.4, §13.6, §18.4 — ces sections seulement
- `docs/backlog/H2-barometre-document-publiable.md`
- `docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md`

Ne rien charger d'autre sans nécessité démontrée.

## Ce qui bloque

`SPEC.md` §7.5 exclut toute carte du baromètre, et la carte interactive appartient à la plateforme
gelée (§6.2), qui ne se dégèle qu'aux conditions de §11.3. Une carte de chaleur des prix au m² ou
des étiquettes DPE ne peut donc pas s'implémenter : elle demande une décision, puis un amendement
de `SPEC.md` sous ticket.

## Ce que la décision tranche

1. **La forme.** Proposition : une carte choroplèthe statique en SVG, par commune et par EPCI,
   intégrée au document HTML de H2 (§7.4), à partir de la couche `communes` de DS-01. Aucune tuile,
   aucune interaction, aucune dépendance réseau. Une carte interactive reste la plateforme gelée.
2. **La maille.** Pas plus fine que la commune : un carroyage ou une parcelle rapproche des
   mutations individuelles, ce que §18.4 interdit. Une commune sous le support déclaré est rendue
   « sans support », jamais colorée ni interpolée.
3. **Les mesures cartographiées.** BAR-002 (prix médian au m²) et BAR-006 (taux de mutation à
   douze mois) existent. Une carte des étiquettes DPE serait une **mesure nouvelle**, à inscrire au
   registre §13.4 : le parc diagnostiqué n'est pas le parc — on fait un DPE surtout pour vendre ou
   louer — et la réforme du 1er janvier 2026 coupe la série. La décision dit si cette mesure entre,
   et sous quel intitulé qui ne la fasse pas passer pour la qualité du parc.
4. **Le moment.** Avant H3, pour montrer la carte aux cinq professionnels, ou après, si leur
   verdict la demande (§11.3 : « un professionnel a demandé une carte »).

## Ce que ce ticket ne fait pas

Aucun code, aucun amendement de `SPEC.md`. Si la décision est positive, un ticket d'implémentation
s'ouvre, qui amende §7.4 et §7.5, et §13.4 le cas échéant, avant la première ligne.
