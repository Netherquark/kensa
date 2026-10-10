-- HiveQL / Spark SQL Rollup & Cube Multidimensional Analytics
-- Evaluates sub-totals across discrete electron and muon multiplicity combinations
SELECT
  COALESCE(CAST(n_electrons AS STRING), 'ALL_ELECTRONS') AS n_electrons,
  COALESCE(CAST(n_muons AS STRING), 'ALL_MUONS') AS n_muons,
  COUNT(*) AS event_count,
  ROUND(AVG(met_pt), 2) AS mean_met_pt,
  ROUND(AVG(ht_jets), 2) AS mean_ht_jets,
  ROUND(AVG(sum_lepton_pt), 2) AS mean_sum_lepton_pt
FROM events
GROUP BY n_electrons, n_muons WITH ROLLUP
ORDER BY n_electrons ASC, n_muons ASC;
