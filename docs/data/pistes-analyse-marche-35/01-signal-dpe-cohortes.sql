\timing off
-- parcelle × DPE via bâtiment en relation certaine
CREATE TEMP TABLE dpe_parcel AS
SELECT link.parcel_id, a.dpe_number,
       coalesce(a.deposited_at, a.assessment_date) AS dep,
       a.energy_label, a.properties->>'type_batiment' AS tb,
       (a.properties->>'numero_dpe_remplace') IS NOT NULL AS replaces,
       (a.properties->>'numero_dpe_immeuble_associe') IS NOT NULL AS from_immeuble,
       a.properties->>'methode_application_dpe' AS meth
  FROM observation.energy_assessment a
  JOIN reference.building_parcel link ON link.building_id = a.building_id AND link.relation_status='certain';
CREATE INDEX ON dpe_parcel(parcel_id);
CREATE TEMP TABLE first_dpe AS
SELECT DISTINCT ON (parcel_id) parcel_id, dep, energy_label, tb, replaces, from_immeuble, meth
  FROM dpe_parcel ORDER BY parcel_id, dep;
CREATE TEMP TABLE mut AS
SELECT DISTINCT tp.parcel_id, t.mutation_date
  FROM observation.transaction_property tp JOIN observation.transaction t ON t.id=tp.transaction_id
 WHERE tp.parcel_id IS NOT NULL AND t.mutation_nature LIKE 'Vente%';
CREATE INDEX ON mut(parcel_id, mutation_date);
-- P1 cohortes annuelles, conversion à 12 mois
\echo '== P1 cohortes (premier DPE par année) : parcelles | vendues<=365j | taux'
SELECT extract(year from dep)::int y, count(*),
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep AND m.mutation_date <= f.dep+365)),
       round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep AND m.mutation_date <= f.dep+365))/count(*),2)
  FROM first_dpe f WHERE dep < '2025-01-01' GROUP BY 1 ORDER BY 1;
\echo '== P1bis premier DPE ≠ premier de l extrait : parcelles 2023-2024 ayant un DPE antérieur (impossible par construction) → part des DPE 2023/2024 qui ne sont pas les premiers de leur parcelle'
SELECT extract(year from dep)::int y, count(*) total,
       count(*) FILTER (WHERE (parcel_id, dep) NOT IN (SELECT parcel_id, dep FROM first_dpe)) not_first
  FROM dpe_parcel WHERE dep BETWEEN '2022-01-01' AND '2024-12-31' GROUP BY 1 ORDER BY 1;
\echo '== P2 courbe de conversion, cohorte 2023 (suivi 24 mois) et 2024 (12 mois) : mois | cumul %'
WITH c AS (SELECT f.parcel_id, f.dep, extract(year from f.dep)::int y,
                  (SELECT min(m.mutation_date) FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep) AS first_sale
             FROM first_dpe f WHERE dep BETWEEN '2023-01-01' AND '2024-12-31')
SELECT y, h.m, round(100.0*count(*) FILTER (WHERE first_sale <= dep + h.m*30)/count(*),2) AS cum_pct
  FROM c CROSS JOIN (VALUES (1),(2),(3),(6),(9),(12),(18),(24)) h(m)
 WHERE (y=2024 AND h.m<=12) OR y=2023
 GROUP BY 1,2 ORDER BY 1,2;
\echo '== P3 lift par étiquette, cohortes 2023+2024 : étiquette | parcelles | taux 12 mois'
SELECT coalesce(energy_label,'?') l, count(*),
       round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep AND m.mutation_date <= f.dep+365))/count(*),2)
  FROM first_dpe f WHERE dep BETWEEN '2023-01-01' AND '2024-12-31' GROUP BY 1 ORDER BY 1;
\echo '== P4 par type de bâtiment / remplacement / issu d immeuble, cohortes 2023+2024'
SELECT tb, replaces, from_immeuble, count(*),
       round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep AND m.mutation_date <= f.dep+365))/count(*),2)
  FROM first_dpe f WHERE dep BETWEEN '2023-01-01' AND '2024-12-31' GROUP BY 1,2,3 ORDER BY 4 DESC;
\echo '== P5 dépôts par mois (tous DPE rattachés) et conversion 12 mois des premiers DPE, 2022-01 → 2024-12'
SELECT to_char(d.dep,'YYYY-MM') mo, count(*) deposits,
       (SELECT count(*) FROM first_dpe f WHERE date_trunc('month',f.dep)=date_trunc('month',d.dep)) firsts,
       (SELECT round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM mut m WHERE m.parcel_id=f.parcel_id AND m.mutation_date > f.dep AND m.mutation_date <= f.dep+365))/nullif(count(*),0),1)
          FROM first_dpe f WHERE date_trunc('month',f.dep)=date_trunc('month',d.dep)) conv
  FROM dpe_parcel d WHERE d.dep BETWEEN '2022-01-01' AND '2025-12-31' GROUP BY date_trunc('month',d.dep), 1 ORDER BY 1;
