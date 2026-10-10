# Install and run on Linux

## 1. Host checks

```bash
docker --version
docker compose version
id -u
id -g
df -h .
free -h
```

Ensure Docker Engine and Compose v2 are active. Reserve at least 5 GB free disk. The primary service is capped at 10 GB memory; Spark driver defaults to 6 GB.

## 2. Ownership setup

Copy `.env.example` to `.env`, then set `HOST_UID` and `HOST_GID` to the output of `id -u` and `id -g`. Keep `SPARK_DRIVER_MEMORY=6g`, `SPARK_SHUFFLE_PARTITIONS=12`, `ETL_CHUNK_ROWS=25000` for the initial run. Tuning can follow from measured runtime and memory.

## 3. Build and test

```bash
make build
make test
```

Unit tests build miniature synthetic files, verify tensor parsing, inject invalid particle type / negative pT / bad padding cases, and check quality counters. Test success validates software paths only.

## 4. Run full project

```bash
make all
```

The downloader calls Zenodo's record API. The script uses file key + published MD5, streams bytes to a temporary `.part`, validates MD5 and API byte count, then atomically renames the file. A failed transfer leaves no accepted HDF5 file.

The audit scans `Particles` in `chunk_rows` intervals. ETL scans the full tensor a second time and writes row groups to Parquet. Spark counts every Parquet row, creates a partitioned copy, checks count parity, executes query files, and performs one key-value aggregation. Plot code verifies input-row count against the audit before rendering.

## 5. If Zenodo cannot resolve

Network DNS may block `zenodo.org`. Download `background_for_training.h5` from the record page using a browser or approved network. Save file at `data/raw/background_for_training.h5`, then run stages individually:

```bash
make audit
make etl
make spark
make plots
```

`audit/raw_audit.json` contains actual local MD5/SHA-256. Confirm MD5 `08cb4801229f9d480567f8d3f5cac134` before interpreting outputs.

## 6. Optional ML stage

```bash
make ml
make plots
```

MiniBatchKMeans uses a streaming three-pass implementation: scaling fit, cluster updates, complete-event scoring. Every source row appears in each pass. Result is nearest-centroid distance in standardized feature space, not a posterior probability or discovery score.

## 7. Optional Pig Latin stage

```bash
make pig-build
make pig-export
make pig-run
```

Pig runs in a separate Java 8 image using local mode. `outputs/pig/events.tsv` contains five analytical fields for every source event. `outputs/pig/pig_jet_summary/` contains Pig's grouped aggregation. Legacy image build requires access to Apache archive and container registries.

## 8. Native Hive

`hive/register_events.hql` assumes the shared mount resolves to `/workspace/outputs/spark/events_by_n_jets`. Run it in a Hive environment with access to that path. It registers the Parquet partitions, then the SQL suite can be executed under database `ca3_40mhz`. Built-in Compose flow executes the suite on Spark SQL; this distinction must remain explicit in the report.

## 9. Reset generated products

```bash
make clean
```

This removes `outputs/*`, `data/processed/*`, `audit/*`. It leaves `data/raw/background_for_training.h5` intact. To reclaim the source file too, delete it manually after preserving any needed evidence and checksum manifest.
