# H4 — Obtenir un avis juridique écrit sur l'usage des données, préalable au radar

**Version :** V2 · radar · **Taille :** S · **État :** À faire
**Nature :** décision humaine · **Preuve :** docs/decisions/avis-juridique-donnees-2026.md
**Dépend de :** A7 · **Bloque :** H5
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md) ; exigé par `SPEC.md` §18.3 depuis le 3 août 2026, jamais fait

## Contexte à charger

- `docs/audit-critique-2026-09-15.md` §5 (juridique)
- `docs/data/biens-en-vente-35051.md` (ce que la liste E8f montre : adresse, étiquette, chance de vente)
- `SPEC.md` §13.6, §18 — ces sections seulement

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket décide

Ce qu'un radar de mise en vente a le droit de montrer, à qui, et sous quelle forme. Sans cette
réponse, H5 ne peut pas choisir ses colonnes. Une heure d'un avocat spécialisé données et
immobilier coûte moins qu'un ticket ; la réponse est écrite dans le dépôt, datée, avec le nom du
cabinet ou la mention « avis interne, non opposable ».

## Questions à poser, telles quelles

1. **DVF rapproché d'une parcelle et d'une adresse.** Le cadre de DVF (loi 2018-727, décret
   2018-1350, art. L112 A LPF) interdit la réidentification. Afficher les mutations d'une parcelle
   identifiée, avec son adresse, dans un outil professionnel payant : licite, sous conditions,
   ou interdit ?
2. **Inférence de mise en vente à une adresse.** Publier à des professionnels « ce logement, à
   cette adresse, a fait l'objet d'un DPE le 12 mai 2026 et 31,7 % des logements dans ce cas se
   vendent sous six mois » : est-ce un traitement de données personnelles ? Quelle base légale,
   quelle information des personnes, quel droit d'opposition ? Le passage à l'échelle de la
   parcelle sans adresse change-t-il la réponse ?
3. **Démarchage.** Depuis le 11 août 2026, le démarchage téléphonique B2C sans consentement est
   interdit. Un outil qui désigne des logements de particuliers à des professionnels engage-t-il
   la responsabilité de l'éditeur sur l'usage qu'en font ses clients ? Quelles mentions
   contractuelles ?
4. **API ADEME.** Les conditions d'usage de l'API `data-fair` autorisent-elles l'extraction de
   l'ensemble des diagnostics d'un département et la redistribution des adresses déclarées à des
   tiers payants ?
5. **MAJIC personnes morales × BODACC.** Constituer une liste de biens détenus par des sociétés en
   procédure collective, avec dénomination, à destination de professionnels : licite ? (Prépare V3,
   sans engagement.)

## Critères d'acceptation

- le fichier de preuve existe, daté, avec la source de l'avis ;
- chaque question ci-dessus a une réponse en trois valeurs : *licite*, *licite sous conditions
  (lesquelles)*, *à ne pas faire* ;
- les conditions retenues sont reportées telles quelles dans les critères d'acceptation de H5.
