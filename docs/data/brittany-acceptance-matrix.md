# Matrice d'acceptation Bretagne — v0.8

**Date de coupe :** 10 août 2026  
**Règle :** seul `accepted` avec release active et sans contrôle bloquant vaut couverture.

| Source | 22 | 29 | 35 | 56 |
|---|---|---|---|---|
| DS-01 Cadastre | absent | absent | **accepté** | absent |
| DS-02 RNB | absent | absent | importé, revue requise | absent |
| DS-03 BDNB Open | absent | absent | contrat seul | absent |
| DS-04 BD TOPO | absent | absent | contrat seul | absent |
| DS-05 BAN | absent | absent | bloqué par conflits | absent |
| DS-06 DVF+ | absent | absent | fixture seule | absent |
| DS-07 DPE | absent | absent | fixture seule | absent |
| DS-08 GPU/CNIG | absent | absent | fixture seule | absent |
| DS-09 Géorisques | absent | absent | fixture seule | absent |

Verdict de couverture : **0/4 département couvert** au sens v0.8. Le Cadastre 35 est accepté,
mais un département n'est pas présenté comme couvert lorsqu'une donnée critique manque. Les
rapports sources existants restent limités au 35 ; ils ne valent aucune preuve pour 22, 29 ou 56.

Les 36 cases sont aussi calculées à l'exécution par la vue
`meta.brittany_release_readiness`. La publication atomique refuse un bundle incomplet, une release
non acceptée, un contrôle bloquant, une segmentation en brouillon ou un score non publiable.
