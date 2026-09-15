# D6b — Voir les diagnostics d'une parcelle, pour vérifier que l'appariement DPE tient

**Version :** v0.5 · **Taille :** S · **État :** Terminé
**Touche :** backend/src/immo/explorer.py, backend/src/immo/api/routes/explorer.py, apps/web/src/App.tsx, docs/data/dpe-verification-35.md
**Dépend de :** D4 · **Bloque :** —
**Scindé de :** [D6](./D6-revue-manuelle-metier.md), 15 septembre 2026

> **C'est un instrument de vérification, pas une fonctionnalité produit.** Symétrique de
> [D6a](./D6a-verification-mutations-parcelle.md), qui a fait le même geste pour DVF et y a trouvé
> quatre défauts structurels.

## Pourquoi maintenant, et pas dans D6

[D6](./D6-revue-manuelle-metier.md) revoit la **sélection** — le diagnostic retenu est-il le bon,
les `ambiguous_match` sont-ils justement écartés. Cela suppose la règle de sélection de
`features.py` et les segments que [E1](./E1-profiling-distributions.md) doit encore produire. D6
attend D5 ; il est loin.

Ce ticket vérifie autre chose, de plus élémentaire et de disponible aujourd'hui : **les
diagnostics rattachés à une parcelle sont-ils ceux de ses bâtiments ?** Ni segment, ni comparable,
ni score — seulement l'import et le rattachement.

**208 086 diagnostics sont en base et rien ne les montre.** L'unique lecture qui les expose,
`GET /property-units/{id}/market-context`, joint `meta.active_dataset_release`, qui **ne contient
aucune ligne pour DS-07** : elle renvoie donc toujours `energy_assessment: null`. La donnée est
importée, contrôlée, rapportée — et invisible.

## Ce que l'exploration en base a établi

Le chemin de rattachement existe déjà et n'a rien à inventer :

```text
energy_assessment.building_id  →  reference.building (RNB)
                               →  reference.building_parcel  →  reference.parcel
```

| Constat | Mesure |
|---|---:|
| Diagnostics rattachés à un bâtiment RNB | 136 628 |
| … dont atteignant une parcelle | **136 294** |
| Parcelles portant au moins un diagnostic certain | 46 695 |
| Relations `certain` par diagnostic | **exactement 1, sans exception** |
| Parcelles touchées en comptant les relations `ambiguous` | 2,24 en moyenne |
| Diagnostics sans étiquette | **0** |
| Maximum sur une seule parcelle | **526** (`35238000AZ0487`, 3 étiquettes distinctes) |

Deux conséquences de conception :

1. **Le bloc va sur la fiche parcelle**, à côté du bloc DVF — pas sur la fiche bâtiment. Celle-ci
   affiche un bâtiment **cadastral** (`reference.active_cadastral_building`), alors que le DPE est
   rattaché à un enregistrement **RNB** (`reference.building`, qui ne contient que du RNB :
   741 379 lignes, aucune cadastrale). Il n'existe aucun pont entre les deux, et en fabriquer un
   par géométrie serait un raccordement inventé.
2. **Les diagnostics rattachés à la seule adresse — 71 458 — restent hors de cet écran.** Les
   poser sur une parcelle demanderait la relation adresse ↔ parcelle, que
   [B4](./B4-revue-manuelle-appariements.md) a établie non vérifiable, avec un taux d'erreur
   d'environ 24 % irréductible. Le bloc doit le dire, pas le contourner.

## Ce qu'il faut montrer

| Colonne | Pourquoi |
|---|---|
| Date du diagnostic | un DPE ancien reste valide, sa fraîcheur est une information distincte |
| Étiquette et consommation | la valeur observée, jamais interprétée en état du bâti |
| Rattachement `certain` / `ambiguous` | un bâtiment chevauche 2,24 parcelles en moyenne |
| Numéro du diagnostic et release | c'est ainsi qu'un mélange de versions de transformation se voit |

