# CA3 Beamer deck — slide content sketch

Style: caveman ultra. Deck = complement to `docs/CA3_REPORT.pdf`. All numbers code-verified vs manifests. Report tex stale spots noted → deck uses manifest values.

Palette: primary RGB(16,44,87) · secondary RGB(53,101,169) · accent gold RGB(218,165,32) · teal RGB(0,128,128) · defect red RGB(176,32,48).

---

## S1 Title
- Big Data Analytics → LHC Event Quality + Exploratory Outlier Ranking in 40 MHz Training Data
- CA3 case study · Soham Kulkarni · PRN 23070126129 · AIML B2 · FY 2023–27
- Stack: Hadoop · Hive · Spark 3.5.7 · Pig 0.17 · scikit-learn 1.6.1 · Docker Compose

## S2 Agenda
- problem → dataset → tensor schema → physics context → pipeline → quality gate → results → SQL + RDD → ecosystem → ML → caveats

## S3 Problem + RQ
- 40 MHz crossings → 25 ns spacing → trigger prunes rate pre-storage
- RQ: reproducible bounded-memory pipeline → validate every event → tensor → auditable table → BigData ops → kinematics + outlier ranking @ 6-core host
- scope: `local[6]` single Docker host → no multi-node speedup, no L1 latency; no per-event truth labels → no accuracy/ROC-AUC/precision/recall/discovery claims

## S4 Dataset + provenance (table)
- Zenodo rec 5046428 · `background_for_training.h5` · 646,391,984 B = 646.392 MB
- MD5 `08cb4801229f9d480567f8d3f5cac134` ✓ match pub · SHA-256 `5f460bd3af44…`
- `/Particles` shape (13,451,915, 19, 4) float64 · gzip-4 · chunks (26274,1,1)
- paper reports 4.0M events → audit reads 13,451,915 rows = 3.36× → ALL rows processed, 0 sampled/dropped
- scalars: 13.45M×19×4 = 1,022,345,540 → ×8 B = 8.18 GB raw payload

## S5 Tensor schema (fig: `docs/figures/documented_tensor_schema.png`)
- slot 0 = MET t=1 · slots 1–4 = e⁻ t=2 · slots 5–8 = μ t=3 · slots 9–18 = jets t=4 · unused = t=0 padding
- fields/slot: pT, η, φ, class · desc-pT sorted within group
- padding rule: t=0 ⇒ pT=η=φ=0.0 · type check: finite + integral + ∈{0..4} before cast

## S6 Physics context (fig: `docs/figures/published_process_mix.png`)
- SM mix (published): W→ℓν 59.2% · QCD 33.8% · Z→ℓℓ 6.7% · tt̄ 0.3%
- 13 TeV pp · PYTHIA + DELPHES · single-lepton trigger
- pT=√(px²+py²) · η=−ln tan(θ/2) · Δφ=atan2(sin,cos) · MET = stored slot-0 magnitude
- type code = reconstructed species ≠ generator process · no per-event truth in file

## S7 Architecture (TikZ flow)
- 1 Zenodo ingest (MD5+size gate) → 2 HDF5 audit (1.02B scalars) → 3 feature ETL (13.45M rows) → 4 Parquet store (624.78 MB Snappy, 539 row groups)
- bus → engines: Spark SQL ×9 · RDD map/reduceByKey key=Njets · MiniBatchKMeans K=8
- outputs: 9 figs (PNG+SVG) · 9 CSV result dirs · JSON manifests · `cluster_scores.parquet`
- dashed row: Hadoop Streaming · Hive DDL · Pig — standalone, external infra

## S8 Execution contract
- invariants: checksum+size gate → HDF5 schema gate → 1:1 row mapping → Parquet==Spark==MR totals; violation → fail-fast
- chunk = 25,000 rows → 539 chunks; bounded memory; batch size configurable
- parity proofs: ETL in==out · partition read-back count · ∑n_j = N_input

## S9 Quality gate (chart: occupancy stacked bar 82.83% pad / 17.17% occupied)
- defect counters ALL ZERO: NaN · +inf · −inf · invalid type · non-integral type · pT<0 · |φ|>π · bad padding · wrong-slot
- occupied slots 43,876,265 · padding 211,710,120 (82.83%) · 100% events padded
- type counts: MET 13,451,915 · e⁻ 7,894,415 · μ 6,859,819 · jets 15,670,116

## S10 Multiplicity (fig: `outputs/figures/02_event_multiplicity.png` + pgfplots bars)
- e⁻: 0→45.5% · 1→50.5% · 2→4.0% · 3→0.08% · 4→0.004%
- μ: 0→52.3% · 1→44.5% · 2→3.2% · 3→0.05% · 4→0.001%
- jets: 0→37.8% · 1→29.8% · 2→18.4% · 3→8.8% · 4→3.4% · … · 10→0.005%
- Nj≤2 → 86.0% events; tail → full slot usage (731 events @ Nj=10)

## S11 pT spectra (fig: `outputs/figures/01_pt_spectrum_by_object_type.png`)
- log-scale pT per class; distinct trigger threshold pT>23 GeV; peaks 20–50 GeV; jet tail → 1000+ GeV; type-0 padding excluded

## S12 MET×HT density (fig: `outputs/figures/03_met_vs_jet_ht_density.png`)
- hexbin log density; bulk MET<50 GeV ∧ HT<100 GeV; conditional median HT rises with MET

## S13 HT | Nj (fig: `outputs/figures/04_ht_by_jet_multiplicity.png`)
- median HT monotonic 0 → 652.9 GeV; IQR widens w/ Nj; P75–P97 tail annotated; n per bin shown

