-- Two-dimensional binned density, computed from every event.
SELECT
  CAST(FLOOR(met_pt / 20.0) AS INT) AS met_bin_20_GeV,
  CAST(FLOOR(ht_jets / 50.0) AS INT) AS ht_bin_50_GeV,
  COUNT(*) AS event_count
FROM events
GROUP BY CAST(FLOOR(met_pt / 20.0) AS INT), CAST(FLOOR(ht_jets / 50.0) AS INT)
ORDER BY met_bin_20_GeV, ht_bin_50_GeV;
