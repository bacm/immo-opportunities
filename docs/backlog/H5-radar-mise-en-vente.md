# H5 — Radar de mise en vente : un flux hebdomadaire des DPE fraîchement déposés, par secteur

**Version :** V2 · radar · **Taille :** L · **État :** À faire
**Nature :** implémentation · **Touche :** pipelines/scripts/market_listing_candidates.py, pipelines/scripts/pin_dpe_release.py, pipelines/tests/test_market_listing_candidates.py, Makefile, docs/data/radar-mise-en-vente-35.md, contracts/datasets/DS-07/releases/
**Dépend de :** H3, H4 · **Bloque :** H6
**Demandé par :** [ADR-016](../decisions/ADR-016-intelligence-de-marche-puis-radar.md)

## Contexte à charger

- `docs/decisions/avis-juridique-donnees-2026.md` (sortie de H4 : ce qui peut être montré)
- `docs/data/entretiens-professionnels-35.md` (sortie de H3 : ce qu'ils veulent recevoir)
- `pipelines/scripts/market_listing_candidates.py` et `docs/data/biens-en-vente-35051.md` (E8f, point de départ)
- `docs/data/dpe-signal-vente-35.md` et `docs/backlog/D4-import-dpe-ds07.md` (comment un extrait DPE est épinglé)

Ne rien charger d'autre sans nécessité démontrée.

## Ce que ce ticket produit

Le produit V2 : chaque semaine, pour un secteur (commune ou EPCI) choisi par l'abonné, la liste
des parcelles bâties dont un premier DPE de maison a été déposé depuis le dernier envoi, avec
l'âge du dépôt, la chance résiduelle de vente observée sur la cohorte de référence, l'étiquette,
le taux de la commune, la dernière mutation connue — **et rien de plus que ce que H4 autorise**.
Un flux, pas un stock : c'est ce qui justifie un abonnement.

## Ce qui change par rapport à E8f

- **La cadence est une release.** Chaque extrait hebdomadaire de l'API ADEME est épinglé
  (`pin_dpe_release.py`), checksumé, importé sous sa version de transformation. Pas d'alias, pas de
  « dernier extrait ». Le coût de reproductibilité est assumé : une release DS-07 par semaine.
- **La fenêtre se compte depuis la date d'extrait**, jamais depuis l'horloge (règle E8f
  conservée).
- **Les colonnes sont celles de H4.** Si l'avis interdit l'adresse, la ligne porte la parcelle et
  la commune ; si l'avis interdit la chance de vente individuelle, elle porte le taux communal
  seulement. Le ticket ne décide pas de ce point, il l'applique.
- **Aucune combinaison de signaux** : âge et étiquette restent deux lectures indépendantes de la
  même cohorte, jamais un score (règle E8g conservée). Si H3 réclame un rang unique, c'est une
  décision produit nouvelle, à écrire avant de la coder.
- Les appartements issus d'un DPE d'immeuble sont exclus ; l'exclusion est comptée.

## Ce que ce ticket ne fait pas

- Il ne touche ni au front, ni à l'API, ni aux tuiles : la sortie est un fichier par secteur et
  par semaine, remis par le canal que H3 aura montré acceptable (courriel, PDF, CSV).
- Il ne prétend pas à l'off-market : un DPE frais désigne un bien qui entre sur le marché. Le
  document le dit en première ligne.
- Il ne s'étend pas au 22, 29, 56 tant que le 35 n'a pas un abonné.

## Critères d'acceptation

- deux semaines consécutives produites depuis deux releases DS-07 distinctes, sans doublon entre
  les deux envois, avec un test qui le prouve ;
- chaque colonne nominative est autorisée par `avis-juridique-donnees-2026.md`, citée en tête du
  rapport ;
- le taux et la courbe de référence sont ceux du baromètre H1, recomptés ;
- `make check` vert.
