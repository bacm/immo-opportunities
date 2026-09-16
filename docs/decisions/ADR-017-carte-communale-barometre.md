# ADR-017 — Pas de carte dans le baromètre avant H3

**Date :** 17 septembre 2026
**Décidé par :** l'agent, sur délégation du porteur du projet (« enchaîne en prenant les
meilleures décisions »), le 17 septembre 2026. Révisable par le porteur.

**Contexte.** La demande du 16 septembre (« heat maps de DPE, prix m², etc. ») a ouvert H8.
`SPEC.md` §7.5 exclut toute carte du baromètre. Le gel de la plateforme est levé (ADR-019) : une
carte interactive dans l'Explorer n'est plus bloquée, seule la question du document reste. Les
faits établis par H8 :

- le document de H2 tient sur deux pages A4 exactement ; une carte remplace un graphique ou ajoute
  une page ;
- la marge de revente n'existe qu'au département et à l'EPCI, jamais à la commune ;
- une carte des étiquettes DPE serait une mesure nouvelle, trompeuse sans précaution : le parc
  diagnostiqué n'est pas le parc, et la réforme de 2026 coupe la série ;
- **H3 prévoit d'observer si les professionnels demandent une carte d'eux-mêmes, sans la leur
  suggérer.** Un document qui en porterait une rendrait l'observation impossible.

**Alternatives écartées.**

- *Une choroplèthe du prix médian au m² par commune dans le document, avant H3.* Elle ajouterait
  une page, changerait le document que H3 doit montrer tel quel, et fausserait la question posée
  aux professionnels.
- *Une carte des étiquettes DPE.* Mesure nouvelle, dont l'intitulé devrait empêcher de la lire
  comme un état du parc ; rien ne la demande encore.

**Décision.**

1. **Le document du baromètre reste sans carte jusqu'au verdict de H3.** `SPEC.md` §7.5 n'est pas
   amendé.
2. **Si H3 fait apparaître la demande**, un ticket d'implémentation l'ouvre : choroplèthe SVG
   statique, maille commune au plus fin, communes sous le support rendues « sans support », jamais
   colorées ni interpolées (§18.4), mesures existantes seulement (BAR-002, BAR-006). Il amende
   §7.4 et §7.5 avant la première ligne.
3. **Une carte des étiquettes DPE** reste hors du baromètre tant qu'une mesure n'est pas inscrite
   au registre §13.4 par décision.
4. **L'Explorer** peut montrer une couche communale de mesures agrégées sous ticket ordinaire
   (ADR-019), à usage de vérification, sans rien changer au document.

**Conséquences.**

- H8 est clos ; H3 garde sa question « carte » intacte.
- Le document que les professionnels verront est celui de H7, recompté.
