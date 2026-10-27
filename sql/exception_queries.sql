-- Run in DuckDB against data/recon.duckdb (created by run.py)

-- 1. Exceptions and exposure by control
SELECT control, COUNT(*) AS exceptions, ROUND(SUM(exposure_usd), 0) AS exposure_usd
FROM exceptions GROUP BY control ORDER BY exposure_usd DESC;

-- 2. P1 exceptions to clear first, largest first
SELECT e.trade_id, e.control, s.desk, s.entity, ROUND(e.exposure_usd, 0) AS exposure_usd, e.age_days
FROM exceptions e JOIN subledger s USING (trade_id)
WHERE e.priority = 'P1' ORDER BY e.exposure_usd DESC LIMIT 20;

-- 3. Which desk-entity pairs generate the most breaks (root-cause hunting)
SELECT s.desk, s.entity, COUNT(*) AS exceptions
FROM exceptions e JOIN subledger s USING (trade_id)
GROUP BY 1, 2 ORDER BY exceptions DESC LIMIT 10;