## S14 Correlations (fig: `outputs/figures/06_feature_correlations.png`)
- HT–Nj: Pearson r=0.74, Spearman ρ=0.87 (construction-driven); MET–HT r=0.15 weak

## S15 HT corpus dist (fig: `outputs/figures/07_full_corpus_ht_distribution.png`)
- symlog render; 5.08M zero-jet events @ HT=0; physical tail >4,000 GeV

## S16 Spark SQL suite (table: 9 queries)
- runtime 93.8 s · local[6] · 12 shuffle partitions · AQE on
- Q01 overview (COUNT/SUM/AVG/percentile_approx) → 1 row · Q02 multiplicity UNION ALL → 21 · Q03 HT|Nj cond-agg+corr → 11 · Q04 2D bins 20×50 GeV → 943 · Q05 quality flags → 1 · Q06 top-HT ORDER BY+LIMIT → 100 · Q07 feature corr GROUP BY → 11 · Q08 Window DENSE_RANK+ROW_NUMBER top-3/slice → 30 · Q09 ROLLUP e⁻×μ → 28

## S17 MapReduce RDD (pgfplots line: mean HT vs Nj)
- map: (Nj, (1, HT, MET, Sℓ)) · reduce: elementwise ⊕ (assoc+comm) · ∑n_j = 13,451,915 ✓
- mean HT GeV: 0→0 · 1→38.8 · 2→85.9 · 3→136.9 · 4→193.3 · 5→258.2 · 6→332.4 · 7→417.1 · 8→512.3 · 9→610.8 · 10→739.6
- mean MET 39.2→68.4 GeV · mean Sℓ 34.6→63.2 GeV

## S18 Ecosystem artefacts (placeholders: native run logs)
- Hadoop Streaming: `mapper.py`/`reducer.py` tab protocol · real job needs HDFS/YARN + logs — script-only here
- Hive: `register_events.hql` external partitioned Parquet table + `MSCK REPAIR TABLE` · needs Hive install; Spark SQL ≠ HiveServer2 run
- Pig 0.17: `analyze_events.pig` GROUP/FOREACH/COUNT/AVG · `-x local` · full-row TSV · legacy Java 8 image · no distributed Pig claim

## S19 ML: streaming MiniBatchKMeans (`scripts/stream_cluster.py`)
- 10 feats: met_pt · ht_jets · sum_lepton_pt · n_e⁻ · n_μ · n_jets · lead e⁻/μ/jet pT · max|η|
- pass1 `StandardScaler.partial_fit` → pass2 `MiniBatchKMeans.partial_fit` K=8 rs=27 n_init=3 → pass3 score all rows
- z_j=(x_j−μ_j)/σ_j · s(x)=min_k ‖z(x)−μ_k‖₂
- rows scaled == fit == scored == 13,451,915 · 25.2 s · inertia 7756.2 · 539 iters

## S20 Anomaly visuals (figs: `08_cluster_distance_distribution.png` + `09_cluster_distance_by_jet_multiplicity.png`)
- score: min 0.224 · mean 1.648 · σ 0.946 · max 336.8 · P99 = 4.62
- median distance: Nj=0 → 1.15 · Nj=10 → 7.12 → score tracks multi-jet topology
- cluster sizes 281,892 … 3,994,528
- score ≠ probability ≠ p-value ≠ discovery

## S21 Evidence classes + guarantees
- classes: published fact / calculated quantity / local measurement / conditional artifact — never mixed
- guarantees: reject partial/bad-checksum downloads · schema fail-fast · ETL parity · partition parity · MR sum parity · ML row parity · tests inject corruption into synthetic fixture only

## S22 Course-outcome alignment
- CO1 MapReduce → RDD kv + Hadoop scripts · CO2 Hive/SQL → 9 HiveQL-compatible queries + HQL DDL · CO3 Pig → local-mode grouped dataflow · CO4 Spark columnar → ETL + partitionBy + read-back · CO5 intelligent technique → MiniBatchKMeans (scikit-learn, NOT Mahout — caveat stated) · visual analytics → 9 figs w/ manifest

## S23 Conclusion + caveats
- 13,451,915 events audited → 0 defects · ETL 1:1 parity · 9 SQL groups · RDD ∑=N · K=8 full-corpus scores
- caveats: no truth labels → no new-physics claim · scores = exploratory geometric rank · local[6] ≠ scale-out benchmark · native Hadoop/Hive/Pig runs need external infra
- placeholders: signal-benchmark records · multi-node scaling · Δφ separation feature · Mahout port

## S24 References + repro
- Govorkova et al., SciData 9:118 (2022), doi:10.1038/s41597-022-01187-8 · Zenodo 5046428, doi:10.5281/zenodo.5046428 · ADC2021 · Spark 3.5.7 SQL+RDD guides · Hadoop Streaming · Hive DDL · Pig 0.17 · PyArrow 18.1.0 · scikit-learn (JMLR 12:2825)
- repro: `make build && make test && make all` · `xelatex ×2 docs/CA3_REPORT.tex`

---

## Report-vs-code reconciliation (footnote for S4/S16)
- report §12.1 hardcodes 4M events / 304M scalars / 160 chunks → stale; manifest: 13,451,915 / 1,022,345,540 / 539
- report §6.3 claims 7 SQL + "no Window/ROLLUP" → stale; code has `sql/08_window_jet_slice_rankings.sql` + `sql/09_multidimensional_lepton_rollup.sql`, manifest shows 9 executed
- report §10 table already says 9 queries incl. Window/ROLLUP ✓
- deck = manifest-truth; report PDF = conditional fallback text (no `outputs/report_generated_results.tex` present)