**La confiance d'appariement ne s'affiche pas comme une colonne utile ici** : elle vaut 1,0 pour
tous les rattachés-bâtiment, parce que l'`id_rnb` est **déclaré par le producteur** et repris tel
quel. C'est précisément l'hypothèse que cet écran met à l'épreuve — personne n'a jamais vérifié
que l'identifiant déclaré désigne le bon bâtiment. Une confiance héritée n'est pas une confiance
vérifiée.

## Ce que ce ticket ne doit pas faire

- **Devenir un consultatif DPE.** Pas d'entrée de menu, pas de filtre par étiquette, pas d'export.
  L'accès se fait depuis une parcelle déjà sélectionnée.
- **Colorer la carte de A à G.** Une classe F rendue en rouge sur une tuile devient un signal de
  dégradation — ce que le produit s'interdit. Et les tuiles ne portent que du rendu.
- **Tirer un signal d'une absence.** Une parcelle sans diagnostic est sans diagnostic. Ce n'est ni
  une vacance, ni une dégradation.
- **Dériver quoi que ce soit.** Pas de moyenne d'étiquettes sur la parcelle, pas de classe
  « dominante » : agréger 526 diagnostics en une note fabriquerait une valeur qui n'existe pas.

## Travail à réaliser

1. Exposer les diagnostics d'une parcelle par l'API privée, sous RLS — jamais par les tuiles.
2. Afficher le bloc dans la fiche parcelle, replié, chargé à la demande comme celui de D6a.
3. Vérifier sur un échantillon : les diagnostics sont-ils plausibles pour le bâti de la parcelle ?
   Inclure les cas extrêmes — 526, 449 et 438 diagnostics — et des communes aux deux bouts du taux
   d'appariement : SAINT-JUST (14,75 %) et BRÉCÉ (80,17 %).
4. Consigner le résultat dans `docs/data/dpe-verification-35.md`, y compris s'il ne trouve rien.

## Critères d'acceptation

- les diagnostics d'une parcelle sont consultables sur données réelles, sans fixture ;
- un rattachement ambigu se distingue à l'écran d'un rattachement certain ;
- la limite adresse-seule est énoncée dans le bloc, pas seulement dans un rapport ;
- le rapport de vérification est écrit, et dit ce qui a été regardé et combien.

## Résolution — 15 septembre 2026

Preuve : [`docs/data/dpe-verification-35.md`](../data/dpe-verification-35.md).

Livré : `list_parcel_energy_assessments`, la route `/parcels/{id}/energy-assessments` sous RLS, et
un bloc replié dans la fiche parcelle de l'Explorer. Trois tests de contrat couvrent le
rattachement ambigu qui doit rester visible et la surface non déclarée qui doit rester nulle ; un
test e2e vérifie qu'une fiche ne garde pas les diagnostics de la parcelle précédente.

**Quatre constats, dont un qui change ce qu'on croyait savoir :**

| Constat | Mesure |
|---|---:|
| Un `id_rnb` saisi par logiciel est plus souvent incohérent qu'un identifiant repris du RNB | **5,8×** — 0,427 % contre 0,073 % |
| Le rattachement place les diagnostics sur un bâti de la bonne taille | 0,12 % au-delà de 4× l'emprise |
| Le filtre « rattaché bâtiment » retient un diagnostic périmé et cache son remplaçant | 2 cas |
| La parcelle aux 526 diagnostics est une résidence collective cohérente, pas un défaut | 24 720 m² sur 2 792 m² d'emprise |

Le premier justifie a posteriori d'afficher la provenance de l'identifiant plutôt qu'une
confiance d'appariement qui vaut 1,0 pour tous les rattachés-bâtiment. **Une confiance héritée
d'un identifiant déclaré n'est pas une confiance vérifiée** — et jusqu'ici, rien ne le disait.

Le troisième est à reprendre par [D6](./D6-revue-manuelle-metier.md) : le filtre de rattachement
n'est pas neutre vis-à-vis de la fraîcheur, et rien ne garantit qu'un diagnostic plus récent soit
mieux rattaché.

**Ce que ce ticket n'a pas changé :** DS-07 reste `display_only`, `REN-001..008` reste non
matérialisé en attendant [BUG-13](./BUG-13-sujet-des-features-batiment.md), et aucune étiquette
n'atteint la carte ni le score.
