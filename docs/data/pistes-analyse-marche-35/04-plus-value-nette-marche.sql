\timing off
CREATE TEMP TABLE sales AS
SELECT tp.parcel_id, t.mutation_date d, tp.allocated_price_eur p, tp.surface_m2 s, t.commune_code
  FROM observation.transaction_property tp JOIN observation.transaction t ON t.id=tp.transaction_id
 WHERE tp.property_type='Maison' AND tp.allocation_method='single_property_full_price' AND tp.parcel_id IS NOT NULL
   AND t.mutation_nature='Vente' AND tp.surface_m2 > 0 AND tp.allocated_price_eur > 0;
CREATE TEMP TABLE ref AS SELECT commune_code, extract(year from d) y, percentile_cont(0.5) WITHIN GROUP (ORDER BY p/s) med, count(*) n FROM sales GROUP BY 1,2;
CREATE TEMP TABLE pairs AS
SELECT * FROM (SELECT parcel_id, commune_code, d, p, s, lag(d) OVER w d0, lag(p) OVER w p0, lag(s) OVER w s0 FROM sales WINDOW w AS (PARTITION BY parcel_id ORDER BY d)) x WHERE d0 IS NOT NULL AND d-d0 > 180;
CREATE TEMP TABLE pe AS
SELECT pr.*, (pr.p/pr.p0) ratio, (r1.med/r0.med) market, (pr.p/pr.p0)/(r1.med/r0.med) excess, (pr.p0/pr.s0)/r0.med entry_rel, (pr.d-pr.d0)/365.25 yrs
  FROM pairs pr JOIN ref r0 ON r0.commune_code=pr.commune_code AND r0.y=extract(year from pr.d0) AND r0.n>=15
                JOIN ref r1 ON r1.commune_code=pr.commune_code AND r1.y=extract(year from pr.d) AND r1.n>=15
 WHERE pr.s = pr.s0;
\echo '== P6d plus-value nette de marché (ratio prix / évolution médiane commune, surface inchangée) : tranche délai | paires | excess Q1 | médiane | Q3'
SELECT CASE WHEN yrs<1 THEN '0.5-1 an' WHEN yrs<2 THEN '1-2 ans' WHEN yrs<3 THEN '2-3 ans' WHEN yrs<5 THEN '3-5 ans' ELSE '5 ans +' END tr, count(*),
       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY excess)::numeric,2), round(percentile_cont(0.5) WITHIN GROUP (ORDER BY excess)::numeric,2), round(percentile_cont(0.75) WITHIN GROUP (ORDER BY excess)::numeric,2)
  FROM pe GROUP BY 1 ORDER BY min(yrs);
\echo '== P6e selon le prix d entrée relatif à la commune (achat décoté ou non), revente < 3 ans : tranche entrée | paires | excess médiane | Q3 | part excess > 1.2'
SELECT CASE WHEN entry_rel<0.6 THEN '< 60 % médiane' WHEN entry_rel<0.8 THEN '60-80 %' WHEN entry_rel<1.0 THEN '80-100 %' ELSE '>= 100 %' END e, count(*),
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY excess)::numeric,2), round(percentile_cont(0.75) WITHIN GROUP (ORDER BY excess)::numeric,2),
       round(100.0*count(*) FILTER (WHERE excess>1.2)/count(*),1)
  FROM pe WHERE yrs<3 GROUP BY 1 ORDER BY min(entry_rel);
\echo '== P6f combien de communes ont >= 10 paires de revente < 3 ans (support pour une mesure locale)'
SELECT count(*) FILTER (WHERE n>=10), count(*) FILTER (WHERE n>=30), count(*) FROM (SELECT commune_code, count(*) n FROM pe WHERE yrs<3 GROUP BY 1) x;
