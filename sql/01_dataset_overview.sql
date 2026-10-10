-- One-row corpus profile. All four million source events should appear after ETL.
SELECT
  COUNT(*) AS event_count,
  SUM(CASE WHEN has_nonfinite THEN 1 ELSE 0 END) AS events_with_nonfinite,
  SUM(CASE WHEN invalid_type_count > 0 THEN 1 ELSE 0 END) AS events_with_invalid_type,
  SUM(CASE WHEN negative_pt_count > 0 THEN 1 ELSE 0 END) AS events_with_negative_pt,
  AVG(met_pt) AS mean_met_pt,
  percentile_approx(met_pt, 0.50, 10000) AS median_approx_met_pt,
  percentile_approx(met_pt, 0.95, 10000) AS p95_approx_met_pt,
  AVG(ht_jets) AS mean_ht_jets,
  percentile_approx(ht_jets, 0.95, 10000) AS p95_approx_ht_jets,
  AVG(n_jets) AS mean_jet_multiplicity
FROM events;
