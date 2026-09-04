# Contrats versionnés

Ce dossier contient les interfaces stables entre les sources, les pipelines, le backend et le frontend.

- `datasets/` : schémas et règles d’acceptation par dataset et release ;
- `features/` : définitions déclaratives, provenance et politiques de valeurs manquantes ;
- `scoring/` : registres actifs, définitions de score, transformations et règles d'éligibilité ;
- `openapi/` : contrat HTTP généré depuis FastAPI.

Les contrats de datasets et de features sont ajoutés dans les versions qui les introduisent. Une modification incompatible crée une nouvelle version ; elle ne remplace pas silencieusement la précédente.
