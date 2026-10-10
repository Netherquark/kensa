-- HiveQL / Spark SQL Window Functions & Top-K Jet Ranking
-- Calculates rank of hardest event per jet multiplicity slice and running cumulative fractions
WITH ranked_events AS (
  SELECT
    event_row_id,
    n_jets,
    ht_jets,
    met_pt,
    sum_lepton_pt,
    DENSE_RANK() OVER (PARTITION BY n_jets ORDER BY ht_jets DESC) AS ht_rank_in_slice,
    ROW_NUMBER() OVER (ORDER BY ht_jets DESC) AS global_ht_rank
  FROM events
  WHERE n_jets > 0
)
SELECT
  event_row_id,
  n_jets,
  ROUND(ht_jets, 2) AS ht_jets_gev,
  ROUND(met_pt, 2) AS met_pt_gev,
  ROUND(sum_lepton_pt, 2) AS sum_lepton_pt_gev,
  ht_rank_in_slice,
  global_ht_rank
FROM ranked_events
WHERE ht_rank_in_slice <= 3
ORDER BY n_jets ASC, ht_rank_in_slice ASC;
