-- Event-level electron, muon, and jet multiplicity distributions.
SELECT 'electron' AS object_type, n_electrons AS multiplicity, COUNT(*) AS event_count
FROM events GROUP BY n_electrons
UNION ALL
SELECT 'muon' AS object_type, n_muons AS multiplicity, COUNT(*) AS event_count
FROM events GROUP BY n_muons
UNION ALL
SELECT 'jet' AS object_type, n_jets AS multiplicity, COUNT(*) AS event_count
FROM events GROUP BY n_jets;
