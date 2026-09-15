# E7 — Décider si le produit estime la valeur des biens non vendus

**Version :** v0.6 · **Taille :** M · **État :** À faire
**Nature :** décision humaine · **Preuve :** docs/data/valuation-decision.md
**Dépend de :** E6 · **Bloque :** —
**Demandé par :** conversation du 14 septembre 2026

> **Ce ticket est une décision, pas une implémentation.** Il ne peut pas être « fait » par du
> code : il demande d'amender `SPEC.md` et `ARCHITECTURE.md`, ou de refermer la question.

## Ce qui est demandé

Corréler les biens vendus avec ceux qui ne le sont pas — population de la commune, distance aux
grandes villes, distance à la côte, commerces et écoles à proximité — pour estimer une valeur là
où aucune transaction n'existe.

## Pourquoi ce n'est pas faisable en l'état

Trois règles s'y opposent, et aucune n'est accessoire.

**`ARCHITECTURE.md` proscrit le ML en production.** Une estimation hédonique à partir
d'aménités est un modèle statistique appris. Que le code tienne en trente lignes ne change rien
au fond : le résultat n'est pas explicable parcelle par parcelle.

**`SPEC.md` exclut la prédiction.** Le produit classe des candidats à approfondir selon deux
stratégies. Ce n'est ni une prédiction de vente, ni une valorisation.

**[D1](./D1-import-dvf-ds06.md) a déjà tranché le cas limite**, et c'est le plus gênant :

> Une commune rurale peut n'avoir aucun comparable exploitable. C'est un résultat légitime :
> feature absente motivée et confiance réduite, **pas un repli sur la moyenne départementale**.

Estimer un prix depuis les écoles et les commerces **est** ce repli. Mieux habillé, donc plus
difficile à contester — ce qui le rend plus dangereux, pas moins.

## Ce qui rend la demande légitime malgré tout

**282 communes sur 332** atteignent 30 ventes de maison exploitables — sur **douze** millésimes,
depuis que [D8](./D8-historique-dvf-2014.md) a remonté l'historique à 2014. Les 50 autres n'auront
pas de médiane robuste, et un utilisateur qui y cherche un bien reçoit une absence.

> **Ce ticket a été ouvert sur un chiffre qui n'est plus le bon.** Il annonçait 152 communes sur
> 332 et 180 sans support — sur cinq millésimes, et sous la version 2 de transformation. Sous la
> version 4 et sur douze millésimes, les communes sans support passent de 147 à **50**. L'écart
> qui motivait la question s'est réduit d'un facteur trois : l'issue « refermer » en devient
> nettement plus tenable, et c'est au décideur de le dire.

[E6](./E6-segmentation-observee.md) en récupérera une partie : un segment bien tracé fait
bénéficier une commune pauvre en données du support de ses semblables — **sans rien prédire**,
puisque la médiane reste calculée sur des transactions réelles.

**E6 doit donc être livré avant que cette décision se pose**, parce qu'il en déplacera les termes :
il faut savoir combien de communes restent sans support *après* segmentation avant de juger si
l'écart justifie d'amender la spécification.

## Trois issues, à trancher explicitement

1. **Refermer.** La segmentation suffit ; les communes restantes portent une absence motivée. Le
   produit reste ce que la spécification dit qu'il est.
2. **Amender le périmètre.** Le produit estime, et alors `SPEC.md` et `ARCHITECTURE.md` changent,
   avec une note ADR. Une estimation devient un objet distinct d'un comparable : jamais présentée
   comme un prix observé, toujours porteuse de son incertitude, et exclue de toute preuve de score.
3. **Voie étroite.** Une règle explicable et non apprise — par exemple la médiane du segment
   appliquée telle quelle, avec une confiance dégradée et un motif explicite. Ce n'est pas un
   modèle, c'est une imputation assumée et nommée. Reste à décider si elle est plus honnête qu'une
   absence, ou seulement plus confortable.

## Critères d'acceptation

- décision écrite, datée, motivée, avec son auteur ;
- si amendement : ADR et sections modifiées de `SPEC.md` et `ARCHITECTURE.md` ;
- si refus : la raison est consignée pour que la question ne se rouvre pas sans élément nouveau ;
- dans tous les cas, le nombre de communes sans support **après** E6 est publié — c'est le chiffre
  qui fonde la décision, et il part désormais de 50, non de 180.

## Preuve à produire

`docs/data/valuation-decision.md` : la décision, sa date, son auteur, les mesures qui la fondent —
dont le nombre de communes sans support après E6 — et, en cas de refus, la raison qui referme la
question.
