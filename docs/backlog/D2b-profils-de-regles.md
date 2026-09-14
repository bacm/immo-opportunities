# D2b — Profils de règles d'urbanisme, là où un candidat le justifie

**Version :** v0.6 · **Taille :** L · **État :** À faire
**Dépend de :** D2, E3 · **Bloque :** —
**Scindé de :** [D2](./D2-import-gpu-ds08.md), 14 septembre 2026

> **La charge est humaine et elle ne se réduit pas.** Ce ticket n'automatise rien : il organise un
> travail de lecture pour qu'il soit fait là où il change une décision, et nulle part ailleurs.

## Contexte à charger

- `contracts/features/market-data-v1.json` (URB-002, URB-004, URB-005)
- `docs/backlog/D2-import-gpu-ds08.md`

Ne rien charger d'autre sans nécessité démontrée.

## Le chiffre qui fonde ce ticket

Documents d'urbanisme en production en France, relevés sur l'API GPU le 14 septembre 2026 :

| Type | Documents |
|---|---:|
| PLU | 9 463 |
| Cartes communales | 2 723 |
| PLUi | 565 |
| PSMV | 42 |
| POS | 2 |
| **Total** | **12 795** |

À trente minutes par document — optimiste pour lire un règlement et en structurer les règles
indispensables — cela représente environ **6 400 heures, près de quatre années-personne**. La
Bretagne seule en demanderait une dizaine de semaines ; le 35, environ deux et demie.

**L'interprétation automatique libre du texte des règlements est interdite**, et cet interdit
n'est pas une commodité : le produit ne rend pas de décision urbanistique opposable. Aucune astuce
technique ne réduit donc ce coût.

## Le principe : valider là où un candidat émerge

Le produit **classe des candidats à approfondir**. Valider 12 795 règlements avant de savoir
quelles communes en portent, c'est travailler à l'envers.

D'où la dépendance à [E3](./E3-publier-snapshots.md) : une fois des `OpportunitySnapshot` publiés,
la liste des communes qui comptent est courte et connue. On y valide les règlements, et nulle part
ailleurs.

## Travail à réaliser

1. Dériver la file de validation des candidats publiés : communes classées par nombre de
   candidats, puis par rang du meilleur candidat.
2. Structurer les règles indispensables par **version exacte de document** — le rattachement
   profil ↔ version est strict et testé, jamais conventionnel. Un profil appliqué à la mauvaise
   version est le risque déclaré de la v0.5.
3. Calculer `URB-002` et `URB-004` là où le profil est validé, absentes avec motif ailleurs.
4. Publier l'avancement par `URB-005`, qui mesure exactement ce travail.

## Ce que ce ticket ne doit pas faire

- **Interpréter le texte.** Ni règle, ni modèle, ni assistance qui produirait une lecture non
  relue. Un profil non validé par un humain n'existe pas.
- **Viser l'exhaustivité.** Une couverture partielle est l'état normal et permanent de ce ticket.
  `URB-005` la publie ; elle ne se cache pas.
- **Bloquer quoi que ce soit.** `URB-002` et `URB-004` absentes avec motif sont un résultat
  légitime, et le scoring doit fonctionner sans elles.

## Critères d'acceptation

- file de validation dérivée des candidats publiés, et non d'un ordre administratif ;
- chaque profil rattaché à une version exacte, avec un test qui refuse un rattachement approximatif ;
- `URB-005` publiée par commune ;
- aucune règle produite sans relecture humaine tracée.
