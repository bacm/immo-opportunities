# Contrats versionnés

Interfaces stables entre les sources, les pipelines, le backend et le frontend.

- `datasets/` : contrat par dataset (`DS-*/v1.json`) et manifeste par release (`DS-*/releases/`) ;
  c'est la partie réellement exécutée — `cadastre/manifest.py` refuse un manifeste sans SHA-256 ;
- `features/` : définitions déclaratives ; **aucun code ne les lit** (audit §8.4), la logique est
  réimplémentée dans `pipelines/src/immo_pipelines/market_data/features.py` ;
- `scoring/` : deux définitions `draft`, lues par le moteur, jamais publiées ;
- `openapi/` : contrat HTTP généré depuis FastAPI, vérifié en CI.

Une modification incompatible crée une nouvelle version ; elle ne remplace jamais la précédente.
Les mesures du baromètre (`BAR-*`, `SPEC.md` §13.4) n'ont pas de contrat JSON : leurs paramètres
sont déclarés dans le script et écrits dans la sortie.
