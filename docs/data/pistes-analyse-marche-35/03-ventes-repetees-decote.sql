\timing off
-- ventes simples de maisons avec prix alloué, 2014-2025
CREATE TEMP TABLE sales AS
SELECT tp.parcel_id, t.mutation_date d, tp.allocated_price_eur p, tp.surface_m2 s, t.commune_code, t.id tid
  FROM observation.transaction_property tp JOIN observation.transaction t ON t.id=tp.transaction_id
 WHERE tp.property_type='Maison' AND tp.allocation_method='single_property_full_price' AND tp.parcel_id IS NOT NULL
   AND t.mutation_nature='Vente' AND tp.surface_m2 > 0 AND tp.allocated_price_eur > 0;
CREATE INDEX ON sales(parcel_id, d);
\echo '== P6 ventes répétées de maisons (même parcelle, deux ventes simples, > 180 jours) : total paires | délai médian années | ratio prix médian | ratio annualisé médian'
WITH pairs AS (
  SELECT parcel_id, d, p, s, lag(d) OVER w d0, lag(p) OVER w p0, lag(s) OVER w s0 FROM sales WINDOW w AS (PARTITION BY parcel_id ORDER BY d))
, pp AS (SELECT *, (d-d0)/365.25 yrs, p/p0 ratio FROM pairs WHERE d0 IS NOT NULL AND d-d0 > 180)
SELECT count(*), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY yrs)::numeric,2), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ratio)::numeric,3),
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY power(ratio, 1/yrs))::numeric,3) FROM pp;
\echo '== P6b par délai entre les deux ventes : tranche | paires | ratio Q1 | médiane | Q3 | part surface changée'
WITH pairs AS (
  SELECT parcel_id, d, p, s, lag(d) OVER w d0, lag(p) OVER w p0, lag(s) OVER w s0 FROM sales WINDOW w AS (PARTITION BY parcel_id ORDER BY d))
, pp AS (SELECT *, (d-d0)/365.25 yrs, p/p0 ratio FROM pairs WHERE d0 IS NOT NULL AND d-d0 > 180)
SELECT CASE WHEN yrs<1 THEN '0.5-1 an' WHEN yrs<2 THEN '1-2 ans' WHEN yrs<3 THEN '2-3 ans' WHEN yrs<5 THEN '3-5 ans' ELSE '5 ans +' END tr, count(*),
       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY ratio)::numeric,2), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ratio)::numeric,2), round(percentile_cont(0.75) WITHIN GROUP (ORDER BY ratio)::numeric,2),
       round(100.0*count(*) FILTER (WHERE s<>s0)/count(*),1)
  FROM pp GROUP BY 1 ORDER BY min(yrs);
\echo '== P6c revente < 3 ans avec surface bâtie augmentée (extension/rénovation lourde) : paires | ratio médian | ratio par m² médian'
WITH pairs AS (
  SELECT parcel_id, d, p, s, lag(d) OVER w d0, lag(p) OVER w p0, lag(s) OVER w s0 FROM sales WINDOW w AS (PARTITION BY parcel_id ORDER BY d))
SELECT count(*), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY p/p0)::numeric,2), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY (p/s)/(p0/s0))::numeric,2)
  FROM pairs WHERE d0 IS NOT NULL AND d-d0 BETWEEN 181 AND 1095 AND s > s0;
\echo '== P7 décote énergétique : ventes de maisons 2022-2025 avec DPE déposé dans les 24 mois avant l acte ; prix/m² relatif à la médiane commune×année ; étiquette | ventes | ratio Q1 | médiane | Q3'
CREATE TEMP TABLE dpe_parcel AS
SELECT link.parcel_id, coalesce(a.deposited_at, a.assessment_date) dep, a.energy_label
  FROM observation.energy_assessment a JOIN reference.building_parcel link ON link.building_id=a.building_id AND link.relation_status='certain'
 WHERE a.properties->>'type_batiment'='maison' AND a.energy_label IS NOT NULL;
CREATE INDEX ON dpe_parcel(parcel_id);
CREATE TEMP TABLE sd AS
SELECT s.*, (SELECT energy_label FROM dpe_parcel x WHERE x.parcel_id=s.parcel_id AND x.dep <= s.d AND x.dep > s.d-730 ORDER BY x.dep DESC LIMIT 1) lab
  FROM sales s WHERE d >= '2022-01-01';
CREATE TEMP TABLE ref AS SELECT commune_code, extract(year from d) y, percentile_cont(0.5) WITHIN GROUP (ORDER BY p/s) med, count(*) n FROM sd GROUP BY 1,2;
SELECT lab, count(*), round(percentile_cont(0.25) WITHIN GROUP (ORDER BY (p/s)/med)::numeric,2), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY (p/s)/med)::numeric,2), round(percentile_cont(0.75) WITHIN GROUP (ORDER BY (p/s)/med)::numeric,2)
  FROM sd JOIN ref ON ref.commune_code=sd.commune_code AND ref.y=extract(year from sd.d) WHERE ref.n>=20 GROUP BY 1 ORDER BY 1;
\echo '== P7b même chose, prix/m² absolu médian par étiquette (indicatif)'
SELECT lab, count(*), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY p/s)::numeric) FROM sd GROUP BY 1 ORDER BY 1;
