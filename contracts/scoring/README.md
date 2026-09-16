# Contrats de scoring — brouillons

[`division-extension-v1`](./division-extension-v1.json) et
[`renovation-resale-v1`](./renovation-resale-v1.json) sont lues par `scoring/engine.py`
(poids, éligibilités, préfixes interdits validés au chargement). Elles restent `draft` et
`publication_eligible: false` ; le moteur n'a aucun appelant en production et aucune définition
n'a jamais été insérée en base. [`feature-registry-v1`](./feature-registry-v1.json) n'est lu par
aucun code.

Aucun seuil territorial n'est inscrit dans ces contrats. Les bornes de classe de score (40, 60,
80) et de confiance (0,6, 0,8) sont **en dur dans le moteur** (`engine.py:458-465`, audit §8.5) :
elles devront en sortir avant toute publication de score (`SPEC.md` §11.3).
