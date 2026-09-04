# G4 — Couverture documentée département / EPCI / commune

**Version :** v0.8 · **Taille :** M · **État :** À faire
**Dépend de :** G2 · **Bloque :** G8

## Contexte à charger

- `backend/src/immo/brittany_pilot.py`
- `backend/src/immo/api/routes/brittany_pilot.py`
- `docs/data/brittany-pilot-v0.8-report.md`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

La traçabilité indique : « Couverture département/EPCI/commune — table versionnée et rapport vide —
**mesure réelle absente** ». La structure existe, elle n'a jamais été remplie.

L'échelon **EPCI** est le seul des trois qui ne soit pas déjà couvert par les métriques communales
existantes : c'est aussi l'échelon auquel les documents d'urbanisme sont souvent portés (PLUi), donc
celui auquel la couverture GPU se mesure naturellement.

## Contenu attendu

À chacun des trois échelons, et pour chaque source :

| Grandeur | Détail |
|---|---|
| Couverture | unités renseignées / unités totales, avec les volumes |
| Fraîcheur | date de la donnée la plus récente et son âge |
| Publiabilité | score publié / non publié, avec la raison |
| Motifs d'absence | ventilés, jamais agrégés en un taux unique |

## Points de vigilance

- La couverture doit être **calculée**, pas déclarée. Une commune où la source existe mais où
  aucune unité n'est renseignée a une couverture nulle, pas une couverture inconnue.
- Distinguer trois cas à chaque échelon : non couvert, couvert partiellement, couvert. Les
  agréger produirait exactement l'ambiguïté que [C2](./C2-zone-non-couverte.md) cherche à éviter.
- Le rattachement commune → EPCI doit venir d'un référentiel versionné, pas d'une table figée : les
  périmètres d'EPCI changent.
- Un taux régional moyen n'a aucune valeur opérationnelle : c'est la dispersion entre communes qui
  informe.

## Critères d'acceptation

- couverture publiée aux trois échelons, pour chaque source ;
- volumes publiés à côté des taux ;
- motifs d'absence ventilés ;
- rattachement commune → EPCI versionné ;
- la ligne « Couverture département/EPCI/commune » de la traçabilité passe à validé.

## Preuve à produire

Rapport `docs/data/brittany-coverage.md`, généré depuis la base, avec sa commande de régénération.
