# E8 — Produire une liste exploratoire de candidats, confrontable à un professionnel

**Version :** v0.6 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** pipelines/scripts/exploratory_candidates.py, pipelines/tests/test_exploratory_candidates.py, docs/data/exploratory-candidates/, Makefile
**Dépend de :** — · **Bloque :** E9
**Demandé par :** revue de but du 15 septembre 2026

## Contexte à charger

- `docs/backlog/G8-pilote-trois-professionnels.md` (protocole de référence, section « Protocole »)
- `docs/backlog/BUG-11-unite-fonciere-degeneree.md`
- `docs/data/market-data-quality-35.md`
- `SPEC.md` §5 (hypothèses H1 à H5) et §7 (stratégies) — ces sections seulement

Ne rien charger d'autre sans nécessité démontrée.

## Pourquoi ce ticket existe

Le plan actuel place la seule validation qui compte — [G8](./G8-pilote-trois-professionnels.md) —
derrière D6, E1, E2, E3, F1, F2, F3, G1, G3, G4, G5 et G6, dont une extension XL à trois
départements. H1 à H5 ne sont mesurées nulle part. Le produit a été écrit jusqu'à v0.8 avant qu'on
sache si le signal existe et si quelqu'un paierait.

Or **la base contient déjà de quoi répondre** : 1 333 327 unités, 20 M de valeurs de features,
133 066 mutations DVF, 21 136 zones d'urbanisme. Une sonde en lecture sur Cesson-Sévigné (35051)
ramène 679 candidats plausibles sur 9 329 unités. Le classement est donc testable aujourd'hui,
sur une commune, sans profiling et sans publication.

Ce ticket ne remplace pas G8 et ne le préempte pas : il le précède à échelle réduite, pour éviter
de payer le reste du backlog avant de savoir si la promesse tient.

## Ce que ce ticket ne fait pas

- **Il ne publie rien.** Aucun `OpportunitySnapshot`, aucun changement de `publication_eligible`,
  aucune unité ne devient publiable. `entity_resolution_incomplete` reste en place — c'est ce qui
  autorise ce ticket à exister sans contredire [BUG-11](./BUG-11-unite-fonciere-degeneree.md).
- **Il ne fige aucun seuil produit.** Les paramètres du filtre sont **arbitraires et déclarés tels
  quels**, dans le script comme dans le rapport. Ils ne sont pas un profiling, ils n'anticipent pas
  [E1](./E1-profiling-distributions.md), et le professionnel est invité à les contester — c'est
  même l'une des informations recherchées.
- **Il ne passe pas par l'Explorer.** L'Explorer n'affiche que des unités publiées ; le rendre
  capable d'afficher l'inverse serait un contournement du garde-fou. La sortie est un document
  autonome.

## Travail à réaliser

### 1. Deux listes, pas une

H1 dit : « le classement bat un tri cadastral simple ». La mesure exige donc les deux, et
l'exigence d'aveugle de G8 s'applique ici :

| Liste | Contenu |
|---|---|
| **Baseline** | tri cadastral simple — surface de parcelle décroissante parmi les parcelles bâties en zone U |
| **Classement** | les mêmes unités ordonnées par les signaux disponibles : emprise au sol, surface libre, largeur, zonage, contraintes connues, présence et récence de comparables |

Les deux listes sont mélangées et anonymisées dans le document remis : le relecteur ne doit pas
savoir de quelle liste vient un candidat. La correspondance est conservée à part.

### 2. Commune paramétrable

La commune est un paramètre, pas une constante : elle doit correspondre au territoire du
professionnel recruté par [E9](./E9-test-terrain-deux-professionnels.md). Communes entièrement
zonées et riches en DVF, vérifiées en base : `35051` Cesson-Sévigné, `35093` Dinard, `35115`
Fougères, `35047` Bruz, `35236` Redon, `35012` Bain-de-Bretagne — soit un périurbain, un littoral,
deux villes moyennes et un bourg rural.

### 3. Chaque candidat porte ses preuves

Sans elles, H3 n'est pas mesurable et le relecteur juge une adresse, pas un raisonnement :
identifiant cadastral, commune, surface, emprise bâtie, surface libre, largeur, nombre de
bâtiments, zone d'urbanisme et document dont elle vient, contraintes connues, comparables DVF
retenus avec leur date, DPE si rattaché, risques à granularité fine. **Une valeur absente est
affichée absente avec son motif**, jamais omise ni remplacée.

### 4. Dire ce que l'objet est

Chaque ligne doit annoncer qu'elle désigne une **parcelle**, pas un bien, avec la limite de
[BUG-11](./BUG-11-unite-fonciere-degeneree.md) écrite en clair dans le document. C'est une
condition de validité du test : si le professionnel rejette la liste pour cette raison, il faut
que ce soit un constat et non un malentendu.

### 5. Sortie lisible hors application

Un document — CSV pour le dépouillement, et une forme imprimable ou cartographique pour la session
— utilisable par quelqu'un qui n'a pas de compte et ne verra pas l'Explorer.

## Tests obligatoires

- le script ne peut pas écrire dans `scoring.*` ni modifier `publication_eligible` ;
- une unité dont une feature est absente apparaît avec son `missing_reason`, jamais à zéro ;
- baseline et classement produisent des ordres différents sur un jeu de contrôle — sinon la
  comparaison de H1 est vide de sens et il faut le savoir avant la session ;
- la correspondance liste ↔ candidat est reproductible depuis la graine enregistrée.

## Critères d'acceptation

- deux listes produites sur une commune réelle du 35, mélangées et traçables ;
- paramètres du filtre déclarés arbitraires dans le script et dans le rapport ;
- preuves complètes par candidat, absences motivées ;
- limite « parcelle et non bien » écrite dans le document remis ;
- rien de publié, aucun snapshot créé.

## Preuve à produire

`docs/data/exploratory-candidates-35.md` : commune retenue et pourquoi, paramètres et leur
caractère arbitraire, entonnoir chiffré, méthode des deux listes, graine, limites connues.
