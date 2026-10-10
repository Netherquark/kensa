# CA3: Big Data Analytics on CERN's 40 MHz LHC Event Dataset

Runnable, Dockerised BDA project for Linux. Processes the complete **646.4 MB Standard Model training HDF5 file** from Zenodo. No event rows are sampled or removed. Dataset download is checksum-verified before analysis.

## Research objective

Build a reproducible event-data pipeline: HDF5 audit → event-level Parquet → Spark SQL → MapReduce-style aggregation → scientific plots. Optional MiniBatchKMeans scoring processes the full feature table in batches. Output scores describe distance in engineered feature space; they do not establish new physics.

### Source dataset

- Record: [Zenodo, Unsupervised New Physics detection at 40 MHz: Training Dataset](https://zenodo.org/records/5046428)
- Download name: `background_for_training.h5`
- Reported size: 646.4 MB
- Reported events: 4,000,000
- Published MD5: `08cb4801229f9d480567f8d3f5cac134`
- License: Creative Commons Attribution 4.0 International; retain dataset attribution.
- Dataset paper: Govorkova et al., *Scientific Data* 9, 118 (2022), [doi:10.1038/s41597-022-01187-8](https://doi.org/10.1038/s41597-022-01187-8)

This project uses the complete main training record. The four signal-benchmark records and separate black-box record belong to the wider challenge release; they are outside this single-file project scope.

## Requirements

- Linux x86-64 (or compatible Docker host)
- Docker Engine and Docker Compose v2
- 5 GB free disk for input, Parquet, logs and figures; additional room for optional Pig TSV export
- 32 GB RAM recommended for the configured 10 GB container limit; CPU mode uses up to 6 local Spark workers/threads
- Network access to `zenodo.org` for automated download

GPU is optional and unused by the standard pipeline. Radeon Vega 7 / `gfx90c` is not required. Docker image build also requires package-registry access.

## Quick start

```bash
# From this directory
cp .env.example .env
# Set host ownership IDs in .env to your Linux user if needed:
# HOST_UID=1000
# HOST_GID=1000

make build
make test
make all
```

If your Linux UID/GID are not 1000, set `HOST_UID` and `HOST_GID` in `.env` to the values from `id -u` and `id -g`. Docker output paths are bind-mounted into the project, so files remain available on the host.

Equivalent single command:

```bash
docker compose run --rm ca3 all
```

The `all` target executes these stages in order:

1. Fetch full Zenodo HDF5 record; verify API file inventory, full file size and MD5.
2. Scan every tensor row in chunks; write schema inventory and data-quality metrics.
3. Transform every event to a typed Parquet row; no sampling, row filtering or truncation.
4. Run Spark SQL query suite, persist Parquet partitions by jet multiplicity, run full-corpus RDD `map`/`reduceByKey` aggregation.
5. Produce research-oriented Matplotlib figures from the complete corpus and exact streamed counts.

### Individual stages

```bash
make download   # Internet needed
make audit      # Complete HDF5 scan
make etl        # Complete event-level Parquet transform
make spark      # Spark SQL + key/value aggregation
make plots      # Full-corpus plots
make ml          # Optional full-corpus MiniBatchKMeans + distance scores
make test        # Synthetic fixtures only; tests implementation, not physics results
```

All stages operate inside the project Docker image. `make ml` expects `make etl` first. `make plots` expects audit + ETL; after `make ml`, it adds two clustering-distance plots.

### Network-restricted environment

Use a browser or approved mirror to download the exact file listed on the Zenodo record page. Place it at `data/raw/background_for_training.h5`. Run `make audit`, `make etl`, `make spark`, and `make plots`. The audit logs actual MD5/SHA-256; compare MD5 with the published checksum above before trusting results. The automated `make download` path itself uses Zenodo API metadata and rejects checksum/size mismatches.

## Outputs

| Path | Meaning |
|---|---|
| `data/raw/background_for_training.h5` | Original complete HDF5 source, unchanged |
| `data/raw/verified_manifest.json` | Zenodo metadata, bytes, checksum and scope |
| `audit/raw_audit.json` | Full-file schema, exact validity counts, type occupancy, padding and multiplicity distributions |
| `audit/hdf5_inventory.csv` | Dataset keys, dimensions, data types, compression and attributes |
| `audit/quality_metrics.csv` | Compact quality metrics |
| `data/processed/events.parquet` | One engineered feature row per input event |
| `data/processed/etl_manifest.json` | Row-preservation proof, schema and feature definitions |
| `outputs/spark/events_by_n_jets/` | Parquet partitioned by `n_jets` |
| `outputs/spark/sql_results/` | CSV result folders for seven query groups |
| `outputs/spark/mapreduce_jet_multiplicity.json` | Full-corpus `map`/`reduceByKey` summary |
| `outputs/spark/spark_manifest.json` | Spark version, input/output counts, query files and elapsed time |
| `outputs/figures/` | Seven data-derived figures; nine when optional ML outputs exist |
| `outputs/ml/cluster_scores.parquet` | Optional cluster id and nearest-centroid distance for every event |

Spark CSV results are directories containing part files. Read them as folders or concatenate `part-*.csv`; keep the manifest alongside any copied report table.

## Quality guarantees implemented

- Download stage rejects partial files, incorrect checksums and API size mismatches.
- HDF5 audit streams all `Particles` rows in fixed-size chunks.
- ETL verifies the documented `(N, 19, 4)` structure and required metadata; unexpected schemas fail fast.
- Event row ordinal is explicitly named `event_row_id`; it is not represented as a detector event identifier.
- ETL manifest checks `input_rows_read == output_rows_written`.
- Spark checks count parity before and after partitioned Parquet output.
- RDD aggregation checks that grouped event counts sum to the complete input count.
- ML scores retain one row per event; manifests state no pipeline-level row sampling.
- Unit tests inject deliberate corruptions into a tiny synthetic HDF5 fixture. Synthetic test values never enter research outputs.

## Big Data technology mapping

- **Hadoop / MapReduce:** Spark RDD `map` / `reduceByKey` runs in the core path. `hadoop/mapper.py` and `hadoop/reducer.py` implement a genuine Hadoop Streaming job for an existing HDFS cluster; `hadoop/README.md` gives the command. The default Compose stack is single-node Spark, without Namenode/DataNode services.
- **HiveQL:** seven SQL files use Spark SQL functions and HiveQL-compatible syntax. `hive/register_events.hql` creates an external Hive table over the partitioned Parquet output for an existing Hive installation; default Compose service does not claim a separate HiveServer2 runtime.
- **Pig Latin:** `pig/analyze_events.pig` runs a real group/aggregate dataflow in Pig local mode. Optional image uses legacy Apache Pig 0.17 / Java 8; enable only for the course demonstration. The TSV projection retains every event row.
- **Spark:** Parquet, partitioning, predicate/aggregate queries, RDD key-value reduction.
- **ML:** optional streaming StandardScaler + MiniBatchKMeans. Distances are descriptive; no labelled signal benchmark is present in the main training file. This satisfies an intelligent-technique demonstration, but it is scikit-learn rather than a literal Apache Mahout job; the report states this CO5 caveat explicitly.
- **Visual analytics:** exact event multiplicity, pT histograms, MET vs jet HT, HT by jet count, data-quality counters and feature correlations.

## Pig demonstration

Optional and separate from the core path because Apache Pig 0.17 is legacy software:

```bash
make pig-build
make pig-export  # all event rows, five-column projection
make pig-run
```

The Pig image uses Java 8 for compatibility and runs `pig -x local`. This demonstrates Pig Latin semantics on the full TSV projection; it does not claim a distributed Hadoop Pig cluster. The primary validated application runs on Python 3.11 / Java 17 / Spark 3.5.7.

## Hive demonstration

After `make all`, run `hive/register_events.hql` in an existing Hive installation that can read `/workspace/outputs/spark/events_by_n_jets`. The HQL registers a partitioned external Parquet table. Then execute files in `sql/` after selecting database `ca3_40mhz`. For query execution in the supplied Docker stack, `make spark` runs those same statements through Spark SQL and records each result.

## Scientific cautions

The corpus contains simulated 13 TeV proton-proton collision events with an electron/muon selection. The file is finite offline data for developing a 40 MHz real-time trigger use case. Type code zero denotes structural padding. The main training file does not expose per-event truth labels for every hidden process, so supervised precision/recall/F1/AUC and signal-detection claims are unsupported. The published process mixture fractions are contextual paper-level proportions, not values reconstructed from hidden labels in this file.

An unusual score may result from a rare Standard Model topology, reconstruction behaviour, selection effects, schema quality or feature scaling. Physics interpretation requires expert review and a labelled validation sample.

## Reproducibility and citations

See `docs/INSTALL_LINUX.md`, `docs/DATA_DICTIONARY.md`, `docs/ARCHITECTURE.md`, `docs/VIVA_NOTES.md`, and `docs/CA3_REPORT_DRAFT_ULTRA.md`. The CA3 draft is checked by `quality/guardrail27_check.py`; its machine-readable metrics and check outcomes are stored in `quality/guardrail27.json`. The checker measures explicit lexical, structural and formatting proxies, plus records separate editorial review items. No automated metric proves scientific truth or subjective writing quality.
