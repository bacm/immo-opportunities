# B4 — Revue manuelle stratifiée d'un échantillon d'appariements

**Version :** v0.3 · **Taille :** M · **État :** À faire
**Dépend de :** B3 · **Bloque :** B5, clôture de v0.3

## Contexte à charger

- `docs/data/spatial-reference-35-report.md`
- `pipelines/src/immo_pipelines/spatial/resolution.py`
- migrations `20260805_0005` à `20260805_0007` (table de revue)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

C'est le dernier verrou de v0.3, exigé à la fois par les tests obligatoires de la version et par la
conclusion du rapport spatial : « revoir manuellement un échantillon stratifié urbain, périurbain,
rural et cas frontières ».

Aucune métrique automatique ne remplace cette étape : les contrôles vérifient la **cohérence**
interne des appariements, pas leur **exactitude** dans le monde réel.

## Plan d'échantillonnage

Stratification sur deux axes croisés :

| Strate territoriale | Strate d'appariement |
|---|---|
| urbain (Rennes et communes denses) | certain par identifiant officiel |
| périurbain | certain par relation source explicite |
| rural | certain par intersection spatiale |
| littoral | ambigu |
| cas frontières : limites communales, parcelles multi-bâtiments, bâtiments multi-parcelles | rejeté et non apparié |

Fixer la taille d'échantillon **avant** de regarder les résultats, et la justifier : elle doit
permettre de détecter un taux d'erreur au moins aussi bas que celui qu'on prétendra publier. Un
échantillon dimensionné après coup n'est pas une validation.

Inclure obligatoirement :
- les 3 864 bâtiments RNB ponctuels — risque d'emprise inventée ;
- les bâtiments à cardinalité extrême, jusqu'à 37 parcelles ;
- les 217 identifiants BAN conflictuels traités par [BUG-03](./BUG-03-quarantaine-par-attribut.md) ;
- les 403 bâtiments sans code commune et les 33 au code absent, soumis à `rnb-commune-spatial@1`.

## Protocole

1. Tirage aléatoire reproductible : graine fixée et enregistrée.
2. Pour chaque cas, le relecteur consulte les sources d'origine, pas la sortie du moteur seule.
3. Verdict par cas : correct / incorrect / indécidable. « Indécidable » est un résultat valide et
   ne doit pas être forcé.
4. Les désaccords sont conservés, pas arbitrés silencieusement.
5. Résultats consignés dans la table de revue append-only déjà migrée
   (`20260805_0005` à `20260805_0007`).

## Points de vigilance

- Le relecteur ne doit pas voir le score de confiance avant de rendre son verdict, sinon la revue
  mesure l'accord avec le moteur et non l'exactitude.
- Un taux d'erreur mesuré sur un échantillon non stratifié est ininterprétable pour le rural, très
  majoritaire en volume dans le 35.
- Si le taux d'erreur observé dépasse ce que le scoring peut absorber, la conclusion est de ne pas
  publier — pas d'ajuster le seuil de confiance après coup.

## Tests obligatoires

- la revue est append-only : un verdict ne peut pas être réécrit, seulement complété ;
- le tirage est reproductible depuis sa graine ;
- un cas indécidable n'est jamais compté comme correct.

## Critères d'acceptation

- échantillon stratifié tiré, revu et consigné ;
- taille d'échantillon justifiée avant tirage ;
- taux d'exactitude publié par strate, y compris défavorable ;
- les cas ambigus confirmés restent exclus de la publication ;
- v0.3 peut cocher « Métriques et échantillon de validation produits ».

## Preuves à produire

- rapport `docs/data/spatial-matching-manual-review-35.md` : protocole, graine, tailles, résultats
  par strate, désaccords ;
- verdicts persistés dans la table de revue.
