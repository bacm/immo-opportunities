# H3 — Présenter le baromètre à cinq professionnels, et recueillir ce qu'ils paieraient

**Version :** V5 · baromètre · **Taille :** M · **État :** À faire
**Nature :** revue humaine · **Preuve :** docs/data/entretiens-professionnels-35.md
**Dépend de :** H2 · **Bloque :** H5, H6
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)

## Contexte à charger

- `docs/decisions/ADR-016-intelligence-de-marche-puis-radar.md`
- `docs/audit-critique-2026-09-15.md` §2, §4 et §14 (client, concurrence, variantes)
- `docs/data/barometre-marche-35/` (sortie de H2)
- `SPEC.md` §5 (hypothèses) et §22 (monétisation) — ces sections seulement

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket décide

Si l'intelligence de marché intéresse quelqu'un, à quel prix, et si le radar de mise en vente (V2)
est ce qu'ils attendent ensuite. C'est le premier contact du projet avec un professionnel : aucun
entretien, aucune lettre d'intention, aucun prospect nommé n'existe dans le dépôt au 15 septembre
2026. Le verdict oriente H5 et H6.

## Recrutement

Cinq personnes, pas deux, de profils distincts : deux marchands de biens ou
investisseurs-rénovateurs, un aménageur-lotisseur ou constructeur de maisons individuelles, un
géomètre-expert, un agent immobilier ou chasseur. Tous actifs sur le 35. Le baromètre est le
prétexte : il leur est remis quoi qu'il arrive, et c'est ce qui rend l'entretien acceptable.

## Protocole

1. Relever **la méthode actuelle** avant de montrer quoi que ce soit : comment ils trouvent leurs
   affaires, quels outils ils paient (Kel Foncier, Urbanease, Telescop, Géofoncier, pige…), combien
   d'opérations par an, quel territoire.
2. Remettre le baromètre de leur EPCI. Les laisser lire. Noter ce qu'ils regardent en premier, ce
   qu'ils contestent, ce qu'ils reconnaissent de leur métier.
3. Poser les questions de rétention : « que voudriez-vous recevoir chaque mois ? », « et chaque
   semaine ? ».
4. Décrire V2 en une phrase, sans le vendre : « chaque semaine, les maisons de votre secteur dont
   un diagnostic vient d'être déposé, avec la chance observée qu'elles se vendent sous six
   mois ». Recueillir la réaction, puis la question du prix, chiffrée.
5. Poser le prix du baromètre seul, chiffré.
6. Ne rien corriger ni justifier pendant la session. Les objections sont la donnée.
7. Si le professionnel en a le temps, lui soumettre aussi les listes E8 et E8f selon le protocole
   E9 **corrigé** (aveugle rétabli). Sinon, E9 reste un ticket à part.

## Ce qu'il faut spécifiquement écouter

- **Le goulot du métier** : trouver, acheter au bon prix, ou obtenir l'autorisation ? La réponse
  départage V1, V2 et V3.
- **Le propriétaire** : combien de fois revient « mais comment je le contacte ? ». Si c'est
  systématique, aucune variante sans propriétaire ne tient, et V3 (personnes morales) ou V4 (EPCI)
  remontent.
- **Ce qui existe déjà chez eux** : un chiffre du baromètre qu'ils ont déjà ailleurs ne vaut rien.

## Critères d'acceptation

- cinq entretiens, méthode actuelle relevée avant présentation ;
- verbatims conservés, y compris ceux qui contredisent le produit ;
- pour chacun : prix déclaré pour le baromètre, prix déclaré pour V2, ou refus explicite ;
- limite énoncée : cinq personnes n'autorisent aucun pourcentage ;
- une conclusion explicite parmi : *V5 se vend, lancer H5* ; *V5 ne se vend pas, V2 intéresse,
  lancer H4 puis H5* ; *ni l'un ni l'autre, rouvrir V1, V3 ou V7* — et cette conclusion alimente
  H6.
