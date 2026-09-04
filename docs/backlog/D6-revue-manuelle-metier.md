# D6 — Revue manuelle stratifiée comparables / GPU / DPE / risques

**Version :** v0.5 · **Taille :** M · **État :** À faire
**Dépend de :** D5 · **Bloque :** E1, clôture de v0.5

## Contexte à charger

- `pipelines/src/immo_pipelines/market_data/features.py`
- `docs/data/market-data-sources-audit.md`
- `docs/backlog/B4-revue-manuelle-appariements.md` (protocole de référence)

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

Dernier verrou de v0.5, symétrique de [B4](./B4-revue-manuelle-appariements.md) pour les données
métier. Les tests obligatoires de la version l'exigent : « comparaison manuelle de sélections de
comparables ».

Aucune métrique automatique ne peut établir qu'une sélection de comparables est **pertinente** pour
un professionnel. C'est précisément ce que le pilote (G8) mesurera à grande échelle ; cette revue
est le contrôle préalable qui évite d'y aller avec une sélection manifestement fausse.

## Périmètre de la revue

### Comparables DVF (le plus important)

Tirer des unités dans chaque segment de marché et, pour chacune, faire évaluer par un professionnel
ou un relecteur informé :
- les comparables **retenus** sont-ils pertinents ?
- les comparables **exclus** l'ont-ils été à juste titre ?
- le prix de référence produit est-il défendable ?

Les exclusions sont la partie la plus révélatrice : un moteur qui exclut trop produit des absences,
un moteur qui exclut trop peu produit de la fausse précision.

### Zonage GPU

Vérifier sur un échantillon que la zone attribuée à la parcelle correspond au document opposable
réel, et que la version du profil de règles est la bonne.

### Appariement DPE

Vérifier que le diagnostic retenu correspond bien au bâtiment, en particulier sur les cas
`ambiguous_match` et en habitat collectif.

### Risques

Vérifier qu'aucune observation communale n'a été présentée comme parcellaire, et que les absences
de risque correspondent à une couverture fine réellement connue.

## Protocole

1. Stratification sur les segments de marché **et** sur les types territoriaux : urbain, périurbain,
   littoral, rural.
2. Taille d'échantillon fixée et justifiée avant tirage ; graine enregistrée.
3. Verdict par cas : correct / incorrect / indécidable, avec commentaire libre conservé.
4. Le relecteur ne voit pas la confiance calculée avant de rendre son verdict.
5. Résultats consignés, désaccords conservés.

## Critères d'acceptation

- échantillon stratifié revu sur les quatre domaines ;
- taux d'exactitude publié par domaine et par strate, y compris défavorable ;
- les erreurs identifiées sont soit corrigées, soit documentées comme limites connues ;
- si la sélection de comparables est jugée non défendable, la conclusion est de ne pas publier de
  feature de prix — pas d'ajuster les règles après coup pour satisfaire la revue ;
- v0.5 peut être passée à `Terminée`.

## Preuve à produire

`docs/data/market-data-manual-review-35.md` : protocole, graine, tailles, résultats par domaine et
par strate, désaccords, limites retenues.
