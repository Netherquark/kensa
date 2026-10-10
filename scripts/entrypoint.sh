#!/usr/bin/env bash
set -euo pipefail

# Ensure non-root UID has a valid passwd entry for JVM Hadoop user resolution
if ! whoami >/dev/null 2>&1; then
  if [[ -w /etc/passwd ]]; then
    echo "app:x:$(id -u):$(id -g):app:/tmp:/bin/bash" >> /etc/passwd
  fi
fi

cmd="${1:-help}"
if [[ $# -gt 0 ]]; then shift; fi
case "$cmd" in
  help) cat <<'HELP'
40 MHz CA3 project commands:
  download   fetch complete official Zenodo training HDF5 and verify MD5 + size
  audit      scan every event in HDF5; write data-quality JSON/CSV and schema report
  etl        transform all events to event-level Parquet + exact histograms
  spark      run Spark SQL reports and full-corpus map/reduce aggregation
  plots      generate salient Matplotlib visuals from computed outputs
  ml         optional full-corpus streaming MiniBatchKMeans descriptive score
  all        download -> audit -> ETL -> Spark -> plots
  test       run unit tests on tiny synthetic fixtures (not research data)
  pig-export export all event rows to TSV for optional Pig local-mode demonstration
HELP
    ;;
  download) python /workspace/scripts/fetch_dataset.py "$@" ;;
  audit) python /workspace/scripts/audit_hdf5.py "$@" ;;
  etl) python /workspace/scripts/extract_features.py "$@" ;;
  spark) /usr/local/bin/spark-submit --master 'local[6]' --driver-memory "${SPARK_DRIVER_MEMORY:-6g}" --conf "spark.sql.shuffle.partitions=${SPARK_SHUFFLE_PARTITIONS:-12}" --conf spark.driver.maxResultSize=1g /workspace/scripts/spark_analysis.py "$@" ;;
  plots) python /workspace/scripts/make_visuals.py "$@" ;;
  ml) python /workspace/scripts/stream_cluster.py "$@" ;;
  all)
    python /workspace/scripts/fetch_dataset.py
    python /workspace/scripts/audit_hdf5.py
    python /workspace/scripts/extract_features.py
    /usr/local/bin/spark-submit --master 'local[6]' --driver-memory "${SPARK_DRIVER_MEMORY:-6g}" --conf "spark.sql.shuffle.partitions=${SPARK_SHUFFLE_PARTITIONS:-12}" --conf spark.driver.maxResultSize=1g /workspace/scripts/spark_analysis.py
    python /workspace/scripts/make_visuals.py
    ;;
  test) python -m unittest discover -s /workspace/tests -v ;;
  pig-export) python /workspace/scripts/export_pig_tsv.py "$@" ;;
  *) exec "$cmd" "$@" ;;
esac
