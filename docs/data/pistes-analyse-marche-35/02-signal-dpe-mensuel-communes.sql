\timing off
CREATE TEMP TABLE dpe_parcel AS
SELECT link.parcel_id, link.relation_status, coalesce(a.deposited_at, a.assessment_date) AS dep, a.energy_label, a.properties->>'type_batiment' AS tb, a.commune_code
  FROM observation.energy_assessment a
  JOIN reference.building_parcel link ON link.building_id = a.building_id;
CREATE INDEX ON dpe_parcel(parcel_id);
CREATE TEMP TABLE first_dpe AS
SELECT DISTINCT ON (parcel_id) parcel_id, dep, energy_label, tb, commune_code FROM dpe_parcel WHERE relation_status='certain' ORDER BY parcel_id, dep;
CREATE TEMP TABLE mut AS
SELECT DISTINCT tp.parcel_id, t.mutation_date FROM observation.transaction_property tp JOIN observation.transaction t ON t.id=tp.transaction_id
 WHERE tp.parcel_id IS NOT NULL AND t.mutation_nature LIKE 'Vente%';
CREATE INDEX ON mut(parcel_id, mutation_date);
\echo '== Ecart de comptage : cohorte 2024 selon le filtre de relation'
SELECT 'certain' f, count(*) FROM (SELECT DISTINCT ON (parcel_id) parcel_id, dep FROM dpe_parcel WHERE relation_status='certain' ORDER BY parcel_id, dep) x WHERE dep BETWEEN '2024-01-01' AND '2024-12-31'
UNION ALL SELECT 'toutes relations', count(*) FROM (SELECT DISTINCT ON (parcel_id) parcel_id, dep FROM dpe_parcel ORDER BY parcel_id, dep) x WHERE dep BETWEEN '2024-01-01' AND '2024-12-31'
UNION ALL SELECT 'DPE 2024 (pas premier) toutes relations, parcelles distinctes', count(DISTINCT parcel_id) FROM dpe_parcel WHERE dep BETWEEN '2024-01-01' AND '2024-12-31';
\echo '== P5 dépôts par mois (rattachés, certain) | premiers DPE | conversion 12 mois des premiers'
WITH m AS (SELECT date_trunc('month',dep)::date mo, count(*) deposits FROM dpe_parcel WHERE relation_status='certain' AND dep BETWEEN '2022-01-01' AND '2025-12-31' GROUP BY 1),
f AS (SELECT date_trunc('month',dep)::date mo, count(*) firsts,
             round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut x WHERE x.parcel_id=f.parcel_id AND x.mutation_date > f.dep AND x.mutation_date <= f.dep+365))/count(*),1) conv
        FROM first_dpe f WHERE dep BETWEEN '2022-01-01' AND '2024-12-31' GROUP BY 1)
SELECT to_char(m.mo,'YYYY-MM'), m.deposits, f.firsts, f.conv FROM m LEFT JOIN f USING (mo) ORDER BY 1;
\echo '== P8 délai dépôt→acte (médiane jours) et conversion 12 mois par commune, 10 communes les plus fournies, cohortes 2023-2024 maisons'
WITH c AS (SELECT f.parcel_id, f.commune_code, f.dep, (SELECT min(mutation_date) FROM mut x WHERE x.parcel_id=f.parcel_id AND x.mutation_date>f.dep) fs
             FROM first_dpe f WHERE tb='maison' AND dep BETWEEN '2023-01-01' AND '2024-12-31')
SELECT commune_code, count(*) n, round(100.0*count(*) FILTER (WHERE fs<=dep+365)/count(*),1) conv12,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY fs-dep) FILTER (WHERE fs<=dep+365) med_days
  FROM c GROUP BY 1 ORDER BY n DESC LIMIT 10;
