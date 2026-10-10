# Execution architecture and design decisions

## Components

1. `fetch_dataset.py`: Zenodo API metadata + complete download + integrity gate.
2. `audit_hdf5.py`: streaming raw schema inspection and exact quality counters.
3. `extract_features.py`: row-preserving event feature projection to Arrow/Parquet row groups.
4. `spark_analysis.py`: partition write, read-back row count assertion, SQL suite, RDD map/reduce.
5. `make_visuals.py`: full-source pT histograms, event multiplicity and complete event-table graphics.
6. `stream_cluster.py`: optional three-pass full-corpus scaling, MiniBatchKMeans updates, complete event scores.
7. `export_pig_tsv.py`: complete row projection for Pig Latin group aggregation.

## Data contracts

- Raw record checksum must equal the source-listed MD5. SHA-256 is recorded for traceability.
- Required HDF5 keys: `Particles`, `Particles_Names`, `Particles_Classes`.
- Required tensor tail shape: `(19, 4)`. Unexpected schema aborts before transformation.
- One output row per raw event. `event_row_id` is source row ordinal.
- ETL contract: input event count = output event count; zero filtered / sampled rows.
- Spark contract: input Parquet count = partitioned Parquet count = sum of RDD key counts.
- Clustering contract: scaler rows = cluster update rows = score rows = ETL rows.

## Resource plan

The raw audit reads 25,000 events per HDF5 chunk by default. Given 19 × 4 values/event, one float32 chunk occupies roughly 7.6 MB of raw numeric payload; overhead, NumPy boolean masks and temporary arrays raise the actual working set. Feature rows are emitted as Parquet row groups. Spark driver heap defaults to 6 GB inside a 10 GB container limit. Six local workers/threads match the Ryzen 5 5650U's six CPU cores; no GPU acceleration is assumed.

## Failure behaviour

- Dataset absent: stop with download instructions.
- Zenodo API mismatch: reject file.
- MD5 mismatch or transfer interruption: temporary file removed; partial dataset never accepted.
- Required HDF5 key or shape mismatch: fail fast.
- Parquet row count mismatch: fail the ETL stage.
- Spark row-count mismatch at partition or MapReduce phase: fail the Spark stage.
- Optional ML row mismatch: fail scoring stage.
- Nonfinite or invalid values: preserved as audit signals, counted per event; feature arithmetic uses finite replacements where necessary and stores quality flags.

## Scientific boundaries

The dataset is simulated, selected and finite. The project targets BDA processing of a 4M-event record on one host. Wall-clock throughput here cannot substantiate Level-1 trigger latency. The main record lacks public event-level hidden-signal truth, so the model output is an exploratory ranking, not a measured signal-detection result.
