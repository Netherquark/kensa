# CA3 BDA LHC 40MHz Project Knowledge Base

## System & Provenance
- Source: Zenodo record 5046428 (`background_for_training.h5`).
- Size: 646,391,984 bytes (646.392 MB).
- Hashes: MD5 `08cb4801229f9d480567f8d3f5cac134`, SHA-256 `5f460bd3af441d98a7962a83f3964d9b5fea7f2163e35532066adc9a9696cfe5`.
- Rows: 13,451,915 collisions (100% full scan, 0 dropped/sampled).
- Raw Tensor: `/Particles` (13451915, 19, 4), float64, gzip chunked.
- Particle Slots (19): Slot 0=MET, Slots 1-4=e-, Slots 5-8=mu, Slots 9-18=jets.
- Type Codes: 0=padding, 1=MET, 2=electron, 3=muon, 4=jet.

## Data Quality Gate (1.022B Scalars Scanned)
- Non-finite (NaN / Inf): 0 (0.00%).
- Invalid Types: 0 (0.00%).
- Negative pT: 0 (0.00%).
- Out-of-bounds phi: 0 (0.00%).
- Structural Padding: 211,710,120 slots (82.83% of tensor).

## Feature Engineering & Columnar Storage
- Target: Snappy Parquet (`events.parquet`, 624.782 MB, 539 row groups).
- Features Derived:
  - Multiplicities: $N_e = \sum \mathbf{1}(t=2)$, $N_\mu = \sum \mathbf{1}(t=3)$, $N_j = \sum \mathbf{1}(t=4)$.
  - Scalar Activity: $H_T = \sum_{j} p_T$, $S_T = \sum_{e,\mu} p_T$, $\text{MET} = p_{T,0}$.
  - Kinematic Hardness: Leading $p_T$ for $e,\mu,j$, $|\eta|_{\max}$.
  - Flags: `has_nonfinite`, `invalid_type_count`, `negative_pt_count`, `inconsistent_padding_count`.

## Distributed Execution & Big Data Tools
- Docker Compose: Linux sandbox, host UID/GID mapped, `HOME=/tmp` Ivy isolated.
- Spark 3.5.7: `local[6]`, 6GB driver, 12 shuffle partitions.
- Spark SQL: 9 query suites:
  1. Corpus Overview (mean MET 35.32 GeV, mean HT 51.33 GeV).
  2. Multiplicity distributions.
  3. Conditional HT by $N_j$ (mean HT: 0 GeV at $N_j=0 \to 739.60$ GeV at $N_j=10$).
  4. MET-HT 2D density bins (943 occupied bins).
  5. Data Quality confirmation (13.45M valid rows).
  6. High-activity top-100 inspection candidates.
  7. Feature correlation matrix ($r(H_T, \text{MET}) = 0.059 \to 0.364$).
  8. Window functions: `DENSE_RANK() OVER (PARTITION BY n_jets)` & `ROW_NUMBER()`.
  9. Multidimensional aggregations: `GROUP BY n_electrons, n_muons WITH ROLLUP`.
- Spark RDD MapReduce: Key=jet multiplicity, Mapper emit `(n_jets, (1, ht, met, st))`, Reducer `reduceByKey(sum)`.
- Partitioning: `events_by_n_jets` snappy partitioned parquet.
- Hadoop Streaming: `hadoop/mapper.py` + `hadoop/reducer.py` standalone TSV pipeline.
- Apache Pig: `pig/analyze_events.pig` grouped local mode.
- Hive DDL: `hive/register_events.hql` external table schema.

## Machine Learning & Anomaly Scoring (CO5)
- Model: `MiniBatchKMeans` (8 clusters, 539 iterations, random_state=27).
- Preprocessing: `StandardScaler` partial fit on 10 standardized features.
- Metric: Standardized Euclidean distance to nearest centroid.
- Statistics: Mean score 1.648, Std 0.946, Max 336.841.
- Caveat: Feature-space atypicality marker; no supervised signal detection claim without hidden truth labels.

## Visual Manifest (9 Vector Graphics)
1. `01_pt_spectrum_by_object_type.png`: symlog pT distributions.
2. `02_event_multiplicity.png`: e-, mu, jet occupancy.
3. `03_met_vs_jet_ht_density.png`: log-density MET vs HT.
4. `04_ht_by_jet_multiplicity.png`: conditional quartiles.
5. `05_data_quality_flags.png`: audit verification.
6. `06_feature_correlations.png`: Pearson correlation matrix.
7. `07_full_corpus_ht_distribution.png`: signed log1p HT tail.
8. `08_cluster_distance_distribution.png`: novelty score histogram.
9. `09_cluster_distance_by_jet_multiplicity.png`: score boxplot by $N_j$.
