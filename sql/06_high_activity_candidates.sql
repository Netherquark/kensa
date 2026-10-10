-- Descriptive review queue only; ranking is not a new-physics claim.
SELECT event_row_id, n_electrons, n_muons, n_jets, met_pt, ht_jets,
       leading_electron_pt, leading_muon_pt, leading_jet_pt, max_abs_eta,
       has_nonfinite, invalid_type_count, negative_pt_count
FROM events
ORDER BY ht_jets DESC
LIMIT 100;
