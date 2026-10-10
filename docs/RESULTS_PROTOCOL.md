# Final-results protocol

Use this checklist after `make all` on Linux. Values are computed from the file on disk. Source-paper values are tagged separately from new local measurements.

1. Check `data/raw/verified_manifest.json`: `status` starts with `downloaded` or `existing`; `md5` equals `expected_md5`; bytes match Zenodo API.
2. Check `audit/raw_audit.json`: `scan.rows_read == 4000000` and `event_rows_skipped == 0`.
3. Review `schema.Particles_shape`, dtype, key inventory, `Particles_Names`, `Particles_Classes`.
4. Review every field in `quality`. Nonzero NaN / infinity, invalid type, negative pT, unexpected slot, bad padding or phi-range counts require interpretation and possibly code review.
5. Check `data/processed/etl_manifest.json`: input, output rows equal; filtered / sampled / dropped all zero.
6. Check `outputs/spark/spark_manifest.json`: input rows = partition output rows = RDD aggregate event sum. Read `sql_results` CSV parts; record relevant values in the final report.
7. Check visual manifest reports the same event count. Inspect axis labels, tails, empty bins and quality flags.
8. If ML runs, verify `rows_scaled == rows_used_for_cluster_updates == rows_scored`. Report chosen feature list, cluster count, seed and score definition.
9. Record command, wall time, container settings, host CPU/RAM, actual peak memory if measured, output storage size.
10. Draw conclusions from actual generated values. Avoid claims of signal sensitivity, discovery, F1/AUC or real-time 40 MHz inference from this training record.
