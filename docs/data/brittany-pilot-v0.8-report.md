# Rapport régional — pilote Bretagne v0.8

**Date :** 10 août 2026  
**Statut :** socle technique livré, ouverture du pilote refusée.

## Résultat

Les pipelines possèdent désormais les partitions statiques 22, 29, 35 et 56. Le protocole produit
une matrice DS-01…DS-09 exhaustive, des comparaisons de couverture, un échantillon aveugle
stratifié `top_score / baseline / random`, un sous-échantillon doublement évalué, des splits
`development / validation / final`, la précision top 10/20/50 et la stabilité top-k.

Le modèle persiste segmentation et seuils versionnés, couverture département/EPCI/commune,
reviews pseudonymisées, désaccords et résultats successifs. Un bundle régional est publié ou
retiré atomiquement et chaque action est historisée. L'interface permet de naviguer entre les
quatre départements et expose le gate régional sans transformer une absence en couverture.

## État des preuves

- données : 0/4 département couvert ; voir `brittany-acceptance-matrix.md` ;
- scoring : définitions toujours `profiling_required`, aucun backtest réel ;
- H1 à H5 : aucune mesure réelle ;
- professionnels : 0/3 ;
- engagement payant ou équivalent : 0/2 ;
- exploitation : scripts, timers, alertes et drill livrés, aucun RPO/RTO mesuré ;
- charge : benchmark MVT existant, mais carte/liste/API/tuile régionale de production non mesurée.

Les fixtures automatisées testent les invariants et incluent volontairement des cas négatifs. Elles
ne sont comptées ni comme précision produit, ni comme usage professionnel.

## Vérifications techniques

- `make check` : 63 tests backend et 51 tests pipeline réussis, Ruff, Pyright, TypeScript, build
  Vite, OpenAPI et deux modèles Compose valides ;
- Alembic : chaîne complète `0001 → 0015` appliquée deux fois sur PostgreSQL 15/PostGIS 3.5
  jetable ; downgrade/upgrade de `0015` réussi ;
- gate SQL : 36 couples exposés, 0 prêt, publication incomplète refusée ;
- Playwright ciblé : sélecteur départemental et publication bloquée réussis ;
- Ansible : syntaxe des playbooks bootstrap et deploy validée sur l'inventaire staging ;
- scripts d'exploitation : syntaxe Bash validée et dashboard JSON valide.

Le parcours Playwright qui interroge une vraie recherche 35 n'a pas été rejoué pendant cette
livraison, car l'API locale n'était pas démarrée. Les parcours entièrement interceptés et le nouveau
gate régional passent ; ce point n'est pas présenté comme un test staging.

## Décision du gate au 10 août 2026

**ARRÊTER l'ouverture et la publication du pilote Bretagne.** Cette décision est un no-go
opérationnel provisoire, pas une conclusion sur la valeur marché. Elle doit être réexaminée après
les 36 audits, l'activation des deux scores, le test de restauration et la collecte de cas réels.
Il serait trompeur de choisir `poursuivre` ou `pivoter` sur des résultats qui n'existent pas.

## Seuil de réouverture

Le gate devient éligible lorsque les quatre départements sont couverts, H1 à H5 mesurées, le lift
top 20 atteint 2× la baseline ou son échec est documenté, trois professionnels ont réalisé des cas
réels, deux ont pris un engagement et une restauration complète a produit un rapport RPO/RTO.
