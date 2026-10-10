-- Input: full-row TSV projection produced by `make pig-export`.
-- This script reads all event rows. Local mode demonstrates Pig Latin semantics.
events = LOAD '$DATA' USING PigStorage('\t') AS (
    event_row_id:long,
    n_jets:int,
    met_pt:float,
    ht_jets:float,
    sum_lepton_pt:float
);

by_jet_multiplicity = GROUP events BY n_jets;
jet_summary = FOREACH by_jet_multiplicity GENERATE
    group AS n_jets,
    COUNT(events) AS event_count,
    AVG(events.ht_jets) AS mean_ht_jets,
    AVG(events.met_pt) AS mean_met_pt,
    AVG(events.sum_lepton_pt) AS mean_sum_lepton_pt;
ordered = ORDER jet_summary BY n_jets ASC;
STORE ordered INTO '$OUT' USING PigStorage('\t');
