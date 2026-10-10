# CA3 Knowledge Base: 40 MHz LHC Event Quality, Feature Analytics, and Exploratory Outlier Ranking

**Purpose:** technical reference for revising the CA3 report and auditing the accompanying Docker project. This document supplies physics context, dataset semantics, mathematical definitions, empirical methods, Big Data technology roles, visual-analytics requirements, report structure, and source links. It is not a substitute for executing the pipeline and collecting local manifests.

**Primary sources:** the peer-reviewed dataset paper, its Zenodo record, the dataset authors' ADC2021 materials, and official Apache / h5py / Arrow / scikit-learn documentation. Claims based on these sources are distinguished from implementation recommendations.

---

## 0. Priority-zero factual correction

The current report PDF and pasted LaTeX draft contain a material conflict with the published dataset specification and the repository README.

| Item | Published/source-grounded expectation | Current PDF claim | Required action |
|---|---:|---:|---|
| Training events | **4,000,000** | 13,451,915 | Re-read actual local HDF5 shape. Use verified file metadata as final authority. |
| Tensor shape | `(N, 19, 4)`; expected training `N = 4,000,000` | `(13,451,915, 19, 4)` | Report only `Particles.shape` from the checksum-verified downloaded file. |
| Scalar tensor entries | `4,000,000 × 19 × 4 = 304,000,000` | 1,022,345,540 | Recompute from verified dimensions. |
| Float64 tensor payload if `dtype=float64` | `304,000,000 × 8 = 2,432,000,000` bytes before HDF5 compression | Shape/payload inconsistent with training sample | Inspect actual dtype; state the equation conditionally. |
| Parquet row groups | At 25,000 rows per write, `ceil(4,000,000 / 25,000) = 160`, if one written row group per input chunk | 539 | Verify Parquet metadata; do not retain 539 unless local output proves it. |
| Derived summary tables, correlations, quality counts | Must be generated from verified event rows | Report presents exact results based on 13.45M rows | **Invalidate and recompute all such results.** |

