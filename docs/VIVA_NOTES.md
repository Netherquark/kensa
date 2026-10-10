# CA3 viva notes

## Dataset and physics

**What does 40 MHz mean?** Real-time event-selection use case described by the LHC dataset paper. Project input is finite, simulated offline HDF5 data.

**What is inside each event?** Nineteen slots: MET, up to four electrons, four muons and ten jets. Each slot stores pT, eta, phi and type code. Dataset uses zero padding for absent objects.

**What are pT, eta, phi?** `pT` is momentum transverse to the beam. `eta` is pseudorapidity, `-ln(tan(theta/2))`. `phi` is azimuth around the beam axis, in radians. Published phi range: `[-pi, pi]`.

**Why is padding important?** Fixed tensor shape enables batch computation. Code 0 marks empty slots. Counting zeros as particles biases multiplicity and kinematic distributions.

**Can the project claim new physics?** No. Main training corpus contains simulated Standard Model events, without per-event hidden-signal truth. High score means atypical engineered features under chosen model; detector effects and rare Standard Model topologies can also produce it.

## BDA concepts

**Why HDF5 to Parquet?** HDF5 preserves the source tensor. Parquet provides typed, columnar features and predicate / projection pushdown suited to Spark SQL and repeatable reports.

**What is ETL?** Extract HDF5 chunks; transform event tensor to physics-informed summary fields; load row groups into Parquet. Full event-row count must persist.

**What MapReduce operation is implemented?** Map each event to key `n_jets` with `(1, ht_jets, met_pt)`. Reduce by key using elementwise sums. Divide totals by grouped event count for means.

**Is Spark a distributed cluster here?** Core runtime uses Spark `local[6]` on one Docker host. RDD API demonstrates map/reduce semantics. Output gives local-run evidence, not a multi-node benchmark.

**Is Spark SQL the Hive engine?** Spark SQL runs the bundled SQL query suite. Queries use HiveQL-compatible constructs. `hive/register_events.hql` defines native Hive external-table registration for an existing Hive installation.

**Where is Pig?** `pig/analyze_events.pig` performs grouped aggregation. Optional profile uses Apache Pig 0.17 local mode against all event rows projected to TSV. This is Pig Latin execution, not a distributed Pig cluster.

## Quality and model

**How is row loss prevented?** Fetch checksum and size checks; raw scan count; ETL input/output parity; Spark partition row-count parity; reduce-key counts sum to input count; model scores cover every row.

**Why check type codes?** Published code domain is `{0,1,2,3,4}`. Unknown codes can invalidate event features. Slot layout is also checked.

**Why stream in chunks?** Bounds memory for the HDF5 scan and Parquet write; chunk size is configurable without changing record scope.

**What is cluster distance?** Euclidean distance to nearest centroid after feature standardisation. It measures feature-space atypicality. It is not calibrated probability, p-value, significance or a discovery claim.

**Why use ML at all?** Optional extension for CO5-style intelligent analytics. Core report remains valuable through schema validation, full-corpus processing, aggregations and scientific visualization.

## CA3 rubric mapping

| Rubric | Evidence |
|---|---|
| Problem, methodology, tools | Sections 2, 5, 6, 7 of report; source metadata and architecture |
| Analysis / interpretation | Seven SQL outputs, full-corpus MapReduce summary, quality counters, seven plots |
| Documentation / structure | Dataset dictionary, record citations, manifest files, reproducible Docker instructions |
| Presentation / viva | These notes; actual generated runtime and query outputs; explicit limitations |
