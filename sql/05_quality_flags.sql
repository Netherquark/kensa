-- Audit-derived event flags retained during feature extraction.
SELECT
  has_nonfinite,
  invalid_type_count,
  negative_pt_count,
  inconsistent_padding_count,
  COUNT(*) AS event_count
FROM events
GROUP BY has_nonfinite, invalid_type_count, negative_pt_count, inconsistent_padding_count
ORDER BY event_count DESC;
