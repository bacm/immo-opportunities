# Sonde — un signal d'abandon existe-t-il dans les données ouvertes du 35 ?

**Mesuré le :** 15 septembre 2026 · **Sources :** DS-04 BD TOPO (`etat_de_l_objet`, `usage_1`,
`date_d_apparition`, `nombre_de_logements`), DS-06 DVF, DS-07 DPE, relations bâtiment ↔ parcelle
`certain` · **Statut :** sondage en lecture, **non recompté**
**Demandé par :** conversation du 15 septembre 2026 — « l'idée initiale était de trouver des biens
à l'abandon »

## Question

L'idée d'origine du projet (`docs/archive/explo-2026-08.md`) était de repérer des biens vacants,
dégradés ou abandonnés. La version 0.2 de `SPEC.md` l'avait reléguée en module expérimental,
ADR-016 l'a retirée sans l'évaluer. Cette sonde mesure ce que les données déjà en base peuvent en
dire, avant toute décision.

## Population

Maisons individuelles : bâtiments BD TOPO à `usage_1 = 'Résidentiel'`, au plus deux logements,
rattachés à un bâtiment RNB par `identifiants_rnb` et à une parcelle par une relation `certain`.

## Résultat

| Population | Département 35 | Cesson-Sévigné (35051) |
|---|---:|---:|
| Maisons individuelles | 295 980 | 4 151 |
| Sans aucun DPE déposé et sans mutation depuis 2014 | 197 710 (66,8 %) | 2 868 (69,1 %) |
| Idem, `date_d_apparition` avant 1950 | 65 742 | 251 |
| Idem, avant 1900 | 45 107 | 177 |
| `etat_de_l_objet = 'En ruine'` | 39 | 0 |

Sur l'ensemble des 974 172 bâtiments BD TOPO du 35, 729 sont « en ruine », dont 63 à usage
résidentiel ; 472 sont d'usage indifférencié.

## Lecture

- **Le silence n'est pas un signal.** Deux tiers des maisons n'ont ni DPE ni vente depuis douze
  ans : c'est l'état normal du parc. Restreindre à l'ancien ne fait que retrouver la pyramide des
  âges du bâti.
- **Le seul marqueur direct est marginal** : 39 maisons « en ruine » sur 296 000, sans
  vérification de sa fraîcheur.
- **Ce qui discrimine l'abandon n'est pas ouvert** : vacance à l'adresse (LOVAC), durée de
  détention et âge du propriétaire (Fichiers fonciers), successions (fichier des décès, exclu par
  `SPEC.md` §13.6). Tous sont réservés aux ayants droit ou interdits par décision.
- **Aucune vérité terrain** n'existe dans le dépôt pour calibrer un indice. Un « indice de
  signaux compatibles avec une vacance » produirait une liste de 197 710 lignes sans précision
  mesurable.

## Réserves

- `date_d_apparition` est renseignée à 99 % sur cette population, contre 44,6 % dans
  `exploratory-candidates-35051.md` : populations différentes, à instruire au recompte.
- Le rattachement DPE au bâtiment plafonne à 59 % : une part des maisons « sans DPE » en ont un
  rattaché à la seule adresse. Le taux de silence est donc surestimé, sans changer la conclusion.
- Non recompté. Aucun chiffre de ce fichier ne sort du dépôt sans `recompte-preuve`.

## Requête

```sql
with bdtopo as (
  select 'building:rnb:'||unnest(string_to_array(properties->>'identifiants_rnb','/')) rnb_id,
         properties->>'usage_1' u, nullif(left(properties->>'date_d_apparition',4),'')::int built,
         nullif(properties->>'nombre_de_logements','')::int dw, properties->>'etat_de_l_objet' etat
  from meta.entity_source_observation
  where source_entity_type='bdtopo_building' and properties->>'identifiants_rnb' is not null),
house as (
  select b.rnb_id, bp.parcel_id, left(replace(bp.parcel_id,'parcel:cadastre:',''),5) commune, b.built, b.etat
  from bdtopo b join reference.building_parcel bp on bp.building_id=b.rnb_id and bp.relation_status='certain'
  where b.u='Résidentiel' and coalesce(b.dw,1)<=2),
flagged as (
  select h.*,
    exists (select 1 from observation.energy_assessment e where e.building_id=h.rnb_id) has_dpe,
    exists (select 1 from observation.transaction_property tp join observation.transaction t on t.id=tp.transaction_id
            where tp.parcel_id=h.parcel_id and t.mutation_date>=date '2014-01-01') mut_since_2014
  from house h)
select count(distinct parcel_id),
  count(distinct parcel_id) filter (where not has_dpe and not mut_since_2014),
  count(distinct parcel_id) filter (where built<1950 and not has_dpe and not mut_since_2014),
  count(distinct parcel_id) filter (where built<1900 and not has_dpe and not mut_since_2014),
  count(distinct parcel_id) filter (where etat='En ruine')
from flagged;
```
