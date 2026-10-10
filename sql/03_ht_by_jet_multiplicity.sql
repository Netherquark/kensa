-- Does scalar jet activity rise with reconstructed jet count?
SELECT
  n_jets,
  COUNT(*) AS event_count,
  AVG(ht_jets) AS mean_ht_jets,
  percentile_approx(ht_jets, 0.25, 10000) AS p25_ht_jets,
  percentile_approx(ht_jets, 0.50, 10000) AS median_ht_jets,
  percentile_approx(ht_jets, 0.75, 10000) AS p75_ht_jets,
  AVG(met_pt) AS mean_met_pt,
  corr(ht_jets, met_pt) AS ht_met_pearson_r
FROM events
GROUP BY n_jets
ORDER BY n_jets;
