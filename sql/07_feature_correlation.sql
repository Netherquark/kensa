-- Groupwise correlations expose dependence and sample composition effects.
SELECT n_jets, COUNT(*) AS event_count,
       corr(ht_jets, met_pt) AS correlation_ht_met,
       corr(sum_lepton_pt, met_pt) AS correlation_lepton_sum_met,
       AVG(max_abs_eta) AS mean_max_abs_eta
FROM events
GROUP BY n_jets
ORDER BY n_jets;
