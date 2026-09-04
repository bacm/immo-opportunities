# E4 — Backtest régional contre baseline cadastrale

**Version :** v0.6 · **Taille :** L · **État :** À faire
**Dépend de :** E3 · **Bloque :** E5, clôture de v0.6

## Contexte à charger

- `pipelines/src/immo_pipelines/scoring/engine.py` (baseline, ablation)
- `pipelines/tests/test_scoring_engine.py`
- `docs/data/scoring-v0.6-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

DoD de v0.6 ouverte : « Backtest régional initial produit ». Le moteur de backtest, les baselines
et les ablations sont implémentés ; il manque l'exécution sur données réelles.

**Question à laquelle le backtest répond :** le score apporte-t-il quelque chose qu'un simple tri
cadastral n'apporte pas ? Si la réponse est non, le produit n'a pas de valeur et il vaut mieux le
savoir avant le pilote.

## Protocole

1. **Baseline** : classement obtenu à partir des seuls attributs cadastraux, sans les features
   métier. C'est le point de comparaison honnête.
2. **Métriques** : précision top 10, top 20, top 50 pour chaque stratégie.
3. **Ablation** : retirer une feature à la fois et mesurer l'effet sur le classement. Une feature
   dont le retrait ne change rien ne mérite pas d'être dans le score.
4. **Absence de fuite temporelle** : aucune donnée postérieure au snapshot n'entre dans le calcul.
   Le moteur le teste déjà ; le vérifier sur données réelles est différent de le vérifier sur fixture.
5. **Séparation** : les données ayant servi au profiling de E1 ne doivent pas servir à valider.

## Difficulté propre à ce produit

Il n'existe pas de vérité terrain directe : le produit ne prédit pas une vente, donc « le bien
s'est vendu » n'est pas le critère. Le proxy retenu doit être choisi et **justifié explicitement**
avant de mesurer, et ses limites documentées. Sinon la métrique produira un chiffre sans signification.

C'est aussi pourquoi le backtest ne remplace pas le pilote [G8](./G8-pilote-trois-professionnels.md) :
la validation décisive est le jugement de professionnels sur des cas réels. Le backtest sert à
éviter d'aller au pilote avec un classement qui ne bat pas un tri trivial.

## Points de vigilance

- **Publier les résultats même s'ils sont défavorables.** C'est un critère d'acceptation explicite
  de v0.6, pas une option.
- Un gain apparent sur un échantillon faible n'est pas un gain. Publier les intervalles, pas
  seulement les points.
- Le choix du proxy de vérité terrain est le paramètre le plus discutable de l'exercice : le
  documenter comme tel.

## Tests obligatoires

- garde temporelle : un résultat sélectionné qui fuit le futur fait échouer le calcul ;
- l'ablation produit un résultat par feature retirée ;
- le backtest est reproductible depuis les releases citées ;
- la baseline n'utilise aucune feature métier.

## Critères d'acceptation

- précision top 10 / 20 / 50 publiée pour les deux stratégies, contre baseline ;
- résultats d'ablation publiés par feature ;
- proxy de vérité terrain justifié et ses limites documentées ;
- absence de fuite temporelle vérifiée sur données réelles ;
- résultats publiés même défavorables.

## Preuves à produire

- rapport `docs/data/scoring-backtest-35.md` ;
- mise à jour de [`scoring-v0.6-report.md`](../data/scoring-v0.6-report.md).
