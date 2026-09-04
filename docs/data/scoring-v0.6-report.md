# Rapport technique du scoring v0.6

**Date :** 7 août 2026  
**Définitions :** `division-extension-v0.1`, `renovation-resale-v0.1`  
**Statut :** moteur et publication validés ; activation bloquée jusqu'au profiling et au backtest
régional sur données réelles.

## Décision de publication

Les deux définitions reprennent les composantes et poids initiaux de la spec, mais sont enregistrées
avec `publication_eligible: false` et `parameter_status: profiling_required`. Aucun seuil absolu de
surface, largeur, marché ou risque n'a été inventé. Une tentative d'activation de ces définitions
échoue explicitement en base.

## Propriétés validées

- une feature requise absente bloque la publication ;
- une feature optionnelle absente reçoit la contribution neutre fixe et son poids n'est pas
  redistribué ;
- une feature `confidence_only` ne change jamais le classement ;
- le score et la confiance sont bornés et calculés séparément ;
- une feature dupliquée, interdite ou postérieure au snapshot fait échouer le calcul ;
- l'ordre des entrées ne modifie ni le score ni le digest reproductible ;
- les contributions positives, négatives et neutres conservent sources, releases, formule,
  qualité et gabarit d'explication ;
- les scénarios prudent, central et optimiste incluent acquisition, travaux, frais, financement et
  portage ;
- les résultats de baseline et de moteur sont rapportés même lorsque le lift est défavorable ;
- le jeu `development` est exclu des métriques `validation` et `final`.

## Validation PostgreSQL isolée

La chaîne Alembic complète a été appliquée sur PostgreSQL 15 / PostGIS 3.5, redescendue jusqu'à
`20260806_0011`, puis réappliquée. Une fixture complète a ensuite vérifié :

1. l'activation atomique d'une définition publiable et complète ;
2. la publication d'un snapshot possédant toutes ses composantes et preuves ;
3. le rejet d'un `UPDATE` rétroactif avec le message d'immutabilité ;
4. le déplacement atomique du pointeur vers un snapshot historique ;
5. l'enregistrement d'un événement `rolled_back`.

La base de validation et son conteneur ont été supprimés après le test.

## Baseline et backtest

Le moteur de baseline accepte uniquement des seuils fournis par une définition profilée. Il ne
contient aucune constante territoriale arbitraire. Le rapport de backtest calcule précision à K,
précision baseline, lift et précision par segment `urban`, `periurban`, `littoral` et `rural`.

Les tests utilisent une fixture volontairement défavorable (`lift@2 = 0,5`) afin de vérifier que
le résultat n'est pas masqué. Ce résultat n'est pas une mesure produit et ne remplace pas le
backtest régional.

## Travail restant avant activation

- profiler les distributions réelles par stratégie, type de bien, segment géographique et classe
  de surface ;
- figer les transformations et barèmes observés dans une nouvelle version publiable des contrats ;
- construire les jeux développement, validation et final sans fuite temporelle ;
- produire précision à 10, 20 et 50, lift, taux de rejet et résultats d'ablation ;
- documenter chaque segment critique, y compris tout résultat défavorable ;
- réaliser la revue professionnelle avant publication.