Zenodo's record for `background_for_training.h5` reports 646.4 MB and MD5 `08cb4801229f9d480567f8d3f5cac134`. The dataset paper states that the Standard Model cocktail contains 8,209,492 events overall, of which **4 million define the training dataset**; other events are used in the challenge's black-box mixture. Sources: [Zenodo record 5046428](https://zenodo.org/records/5046428), [Govorkova et al., *Scientific Data* (2022), dataset article](https://www.nature.com/articles/s41597-022-01187-8), especially its Data Records section.

The figure `13,451,915` is not a rounding discrepancy. All reported row-dependent results derived under that count, including percentages, padding totals, means, maxima, correlations, ML score distribution, visualisations, runtime throughputs, and row-group counts, require fresh generation from the exact file. Do not “correct” table totals algebraically while leaving plots or manifests stale. Search the entire repository and report source for every occurrence.

**Precondition for scientific prose:** successful source download or an independently supplied file, matching byte size and source checksum, HDF5 inventory, and `Particles.shape[0]` recorded in an immutable run manifest. If execution cannot be completed, mark numerical results *pending execution*; do not invent, extrapolate or recycle them.

---

## 1. Research question, scope, and defensible claims

### 1.1 Core research question

Can a reproducible, bounded-memory data pipeline validate the structure of the complete 40 MHz training corpus, derive interpretable collision-event features, execute full-corpus aggregations and conditional queries, and rank unusual Standard Model events using unsupervised feature-space distances on a six-core CPU host?

### 1.2 Objectives

1. Verify provenance, exact size, checksum, file version, HDF5 keys, dimensions, dtype, metadata, and compression.
2. Audit every event without row sampling: numeric finiteness, type-code validity, slot/category consistency, angular range, non-negative transverse momentum for occupied objects, and padding semantics.
3. Convert every source row to one typed Parquet event row, retaining source-row ordinal and quality flags.
4. Use Spark SQL for corpus summaries, object multiplicities, conditional activity distributions, joint density bins, quality summaries, and correlation analysis.
5. Demonstrate key-value aggregation through Spark RDD `map` and `reduceByKey`, with an equivalent Hadoop Streaming mapper/reducer for a separately configured HDFS runtime.
6. Demonstrate HiveQL concepts accurately through Spark SQL compatibility plus an external Hive-table DDL artifact; demonstrate Pig Latin through its optional local-mode job.
7. Optionally rank feature-space outliers using standardisation and MiniBatchKMeans. Treat the scores as exploratory distances, not probabilities of new physics.
8. Create data-derived plots that answer explicit research questions, with every numeric plot generated from versioned output manifests.

### 1.3 Scope boundary

The dataset is a **finite simulated offline corpus** designed to emulate a low-level trigger event representation. “40 MHz” describes the real-time use case and bunch-crossing interval. A local Docker run over the released file is not a live stream, a 40 MHz benchmark, a multi-node cluster demonstration, or proof of microsecond inference latency. The study must not claim any of those capabilities without a separately designed experiment.

This main training record is a Standard Model mixture without public per-event secret-signal ground truth. Therefore, the project can study event properties, data integrity, unusual Standard Model topologies, and feature-space outlier rankings. It cannot compute supervised signal efficiency, precision, recall, F1, ROC-AUC, or discovery significance from this record alone.

---

## 2. Dataset provenance and exact data contract

### 2.1 Authoritative provenance

- **Dataset record:** [Zenodo 5046428](https://zenodo.org/records/5046428)
- **File:** `background_for_training.h5`
- **Reported download size:** 646.4 MB on the record page
- **Published MD5:** `08cb4801229f9d480567f8d3f5cac134`
- **License shown by record:** Creative Commons Attribution 4.0 International. Preserve attribution and source DOI.
- **Dataset paper:** E. Govorkova et al., “LHC physics dataset for unsupervised New Physics detection at 40 MHz,” *Scientific Data* 9, 118 (2022), [DOI 10.1038/s41597-022-01187-8](https://doi.org/10.1038/s41597-022-01187-8).
- **Authors' challenge materials and example code:** [ADC2021](https://mpp-hep.github.io/ADC2021/) and [mpp-hep/ADC2021-examplecode](https://github.com/mpp-hep/ADC2021-examplecode).

Zenodo notes that the record contains several bug fixes in dataset definition. Record version and metadata should therefore be captured with the manifest. The file's actual shape, dtype and metadata remain runtime facts, even when a paper provides expected values.

### 2.2 HDF5 container

The dataset paper specifies three principal HDF5 datasets:

| Dataset key | Role | How to document it |
|---|---|---|
| `/Particles` | Main tensor of event objects and features | Record full shape, dtype, `nbytes`, chunks, compression, attributes. Expected shape: `(N, 19, 4)`. |
| `/Particles_Names` | Feature naming metadata | Print raw values, decoded strings, shape and dtype. Avoid assuming metadata order without inspecting file and paper. |
| `/Particles_Classes` | Object-class/type-code metadata | Print raw values, decoded strings, shape and dtype; map observed codes to documented classes. |

The final report's table must be produced from an actual `h5py` inventory, not manually typed before inspecting the file. Dataset metadata may have byte strings, NumPy scalar wrappers or arrays. Decode values explicitly, preserve original representations in JSON-safe form, and never use an inferred header as proof of the stored metadata.

### 2.3 Tensor axes

Let `Particles` have shape `(N, 19, 4)`:

- Axis 0: collision/event rows; published training sample expects `N = 4,000,000`.
- Axis 1: 19 fixed physics-object slots per event.
- Axis 2: four values per slot: three kinematic entries plus object-type code.

The published object-slot design is:

| Zero-based slot index | Slot purpose | Expected object code |
|---|---|---:|
| `0` | Missing transverse momentum / MET object | `1` |
| `1..4` | Up to four electrons, ordered by decreasing `pT` | `2` |
| `5..8` | Up to four muons, ordered by decreasing `pT` | `3` |
| `9..18` | Up to ten jets, ordered by decreasing `pT` | `4` |
| Any empty object slot in applicable regions | Structural zero padding | `0` |

Paper convention: classes 1–4 denote MET, electron, muon and jet; class 0 denotes padding. The fourth tensor component can be stored as floating point even though its semantic type is categorical. Validate that type values are finite, close to integers under a documented tolerance, and in `{0,1,2,3,4}` *before* integer conversion. A corrupted float must not silently round to a valid class.

### 2.4 Event volume arithmetic

With `N = 4,000,000`, 19 slots/event and 4 components/slot:

\[
N_{\text{slots}} = 4{,}000{,}000\times19 = 76{,}000{,}000
\]

\[
N_{\text{scalar}} = 4{,}000{,}000\times19\times4 = 304{,}000{,}000.
\]

Uncompressed numeric payload is:

\[
B_{\text{payload}} = N\times19\times4\times\text{dtype.itemsize}.
\]

If and only if observed dtype is 64-bit float, `B_payload = 2,432,000,000` bytes (~2.432 GB decimal, ~2.265 GiB), excluding container overhead. This is compatible with a smaller on-disk HDF5 file when compression and zero-padding patterns reduce stored bytes. Report separately: source file bytes, uncompressed dataset bytes (`ds.nbytes`), Parquet bytes, and estimated process memory.

For `chunk_rows = 25,000`, each chunk has at most `25,000 × 19 × 4 = 1,900,000` scalar values. Numeric payload is about 15.2 MB if dtype is float64 or 7.6 MB if float32, before temporary masks/arrays and Pandas/Arrow overhead. Chunked reading bounds memory usage; actual peak RSS must be measured if reported.

### 2.5 Published selection and simulation context

The paper describes simulated 13 TeV proton-proton interactions, generated with PYTHIA 8 and passed through DELPHES parametric detector simulation. The reported workflow uses a Phase-II CMS detector card and samples pile-up with a Poisson distribution centred at 20. Selected events require an electron or muon satisfying a high-level preselection; further selected objects are written into fixed slots.

Published selection details include:

- Event retained if at least one electron has `pT > 23 GeV` within `|eta| < 3`, or at least one muon has `pT > 23 GeV` within `|eta| < 2.1`.
- Included electrons: up to four with `pT > 3 GeV`, `|eta| < 3`.
- Included muons: up to four with `pT > 3 GeV`, `|eta| < 2.1`.
- Included jets: up to ten with `pT > 15 GeV`, `|eta| < 4`.
- MET is also represented.

Use these as **published selection definitions**, not as a result of re-executing the selection code. They explain why the available corpus is already filtered and why per-event distributions cannot be interpreted as unbiased inclusive LHC collision statistics.

The article describes Standard Model contributions including W production, QCD multijet production, Z production and top-quark pair production. If the report presents paper-reported mixture percentages, label them as paper-level sample composition and cite the paper. Do not derive per-event class counts from `Particles_Classes`: those are object types, not generator-process labels.

---

## 3. Physics prerequisites and mathematical foundations

This project needs operational understanding of collider variables and classical statistics. It does not require quantum-field-theory derivations. The physics terms below should be explained at a level that supports correct interpretation of plots and code.

### 3.1 Coordinate system and kinematic variables

The beam defines the longitudinal `z` axis. `x` and `y` span the plane transverse to the beam. A reconstructed object's momentum has components `(p_x, p_y, p_z)`.

**Transverse momentum** is

\[
p_T = \sqrt{p_x^2+p_y^2}.
\]

It measures momentum projected into the transverse plane and is expressed in GeV under natural-unit convention `c = 1`. It is non-negative. High-`pT` tails often carry useful information about energetic event topologies, but tail events can also be finite-sample extremes, reconstruction effects or rare Standard Model processes.

**Azimuth** `phi` is the angle of the transverse momentum around the beam direction, measured in radians within the publication's convention `[-pi, pi]`. Since it is circular, `-pi` and `+pi` are adjacent directions. Ordinary linear averages/correlations of `phi` may be misleading near the wrap boundary. For angular difference use wrapped `delta_phi = atan2(sin(phi1-phi2), cos(phi1-phi2))`; for a model, consider `sin(phi)` and `cos(phi)` when appropriate.

**Pseudorapidity** is

\[
\eta = -\ln\left[\tan\left(\frac{\theta}{2}\right)\right],
\]

where polar angle `theta` is measured relative to the positive beam axis. `eta` is dimensionless. Large `|eta|` corresponds to a direction closer to the beam. The paper uses eta acceptance ranges for electrons, muons and jets.

**MET / missing transverse momentum.** The event's missing transverse momentum vector is defined as the negative vector sum of reconstructed transverse momenta:

\[
\vec p_T^{\,\mathrm{miss}} = -\sum_{k\in\mathrm{reconstructed\ objects}}\vec p_{T,k}.
\]

Its magnitude is the missing transverse momentum, conventionally reported in GeV; the direction has its own azimuth. The report may use `met_pt` for its stored magnitude and `met_phi` for direction if confirmed against file metadata and implementation. MET has no ordinary object pseudorapidity. Never include the MET slot when calculating object `max_abs_eta`.

### 3.2 Fixed-width encoding and padding

Each event is padded to 19 slots so model input shape remains fixed. Type code `0` is the explicit padding indicator. **Padding is not an observed particle.** It must not contribute to multiplicity, spectra or physics sums. Do not infer padding solely from a zero pT because an occupied object may have a zero-valued coordinate in some feature positions; type metadata defines occupancy.

The final report should show both:

1. the count/fraction of code-zero padding slots, as an expected property of representation; and
2. counts of *inconsistent* padding slots whose coordinates conflict with the published convention, as a data-quality issue.

These statistics must be computed using the checksum-verified input file.

### 3.3 Event-level feature engineering

For event `e`, slot `i` has transverse momentum `pT_i` and type code `t_i`. Define indicator `1(condition)` as 1 when true and 0 otherwise.

Object multiplicities:

\[
N_e=\sum_{i=0}^{18}\mathbf 1(t_i=2),\quad
N_\mu=\sum_{i=0}^{18}\mathbf 1(t_i=3),\quad
N_j=\sum_{i=0}^{18}\mathbf 1(t_i=4).
\]

Total reconstructed lepton count and object count:

\[
N_\ell=N_e+N_\mu,\qquad N_{\mathrm{objects}}=N_e+N_\mu+N_j.
\]

Scalar hadronic activity from jets:

\[
H_T^{\mathrm{jets}}=\sum_{i=0}^{18}p_{T,i}\,\mathbf 1(t_i=4).
\]

Scalar lepton activity:

\[
S_T^{\mathrm{leptons}}=\sum_{i=0}^{18}p_{T,i}\,\mathbf 1(t_i\in\{2,3\}).
\]

Leading object pT by category:

\[
p_T^{e,\mathrm{lead}}=\max_{i:t_i=2}p_{T,i},\quad
p_T^{\mu,\mathrm{lead}}=\max_{i:t_i=3}p_{T,i},\quad
p_T^{j,\mathrm{lead}}=\max_{i:t_i=4}p_{T,i}.
\]

For events with no object of a category, the engineering convention may return `0`, provided the corresponding multiplicity remains available to distinguish “no object” from a measured zero. Maximum absolute pseudorapidity:

\[
|\eta|_{\max}=\max_{i:t_i\in\{2,3,4\}}|\eta_i|.
\]

Return 0 when no eligible slots exist and preserve occupancy features alongside it. Do not interpret missing/undefined values silently.

### 3.4 Data quality equations

For a chunk tensor `X`:

- `finite_mask = isfinite(X)`; count NaN, `+Inf`, `-Inf` independently.
- `known_type = finite_type AND near_integer(type) AND rounded_type in {0,1,2,3,4}`.
- `negative_pt = occupied AND pT < 0`.
- `phi_outside = occupied AND finite(phi) AND abs(phi) > pi + tolerance`.
- `bad_padding = (type == 0) AND any(kinematic coordinate != 0)` under the exact padding convention. Record raw values/examples for inspection.
- `slot_type_mismatch = occupied AND observed type != expected type for that fixed slot region`.
- `zero_padding_fraction = count(type == 0) / (N × 19)`.

Every counter is accumulated across chunks in 64-bit integer arithmetic. Event counts, slot counts, scalar counts and percentages must use their proper denominators. The quality gate should preserve bad rows for audit and explicitly mark their derived features. It must not hide corruption by coercing values to integer or dropping rows.

### 3.5 Summary statistics and association

For event feature `X`, report count, missing/non-finite count, mean, median, quartiles, 95th/99th percentiles, maximum, and optionally a trimmed/robust summary. Heavy right tails can make mean and maximum sensitive to a small number of events. Use medians and quantiles alongside means.

For numeric features `X` and `Y`, Pearson correlation is

\[
r_{XY}=\frac{\sum_i(X_i-\bar X)(Y_i-\bar Y)}
{\sqrt{\sum_i(X_i-\bar X)^2\sum_i(Y_i-\bar Y)^2}}.
\]

Interpret `r` as linear association. It does not establish a causal relationship or a physical mechanism. Compare correlations conditional on `N_j` because aggregate event classes can confound the full-corpus relationship. Consider Spearman rank correlation as a sensitivity check for non-linear monotone relationships or influential tails. Exclude event IDs, boolean quality fields and categorical codes from a continuous-feature correlation matrix unless the encoding and interpretation justify inclusion.

For binned joint densities, define fixed documented widths, e.g. MET bins of 20 GeV and `H_T` bins of 50 GeV only if those widths are useful over observed quantiles. Plot log-count density when counts span orders of magnitude. Include underflow/overflow accounting and label zeros. Avoid a scatter plot of millions of overplotted events as the primary presentation.

### 3.6 Unsupervised outlier score

The optional implementation uses `StandardScaler` followed by `MiniBatchKMeans`. For feature `x_j`, standardisation is

\[
z_{ij}=\frac{x_{ij}-\mu_j}{\sigma_j},
\]

where `mu_j` and `sigma_j` are fit on the corpus. StandardScaler uses a mean and standard deviation; its official documentation warns that it is sensitive to outliers. This sensitivity matters for heavy-tailed pT and `H_T` variables. Record feature list, scaler statistics, cluster count `K`, random seed, batch size, model settings and package version.

Given scaled vector `z_i` and centroid `c_k`, the nearest-centroid score is

\[
s_i=\min_{k\in\{1,\ldots,K\}}\|z_i-c_k\|_2.
\]

This is an **empirical feature-space distance**, not a calibrated probability, p-value, likelihood ratio, discovery significance, or indication of a new particle. The high-score tail can contain unusual Standard Model events, rare categories, detector-response effects, reconstruction artefacts, encoding errors or model failure.

Report the overall score distribution, empirical percentile thresholds, cluster sizes, score by jet multiplicity and relationships to `H_T` / MET. Investigate whether the ranking mostly reproduces high jet multiplicity or high `H_T`; if so, state that explicitly. Prefer a robustness study across seeds or `K` values before presenting the ranking as stable. No signal-detection efficiency can be calculated from the main background-only training file.

Source: [MiniBatchKMeans API](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html), [StandardScaler API](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).

---

## 4. Reproducible technical workflow

### 4.1 Provenance gate

`fetch_dataset.py` should query Zenodo's record API, select the named file, record record/version DOI, URL, byte count and server checksum, download to a temporary path, validate size and checksum, then atomically rename into `data/raw/`. A failed transfer must not leave a file that later steps interpret as complete. Compute SHA-256 for local provenance even if the source API's published digest is MD5. Do not state SHA-256 is “verified against Zenodo” unless the source publishes that exact digest.

Manifest fields: UTC timestamp, source record, version/DOI if available, filename, source URL, expected and actual bytes, expected and actual MD5, calculated SHA-256, status, script/package version, and any error. Preserve data license attribution.

### 4.2 HDF5 audit

Use `h5py.File(path, 'r')`. Capture HDF5 dataset inventory before scanning. Inspect `shape`, `dtype`, `chunks`, `compression`, `compression_opts`, `attrs`, raw small metadata values, and `ds.nbytes`. Stream every row through fixed-size slices such as `ds[start:stop]`; do not read all `Particles` into RAM. h5py documents that `shape`, `dtype`, `nbytes`, chunk shape and compression are explicit dataset properties, and chunk dimensions affect IO behaviour ([h5py dataset documentation](https://docs.h5py.org/en/stable/high/dataset.html)).

Audit outputs should separate:
- structural/schema facts,
- exact quality counters,
- multiplicity distributions,
- pT histogram counts and declared bin edges,
- exceptional coordinate examples,
- file integrity metadata,
- scan row count and chunk size.

The audit should fail for absent required keys, incompatible tensor tail dimensions, irreconcilable metadata, row count mismatch, incomplete scan, or checksum mismatch. It should not fail merely because a quality defect is detected; rather mark the data-quality status as warning/fail and permit controlled inspection, with downstream interpretation gated.

### 4.3 ETL to Parquet

Use one output row per original event. `event_row_id` is the zero-based source row ordinal and **not** an experiment-assigned physical event ID. Columnar projection reduces the 19×4 tensor to interpretable event summary features. Retain raw file untouched.

Expected current derived schema (must match actual source code or be updated in both code and docs):

| Column | Meaning | Notes |
|---|---|---|
| `event_row_id` | Source row ordinal | Unique sequence; never call this detector ID. |
| `met_pt`, `met_phi` | MET magnitude/direction fields | Validate against metadata; no MET eta calculation. |
| `n_electrons`, `n_muons`, `n_jets` | Counts by type code | Structural padding excluded. |
| `n_objects` | e + mu + jet count | Excludes MET slot. |
| `leading_electron_pt`, `leading_muon_pt`, `leading_jet_pt` | Maximum pT by type | Empty category maps to 0 and count disambiguates. |
| `ht_jets` | Sum jet pT | GeV. |
| `sum_lepton_pt` | Sum electron/muon pT | GeV. |
| `max_abs_eta` | Maximum |eta| over e, mu, jets | Excludes MET, 0 if no eligible object. |
| `has_nonfinite` | Any non-finite tensor value in event | Quality indicator. |
| `invalid_type_count` | Non-finite, non-integral or unknown type values | Define exactly in schema and report. |
| `negative_pt_count` | Occupied slots with pT < 0 | Quality indicator. |
| `inconsistent_padding_count` | Code-zero slots with nonzero kinematics | Quality indicator. |

Write a manifest with input row count, output row count, rows filtered/sampled/dropped (all must be 0), output bytes, row-group count, compression, schema, source hashes and feature definitions. Verify `ParquetFile.metadata.num_rows`, row groups, schema and field nullability/types after close and atomic rename. Use Snappy only if benchmark rationale exists; report file sizes and encode settings. PyArrow documents Parquet row groups, column metadata/statistics, compression choices and partitioned data sets ([Parquet documentation](https://arrow.apache.org/docs/python/parquet.html)).

Do not partition the raw tensor; the format is not inherently a SQL event table. The current project partitions the derived Parquet by `n_jets`, a low-cardinality column. This supports a teaching demonstration of partition directory layout and filters, but the report must not claim faster performance unless measured using equivalent queries with and without partitioning. Count number of files and records per partition; excessive small files can outweigh pruning benefits.

### 4.4 Spark SQL

Spark SQL provides structured queries and lets the engine optimize operations with schema information. It is the main analytical query interface in this repository ([Spark 3.5.7 SQL guide](https://spark.apache.org/docs/3.5.7/sql-programming-guide.html)). Clearly document each SQL statement, its input, output columns, interpretation, file path and manifest row counts.

Current repository has **seven SQL files / query groups**:
1. `01_dataset_overview.sql`: total rows and event-level quality counts; means, approximate median/P95 for MET and HT; mean jet multiplicity.
2. `02_object_multiplicity.sql`: event count by electron, muon and jet multiplicity.
3. `03_ht_by_jet_multiplicity.sql`: event count, mean/quartiles of HT, mean MET and Pearson HT–MET correlation by jet count.
4. `04_met_ht_density_bins.sql`: count of events in binned MET × HT plane.
5. `05_quality_flags.sql`: count of rows by quality flag/counter combination.
6. `06_high_activity_candidates.sql`: 100 events ranked by jet HT, as an inspection queue.
7. `07_feature_correlation.sql`: groupwise correlations and mean max-|eta| by jet count.

The current `spark_analysis.py` executes each SQL file via Spark SQL and writes results as output directories with CSV part files. It then writes the full corpus partitioned by `n_jets` and verifies row-count parity. The `ORDER BY ... LIMIT 100` query is a global top-N query; it is not a SQL window function. The current SQL files do **not** contain a `RANK() OVER (...)` query or a `ROLLUP` statement. If the report advertises window/rollup functions, the coding agent must either implement and execute useful queries plus tests, or remove those claims. Do not describe feature availability as implemented usage.

Useful genuine extension if implemented:
- Window query: rank `ht_jets` per `n_jets` using `DENSE_RANK() OVER (PARTITION BY n_jets ORDER BY ht_jets DESC)` and produce a small top-k table. State that rankings are descriptive.
- `ROLLUP` query: aggregate event counts/summary measures by jet multiplicity and total corpus, with explicit handling for the subtotal row (e.g. `GROUPING(n_jets)`). Only add it if the resulting table explains an analytical question. Official Spark references: [window functions](https://spark.apache.org/docs/3.5.7/sql-ref-syntax-qry-select-window.html), [GROUP BY, ROLLUP and CUBE](https://spark.apache.org/docs/3.5.7/sql-ref-syntax-qry-select-groupby.html).

`percentile_approx` is an approximate quantile algorithm. Label results as approximate and document accuracy parameters. Correlations computed in SQL are empirical associations, not causal findings.

### 4.5 MapReduce and Spark RDD

Canonical MapReduce flow: input splits → mapper emits intermediate `(key, value)` pairs → framework sorts/partitions intermediate records → reducer combines each key's values → output. The Hadoop documentation describes mappers, reducers, optional combiners, partitioners, input/output formats and task execution ([MapReduce Tutorial](https://hadoop.apache.org/docs/current/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)). Hadoop Streaming allows executable scripts to serve as mappers/reducers ([Streaming documentation](https://hadoop.apache.org/docs/current/hadoop-streaming/HadoopStreaming.html), if reachable in the chosen release).

Project key-value contract:

\[
\text{map}(e) = \left(N_{j,e},\;(1,H_{T,e},MET_e,S_{T,e})\right).
\]

For each jet-count key `j`, reducers add tuples componentwise:

\[
(n_j,\sum H_T,\sum MET,\sum S_T)=\sum_{e:N_{j,e}=j}(1,H_{T,e},MET_e,S_{T,e}).
\]

Then means equal sums divided by `n_j`. Integer counts should use exact integer accumulators; floating sums may have order-dependent roundoff in distributed reduction. Correctness checks: reduced counts sum to the full verified event row count; means recomputed from query results agree within an explicit tolerance.

In the project, `spark_analysis.py` uses RDD `.map(...).reduceByKey(...)` over all feature rows. This is **MapReduce-style programming in Spark**, not an actual Hadoop MapReduce cluster job. `hadoop/mapper.py` and `hadoop/reducer.py` separately implement Hadoop Streaming protocol on a five-column TSV projection; real Hadoop/HDFS execution requires an existing Hadoop environment and is outside the default Docker Compose path. State this distinction in text and diagram.

### 4.6 Hive

Hive supplies SQL data warehousing over filesystem-resident data. `hive/register_events.hql` in the repo is an external-table DDL artifact. Hive's external table points to existing file data; its metadata definition can allow a Hive installation to query Parquet without moving/copying raw data. Partitioned external table DDL must use the actual Parquet schema and a filesystem path visible to the Hive service ([Hive LanguageManual DDL](https://hive.apache.org/docs/latest/language/languagemanual-ddl/)).

Default project behavior: the core Compose path runs SQL statements through Spark SQL. It does **not** automatically run HiveServer2, create a Hive metastore or prove that the DDL succeeded on a Hive installation. The report must say “Hive-compatible query semantics / external Hive DDL for a configured Hive instance,” unless a real Hive service test is added and captured. Do not label Spark SQL output “Hive results.”

### 4.7 Pig Latin

The repository's `pig/analyze_events.pig` loads the TSV projection, groups rows by `n_jets`, and uses `COUNT`, `AVG`, `FOREACH ... GENERATE`, `ORDER`, and `STORE` to create one summary per group. This is a legitimate relational dataflow example for Pig Latin. Pig's `GROUP` groups a relation by a key; `FOREACH ... GENERATE` projects/aggregates the grouped bag. See [Apache Pig 0.17 Pig Latin Basics](https://pig.apache.org/docs/r0.17.0/basic.html) and [built-in aggregates](https://pig.apache.org/docs/r0.17.0/func.html).

The Docker project marks Pig 0.17 as optional and runs it in local mode in a compatibility image. Report it as such. If the command hasn't been run, label it “provided optional script” until executed. Local mode demonstrates syntax/semantics but does not demonstrate distributed Hadoop task execution. TSV export itself is a full-row, five-column projection; document it as an interface conversion, not a lossy subset of event rows.

### 4.8 MiniBatchKMeans and scaling

The ML script runs multiple bounded-memory passes:
1. `StandardScaler.partial_fit` across all batches to collect means and variances.
2. `MiniBatchKMeans.partial_fit` on standardized batches to update centroids.
3. Transform/predict and persist one `cluster_id` plus nearest-centroid distance per event.

Use the manifest to prove `rows_scaled = rows_used_for_cluster_updates = rows_scored = ETL row count`, no filtering, and stable event-row IDs. Report the actual feature list, K, batch size, seed, iterations/steps, cluster occupancy, score moments/quantiles, elapsed time and package versions. Scikit-learn warns StandardScaler is sensitive to outliers, and MiniBatchKMeans uses stochastic minibatch updates; describe those choices and limitations ([StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html), [MiniBatchKMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html)).

MiniBatchKMeans is scikit-learn, not Apache Mahout. If the CA3 rubric explicitly expects Mahout usage, state that this implementation demonstrates an intelligent-technique/ML workflow, with literal Mahout integration as a gap unless added and executed. Never claim CO5 is “fully demonstrated” solely from use of scikit-learn if the assessment wording requires Mahout.

---

## 5. Empirical study design: questions and valid interpretation

The report should organize findings around a small number of concrete questions. Avoid presenting every available metric without a hypothesis.

### Q1. Is data structurally fit for event-level analysis?

Evidence: checksum and byte count; HDF5 inventory; shape/dtype; full scalar count; type-code vocabulary; finite/nonfinite values; fixed-slot conformance; padding consistency; pT and phi range checks; complete row-preservation manifests. Report counts and rates with explicit denominators. A zero observed defect count means “zero detected in this file under these checks,” not universal data perfection.

### Q2. How do object counts distribute across events?

Evidence: marginal distributions for `n_electrons`, `n_muons`, `n_jets`; both count and fraction; logarithmic count axis or complementary cumulative distribution for rare high-multiplicity tails. The published event selection conditions the population; interpret event-level count proportions in that context.

### Q3. How does hadronic activity change with jet multiplicity?

Evidence: median and interquartile range of `ht_jets` conditional on `n_jets`, plus event counts for each group. A mean-only trend can be dominated by upper-tail events. If plotting means, show uncertainty or quantile bands and identify small groups. Since `H_T` is a sum over jets, a positive trend with jet count is mathematically expected to some extent; the useful question is the magnitude, spread, departures and high-activity tail.

### Q4. What relation exists between MET and jet HT?

Evidence: a hexbin / 2D histogram with log-count color scale, plus marginal distributions and median conditional curve. Compute Pearson `r` globally and per jet multiplicity; optional Spearman sensitivity. Discuss selection/correlation and possible topology, without asserting causality. Preserve visible zero-jet / zero-HT populations.

### Q5. Does the corpus exhibit an interpretable upper tail?

Evidence: empirical ECDF or complementary CDF of `H_T`, leading pT and centroid distance; annotate 95th, 99th and 99.9th percentiles only if calculated. Include top event rows with supporting kinematic columns and quality indicators. An extreme HT candidate is a high-activity event, not automatically an anomaly or new-physics candidate.

### Q6. Does the optional model identify novelty beyond a simple high-HT ranking?

Evidence: centroid-distance distribution with percentile cut lines; score by `n_jets`; score versus `ht_jets` density; top events table with features; seed/K sensitivity. If scores closely track `n_jets` or HT, disclose the dependence and consider a conditional comparison within `n_jets` strata. Without labels, report ranking characteristics and stability, not classification quality.

### Q7. What BDA workload was actually executed?

Evidence: stage elapsed time and throughput from manifests; event rows/s; ETL output bytes; Parquet row-group count; partition count and file-size distribution; SQL query runtimes; memory only if measured; container CPU/memory settings. Repeated timings should include warm/cold-cache context and multiple runs if making relative performance claims. One run on one laptop cannot substantiate cluster scalability.

---

## 6. Figure plan: salient plots and what each answers

Use Matplotlib figures generated from actual audit/Parquet/ML output. Prefer vector PDF/SVG for LaTeX inclusion and 300 dpi PNG for preview. Keep axes readable, state N and source stage in captions, label units, use consistent typography, and explicitly distinguish observed sample statistics from paper-reported composition.

### Figure A. Dataset anatomy and data contracts (schematic, not empirical)

A compact schematic of `(N,19,4)` with axes named, slot groups labelled, and final feature dimension shown. Mark class code 0 as padding and classes 1–4 as MET/electron/muon/jet. Caption: “Published schema; runtime shape and metadata validated from local file.” Do not place 13.45M events on it.

### Figure B. Full-corpus object multiplicity

A single figure with three aligned panels for electron, muon and jet multiplicity. Use integer bins, count labels or a separate percentage axis, and a log y-axis if tail counts vary strongly. Title/subtitle should provide verified event total. This directly explains occupancy and the fixed 4/4/10 capacity.

### Figure C. pT spectra by object class

Use occupied slots only and separate MET from particle-object panels because MET is not an electron/muon/jet. Plot logarithmic y-counts and log-spaced pT bins or clearly documented linear bins; optionally show normalised density as a second version for shape comparison. Include underflow/overflow counts from audit manifest. `phi` and padding rows should never be included in pT distributions.

### Figure D. HT conditional distribution by number of jets

Use a box/violin or quantile ribbon showing median and IQR by `n_jets`; print sample count beneath each category. Outlier flier display can obscure the distribution; use quantile ranges and separately show ECDF/upper-tail panel. Do not label quartiles “exact” if query uses approximate percentile functions. Report small group counts to prevent over-interpreting rare bins.

### Figure E. MET versus jet HT joint density

Use a 2D histogram or hexbin with log-count color scale rather than plotting millions of opaque points. Include marginal distributions and perhaps a median `MET` by `HT` bin. Document bin edges and include a separate statistic table with Pearson/Spearman by jet multiplicity. This is one of the strongest scientific figures if correctly generated.

### Figure F. Quality audit panel

Panel 1: structural zero-padding fraction and occupied slots. Panel 2: detected defect counts for nonfinite values, unknown/non-integral codes, type-position mismatch, negative pT and out-of-range phi. Plot defects with count and percentage; zero bars should remain visible and annotated `0 observed`. Padding is expected format structure and must not be mixed with corruption flags. Use exact counters from the raw audit JSON.

### Figure G. Feature association

Show two heatmaps side by side when useful: Pearson linear correlation and Spearman rank correlation across continuous engineered physics features. Exclude ID and quality flags. Mask/annotate diagonal and N. Explain that strong relations can follow feature construction: `ht_jets` sums jet pT; `n_jets` counts terms in that sum.

### Figure H. Outlier-ranking diagnostics, optional ML

One composite figure or two panels: (1) empirical centroid-distance CCDF with 95th/99th/99.9th percentile markers; (2) distance distribution grouped by `n_jets` with group sample counts. Add a companion top-event table with `event_row_id`, `n_jets`, MET, HT, lepton sum, leading pT, max |eta| and quality flags. Avoid a plain unlabeled distance histogram as sole evidence. State scoring is in scaled feature space and no signal truth is available.

### Figure I. BDA execution evidence

Compact stage-duration/throughput chart, plus storage statistics (HDF5 bytes, Parquet bytes, number of row groups, partition file counts). Use only measured manifest values. If no data has been run, omit this figure or render a clearly labelled “measurement not yet collected” table; no mock timings.

**Recommended core report visuals:** A (schema), B (multiplicity), C (pT), D (HT by jets), E (MET–HT), F (quality), G (correlation). Add H only if optional ML finishes. Add I only with real runtime logs. Keep the published process-mixture chart separate and label as paper-derived.

---

## 7. Architecture diagram: design specification

Replace the current wide ASCII box drawing with a scalable vector figure using TikZ (`arrows.meta`, `positioning`, `fit`, optionally `backgrounds`) or an SVG/PDF created from an authored diagram. In the PDF the figure should be visually significant but compact enough for one A4 page and readable when printed.

Use **three visual zones**:

1. **Verified source and transformation (main solid path):** Zenodo file + checksum → HDF5 shape/quality audit → chunked physics feature ETL → typed Parquet event table.
2. **Analytics branches from Parquet:** Spark SQL queries; Spark RDD key-value aggregation; optional scikit-learn MiniBatchKMeans. Connect the branches explicitly.
3. **Compatibility/demo paths (dashed or lighter style):** optional Pig local-mode TSV projection; external Hive table registration; Hadoop Streaming mapper/reducer on an existing HDFS cluster. Visually separate them from default Compose execution.

Finally, connect actual result artifacts (JSON manifests, CSV tables, figures, final LaTeX report) to a compact “Evidence package” output node. Use concise node labels; detail belongs in prose/table, not inside boxes.

The architecture must communicate runtime reality:
- Default `docker compose` pipeline: download → audit → ETL → Spark SQL/RDD → outputs.
- Pig local mode is optional.
- Hive DDL targets an external configured Hive instance.
- Hadoop Streaming requires an existing HDFS/Hadoop runtime.
- Optional ML is a branch from the same full Parquet table.
- `local[6]` is six local Spark execution threads on one host, not six worker nodes.

Include a separate **execution workflow** only if needed; don't duplicate the same stages in an ASCII figure, numbered list, and redundant prose. Use the figure for system components, and a short paragraph for execution ordering.

---

### Optional TikZ layout starter

Use this as an architectural starting point if the report source already loads `tikz`; adjust node widths to actual margins and validate the rendered PDF. Keep optional tools outside the solid core path.

```latex
% Preamble
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,backgrounds,calc}

% Figure body
\begin{figure}[htbp]
  \centering
  \begin{tikzpicture}[
    font=\sffamily\footnotesize,
    node distance=5mm and 6mm,
    stage/.style={draw=blue!55!black, fill=blue!5, rounded corners=2mm,
      text width=2.65cm, minimum height=10mm, align=center, inner sep=2mm},
    analysis/.style={draw=teal!55!black, fill=teal!5, rounded corners=2mm,
      text width=2.9cm, minimum height=11mm, align=center, inner sep=2mm},
    optional/.style={draw=gray!70, fill=gray!5, dashed, rounded corners=2mm,
      text width=2.7cm, minimum height=9mm, align=center, inner sep=2mm},
    flow/.style={-{Stealth[length=2mm]}, thick, draw=blue!60!black},
    optflow/.style={-{Stealth[length=1.8mm]}, dashed, draw=gray!70}
  ]
    \node[stage] (source) {Zenodo source\\HDF5 + checksum};
    \node[stage, right=of source] (audit) {Schema gate\\chunked quality audit};
    \node[stage, right=of audit] (etl) {Event features\\bounded-memory ETL};
    \node[stage, right=of etl] (parquet) {Typed Parquet\\one row per event};

    \draw[flow] (source) -- (audit);
    \draw[flow] (audit) -- (etl);
    \draw[flow] (etl) -- (parquet);

    \node[analysis, below left=10mm and 4mm of parquet] (sql) {Spark SQL\\grouping, quantiles, bins};
    \node[analysis, below=10mm of parquet] (rdd) {Spark RDD\\map / reduceByKey};
    \node[analysis, below right=10mm and 4mm of parquet] (ml) {Optional ML\\scaled cluster distance};
    \coordinate (fanout) at ($(parquet.south)+(0,-3mm)$);
    \draw[flow] (parquet.south) -- (fanout);
    \draw[flow] (fanout) -| (sql.north);
    \draw[flow] (fanout) -- (rdd.north);
    \draw[flow] (fanout) -| (ml.north);

    \node[stage, below=8mm of rdd, text width=7.8cm] (evidence)
      {Evidence package\\JSON manifests, query tables, salient plots, LaTeX report};
    \draw[flow] (sql.south) |- (evidence.west);
    \draw[flow] (rdd.south) -- (evidence.north);
    \draw[flow] (ml.south) |- (evidence.east);

    \node[optional, below=5mm of evidence, text width=9.5cm] (compat)
      {Optional / external demonstrations: Pig local mode ; Hive external table ; Hadoop Streaming on configured HDFS};
    \draw[optflow] (parquet.south east) |- (compat.east);
  \end{tikzpicture}
  \caption{Core Docker execution and optional ecosystem integrations. Solid arrows identify the default pipeline; dashed styling indicates compatibility paths that require separate execution environments.}
  \label{fig:system-architecture}
\end{figure}
```

**Compile refinement required:** the example defines structure and is not a proof that every optional integration ran. Ensure the node glyph separators compile with the project's font; replace them with `\textbullet` or plain commas if needed. The report should use the final polished diagram rendered at full page width, not a screenshot of source code.

---

## 8. Repository implementation truth table

Inspect the latest repository at runtime; this table describes the code discovered in the supplied ZIP and may change when the coding agent adds tests/features.

| Path | Current role | Evidence required in final report |
|---|---|---|
| `scripts/fetch_dataset.py` | Zenodo API metadata, full download and source-checksum gate | Actual `verified_manifest.json`; file bytes and MD5 match. |
| `scripts/audit_hdf5.py` | HDF5 inventory and chunked full-row quality audit | `audit/raw_audit.json`, `hdf5_inventory.csv`, `quality_metrics.csv`; row count agrees with HDF5 shape. |
| `scripts/extract_features.py` | Every-event feature engineering and Parquet row-group writing | `etl_manifest.json`; input/output rows equal and dropped/sampled/filtered are zero. |
| `scripts/spark_analysis.py` | Partitions by jet multiplicity; executes `sql/*.sql`; performs RDD map/reduce | `spark_manifest.json`, query outputs and reduced count equal input row count. |
| `sql/01`–`07` | Seven Spark SQL analyses listed in §4.4 | Query input/output schema, row count and interpretation. |
| `scripts/make_visuals.py` | Matplotlib plots from audit/Parquet outputs | `visual_manifest.json`, images and source manifest. |
| `scripts/stream_cluster.py` | Three-pass StandardScaler/MiniBatchKMeans on every derived row | `cluster_manifest.json`; all processed row counts reconcile. |
| `scripts/export_pig_tsv.py` | Export full event row projection to TSV | Export count equals ETL rows and output schema described. |
| `pig/analyze_events.pig` | Group/aggregate full TSV in Pig local mode | Pig runtime log and result counts if claimed executed. |
| `hadoop/mapper.py`, `hadoop/reducer.py` | Streaming map/reduce scripts over five-column TSV | Unit/shell test and true Hadoop job log if claiming Hadoop job execution. |
| `hive/register_events.hql` | External table DDL for configured Hive runtime | Native Hive metadata/query output if claiming execution. Otherwise label script as provided. |
| `Dockerfile`, `docker-compose.yml`, `Makefile` | Python/Spark main runtime and optional Pig environment | Build/test/run logs; actual image/service architecture. |
| `tests/test_core.py` | Unit tests with synthetic HDF5 fixtures | Test log; explicitly state synthetic values are tests, not research results. |
| `docs/DATA_DICTIONARY.md`, `ARCHITECTURE.md`, `RESULTS_PROTOCOL.md`, `VIVA_NOTES.md` | Project docs and intended contracts | Reconcile against source code. |
| `docs/CA3_REPORT_DRAFT_ULTRA.md` and `.html` | Existing report draft formats | Keep one canonical report source; generated outputs must be build products. |

### Critical code/report mismatches to resolve

- Existing report says 13,451,915 rows. Source paper and repository README say expected 4,000,000 for training file. Re-audit and replace every derivative result.
- Existing report claims 1,022,345,540 scalar values and 539 row groups, which follow the incompatible 13.45M figure. Recompute.
- Existing report claims nine analytical queries and use of Window / `ROLLUP`; repository currently has seven SQL files and the inspected SQL has no window or rollup expressions. Implement justified queries and tests or remove those claims.
- Existing report says the runtime demonstrated a distributed engine; core Spark master is `local[6]`. Call this a single-host local Spark execution using the Spark API.
- Existing report implies full Hadoop/Hive/Pig integration. Default Compose job runs Spark SQL and RDD operations. Hive DDL, Hadoop Streaming, and Pig local-mode are distinct optional paths. Describe them by execution status.
- Existing report says all course outcomes were fully demonstrated, while literal Mahout is absent. Make rubric mapping exact and state the Mahout caveat.
- Existing PDF reports highly specific empirical stats. Those statistics cannot be trusted until manifests match the verified 4M-row source. Rebuild plots from current run outputs.
- Pasted LaTeX source contains Markdown bold markers inside `\textbf{...}`, doubled/backslash-escaped strings and a large ASCII `verbatim` figure. Ensure generated `.tex` is valid TeX and uses `\textbf{Label}` rather than Markdown syntax.
- The supplied project ZIP appears to contain Markdown/HTML report drafts but no obvious canonical `.tex` source. Locate the actual source in the coding-agent working directory; if absent, create a canonical `report/main.tex` and compile it reproducibly.

---

## 9. CA3 report structure and required depth

Follow the assignment's twelve sections exactly. Each section has its own evidentiary job.

1. **Title:** accurate description: big-data analytics and exploratory event outlier ranking; no new-physics discovery claim.
2. **Problem and objectives:** one research question, explicit scope, row-preservation and quality gates, research outcomes.
3. **Background/introduction:** LHC trigger context, dataset motivation, simulation caveats, why event anomaly ranking is relevant.
4. **Dataset description:** record/file/version/checksum/license, authoritative row count, actual HDF5 inventory, axis semantics, object codes, thresholds, source paper vs locally observed details.
5. **Methodology:** data contracts, audit logic, ETL process, query plan, aggregation semantics, optional ML and validation method.
6. **System architecture/workflow:** concise vector diagram with runtime truth; no ASCII architecture art.
7. **Big Data tools:** reason each tool exists and identify whether core, optional-local, script-only, or external-runtime. Give exact versions from manifests.
8. **Implementation / queries / algorithms:** feature equations, code-path summaries, sample SQL / MapReduce key-value algorithm / Pig dataflow / Hive DDL only at useful lengths; point to repo paths.
9. **Analysis and results:** actual full-corpus measured results only; each finding linked to table/figure/query manifest. Discuss distributions, correlations, outlier limitations.
10. **Visualization/graphs:** explain the research question each plot answers, axis choices, data source, N, bins/transformations and limitations.
11. **Conclusion:** answer research question and state bounded claims, limitations and next steps. Avoid unearned “all outcomes fully satisfied.”
12. **References:** primary dataset paper, Zenodo record, authors' code/challenge page and official docs for every named tool/function.

### Useful sub-sections within existing headings

- Dataset Description: “HDF5 container and tensor axes”, “slot ordering and padding”, “data generation and selection”, “data lineage and licenses”.
- Methodology: “integrity gate”, “quality gate”, “event-level feature extraction”, “columnar layout”, “full-corpus aggregation”, “optional unsupervised scoring”, “reproducibility contracts”.
- Tools: “core runtime”, “Hadoop MapReduce demonstration”, “Hive SQL interface”, “Pig dataflow”, “optional ML”, “visualization”.
- Results: “schema audit”, “multiplicity”, “jet activity by multiplicity”, “MET–HT relationship”, “model-ranking diagnostics”, “performance/throughput”. Include only result subsections supported by executed output.

---

## 10. Statistical and scientific pitfalls to explicitly manage

1. **Simulated vs collision data:** no direct claim that these events were recorded by ATLAS/CMS. They are simulation-based and detector-parametrized.
2. **Selection bias:** the corpus requires a high-pT electron or muon. These distributions describe selected events, not inclusive pp collisions.
3. **Fixed caps:** only a finite number of e, mu and jets are stored; very high object multiplicity is truncated by design.
4. **Padding:** do not include class-zero slots in spectra, sums or multiplicities.
5. **MET handling:** MET is a vector-derived quantity, distinct from a detected particle; no eta of MET in feature interpretation.
6. **Class identity:** type code is object category, not source process or anomaly label.
7. **No signal ground truth:** the main training file is not enough for supervised signal-performance metrics.
8. **High `H_T`:** a tail can reflect more jets and/or higher pT. Interpret jointly with multiplicity and leading pT.
9. **Correlations:** construction-induced correlation is expected; `H_T` is a sum of jet pT and jet count is number of terms. Pearson correlation depends on influential tails.
10. **Zero counts:** report “zero observed defects under specified test” rather than “perfect data”. Include detection rules and tolerances.
11. **Anomaly score:** distance from a cluster center is model-relative and not calibrated for physics significance.
12. **Data-processing semantics:** `event_row_id` is index-only. Preserve one row per source event; no subsampling or silent invalid-row deletion.
13. **Distributed claims:** no single-host run establishes scale-out performance or trigger latency.
14. **Storage/benchmark claims:** file compression ratio, Parquet speedups and memory use must be measured, not assumed from format design.
15. **Approximate quantiles:** label Spark `percentile_approx` output and its accuracy setting accordingly.
16. **Multiple comparisons / tail hunting:** a top-scoring event list is a review queue. Without pre-registered criteria and background calibration it is susceptible to post-hoc interpretation.

---

## 11. Source register: high-quality primary references

Use these sources as the default citation base. Cite the dataset paper and record for all dataset-specific claims; cite versioned official technical manuals for software behavior.

1. **Dataset paper (peer-reviewed, open access):** Govorkova et al., *LHC physics dataset for unsupervised New Physics detection at 40 MHz*, *Scientific Data* 9, 118 (2022). [Article](https://www.nature.com/articles/s41597-022-01187-8) · [DOI](https://doi.org/10.1038/s41597-022-01187-8). Defines physics context, event format, object slots, padding, selection cuts, simulation and sample composition.
2. **Official source record:** Zenodo, [Training Dataset, record 5046428](https://zenodo.org/records/5046428). Defines downloadable file, published size, MD5, license, record version/history.
3. **Dataset authors' challenge documentation:** [ADC2021](https://mpp-hep.github.io/ADC2021/). Data-loading and challenge scope.
4. **Dataset authors' example repository:** [mpp-hep/ADC2021-examplecode](https://github.com/mpp-hep/ADC2021-examplecode). Example HDF5 loading, anomaly-model workflows and challenge-specific conventions. Treat this as author/example code, not a replacement for the paper's formal dataset definition.
5. **Hadoop MapReduce Tutorial:** [Apache Hadoop MapReduce Tutorial](https://hadoop.apache.org/docs/current/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html). Mapper, reducer, partitioning, shuffle/sort, combiners, input/output, execution semantics.
6. **Hadoop Streaming:** [Apache Hadoop Streaming](https://hadoop.apache.org/docs/current/hadoop-streaming/HadoopStreaming.html). Mapper/reducer executables through stdin/stdout protocol. Check docs matching the installed Hadoop version.
7. **Spark SQL 3.5.7:** [SQL/DataFrame/Dataset Programming Guide](https://spark.apache.org/docs/3.5.7/sql-programming-guide.html). Structured query execution, DataFrames, SQL integration and optimization.
8. **Spark RDD 3.5.7:** [RDD Programming Guide](https://spark.apache.org/docs/3.5.7/rdd-programming-guide.html). RDDs, transformations/actions, `map`, `reduceByKey`, shuffle and lazy evaluation.
9. **Spark SQL windows:** [Window syntax](https://spark.apache.org/docs/3.5.7/sql-ref-syntax-qry-select-window.html). Window partitioning and ranking syntax.
10. **Spark SQL GROUP BY:** [GROUP BY, ROLLUP, CUBE](https://spark.apache.org/docs/3.5.7/sql-ref-syntax-qry-select-groupby.html). Grouping sets, subtotals and rollup semantics.
11. **Hive DDL:** [Hive LanguageManual DDL](https://hive.apache.org/docs/latest/language/languagemanual-ddl/). External tables, storage formats, partitioned schemas, metadata.
12. **Hive DML:** [Hive LanguageManual DML](https://hive.apache.org/docs/latest/language/languagemanual-dml/). Load / insert semantics and data handling.
13. **Apache Pig 0.17:** [Pig Latin Basics](https://pig.apache.org/docs/r0.17.0/basic.html) and [built-in functions](https://pig.apache.org/docs/r0.17.0/func.html). `LOAD`, `GROUP`, `FOREACH`, `GENERATE`, `COUNT`, `AVG`, `STORE`.
14. **HDF5 access in Python:** [h5py Dataset documentation](https://docs.h5py.org/en/stable/high/dataset.html). Dataset shape/dtype/nbytes, slicing, chunked layout, compression and IO effects.
15. **Parquet / Arrow:** [PyArrow Parquet guide](https://arrow.apache.org/docs/python/parquet.html). Columnar layout, row groups, compression, statistics, partitioned datasets and Spark compatibility.
16. **Scaling:** [scikit-learn StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html). Mean/variance standardisation and outlier sensitivity.
17. **Clustering:** [scikit-learn MiniBatchKMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html). Incremental minibatch clustering, parameters, labels, centroids and distances.
18. **Plotting API:** [Matplotlib hist](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html), [hexbin](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hexbin.html), [imshow](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.imshow.html). Histogram binning, dense joint distributions and matrix visuals.

### Citation practice

- Use numeric citations throughout the report (`[1]`, `[2]`) or consistent author-year citations. Do not mix styles.
- Cite statements near the claim, especially tensor shape/padding, event selection, generation chain, trigger context and process composition.
- Cite official docs where discussing particular API behavior. A dependency listed in `requirements.txt` is not proof that an API was executed.
- Distinguish source-derived claims, locally measured results, calculated quantities and implementation design proposals.
- Record exact doc version matching project versions where possible. `latest` links may change; prefer Spark 3.5.7 and Pig 0.17 versioned references.

---

## 12. Implementation and report acceptance checklist

### Data integrity

- [ ] Zenodo API record/file metadata captured; license and record version recorded.
- [ ] Download byte count and MD5 match authoritative record; local SHA-256 computed.
- [ ] HDF5 shape/dtype/metadata output saved.
- [ ] `Particles.shape[0]` reconciled against expected 4,000,000 or any documented official version discrepancy.
- [ ] All rows/chunks scanned; no unlogged partial scans.
- [ ] Scalar/slot arithmetic verified.
- [ ] ETL reads and writes equal rows; no drops/sample; `event_row_id` min/max/uniqueness checked.
- [ ] Spark partition row count, SQL inputs and RDD key counts reconcile.
- [ ] Optional ML scaled/update/scored rows reconcile.

### Analysis

- [ ] Each figure has a named analytical question.
- [ ] All axes, units, bin widths, N and data source are stated.
- [ ] Log transforms described, zeros accounted for, tails preserved.
- [ ] Quality-zero bars shown as observed zeros; structural padding separate.
- [ ] Correlations are conditional/qualified and correctly defined.
- [ ] Outlier score explicitly described as model-relative distance.
- [ ] Empirical result text was generated from local manifests only.

### Big Data tool honesty

- [ ] Spark SQL is labelled Spark SQL.
- [ ] Spark RDD aggregation is labelled MapReduce-style unless actual Hadoop job is executed.
- [ ] Hadoop Streaming is marked external-cluster/optional if not executed.
- [ ] Hive DDL is marked registration script if no native Hive engine runs.
- [ ] Pig is marked local-mode if `pig -x local` runs; external/distributed otherwise.
- [ ] scikit-learn is not called Mahout.
- [ ] `local[6]` is correctly described as local Spark execution using up to six concurrent threads.

### LaTeX/report quality

- [ ] Canonical `.tex` source exists and compiles from clean checkout.
- [ ] No Markdown syntax remains inside LaTeX commands/tables.
- [ ] System architecture is a compact vector diagram; no ASCII boxes.
- [ ] Figure paths are reproducible and generated by pipeline; no hardcoded data curves.
- [ ] Tables do not overflow page/margins; captions explain interpretation.
- [ ] All twelve CA3 sections exist in supplied order.
- [ ] Bibliography links/DOIs verified; no citation or cross-reference unresolved.
- [ ] PDF rebuilt after final code run; report values and repository manifests agree.
- [ ] Machine-readable writing-guardrail JSON is regenerated from the final report source, with measured failures preserved rather than overridden.

