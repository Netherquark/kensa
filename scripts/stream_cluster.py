#!/usr/bin/env python3
"""Optional full-corpus MiniBatchKMeans descriptive novelty scoring.

Every event participates in scaler fitting, cluster updates and scoring. The resulting
nearest-centroid distance is exploratory and must not be interpreted as a calibrated
probability of new physics.
"""
from __future__ import annotations
import argparse, json, time
from collections import Counter
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INPUT=ROOT/"data/processed/events.parquet"
DEFAULT_OUT=ROOT/"outputs/ml/cluster_scores.parquet"
FEATURES=["met_pt","ht_jets","sum_lepton_pt","n_electrons","n_muons","n_jets","leading_electron_pt","leading_muon_pt","leading_jet_pt","max_abs_eta"]


def batches(path:Path,batch_rows:int):
    dataset=ds.dataset(path,format="parquet")
    return dataset.to_batches(columns=FEATURES+['event_row_id'],batch_size=batch_rows)


def matrix(batch):
    table=batch.select(FEATURES)
    arr=np.column_stack([table.column(i).to_numpy(zero_copy_only=False) for i in range(len(FEATURES))]).astype(np.float64,copy=False)
    arr=np.nan_to_num(arr,nan=0.0,posinf=0.0,neginf=0.0)
    return arr


def run(input_path:Path,out_path:Path,batch_rows:int=25000,n_clusters:int=8):
    if not input_path.exists(): raise FileNotFoundError(f"Missing {input_path}; run ETL first")
    if n_clusters<2: raise ValueError("n_clusters must be >=2")
    t0=time.time()
    scaler=StandardScaler()
    rows=0
    # Pass 1: exact scaler statistics over the entire corpus.
    for b in batches(input_path,batch_rows):
        scaler.partial_fit(matrix(b)); rows+=b.num_rows
    if rows<n_clusters*3: raise ValueError("Too few rows for configured cluster count")
    model=MiniBatchKMeans(n_clusters=n_clusters,random_state=27,batch_size=max(batch_rows,1024),n_init=3,reassignment_ratio=0.01)
    # Pass 2: update clustering from every chunk.
    fit_rows=0
    for b in batches(input_path,batch_rows):
        model.partial_fit(scaler.transform(matrix(b))); fit_rows+=b.num_rows
    if fit_rows!=rows: raise RuntimeError(f"Cluster fitting rows {fit_rows} != scaler rows {rows}")
    out_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=out_path.with_suffix(out_path.suffix+'.part');tmp.unlink(missing_ok=True)
    writer=None; scored=0; score_sum=0.0; score_sq=0.0; min_score=float('inf');max_score=float('-inf');cluster_counts=Counter()
    try:
        # Pass 3: score every event and persist every score.
        for b in batches(input_path,batch_rows):
            x=scaler.transform(matrix(b))
            labels=model.predict(x).astype(np.int16)
            distances=model.transform(x)
            score=distances.min(axis=1).astype(np.float32)
            event_ids=b.column(b.schema.get_field_index('event_row_id')).to_numpy(zero_copy_only=False).astype(np.int64)
            jet_counts=b.column(b.schema.get_field_index('n_jets')).to_numpy(zero_copy_only=False).astype(np.int16)
            cluster_counts.update(int(k) for k in labels)
            out_table=pa.table({"event_row_id":event_ids,"n_jets":jet_counts,"cluster_id":labels,"centroid_distance":score})
            if writer is None: writer=pq.ParquetWriter(tmp,out_table.schema,compression='snappy')
            writer.write_table(out_table,row_group_size=batch_rows)
            scored+=len(score);score_sum+=float(score.sum());score_sq+=float(np.dot(score,score));min_score=min(min_score,float(score.min()));max_score=max(max_score,float(score.max()))
        if writer is not None: writer.close();writer=None
        tmp.replace(out_path)
    except Exception:
        if writer is not None: writer.close()
        tmp.unlink(missing_ok=True);raise
    if scored!=rows: raise RuntimeError(f"Scored rows {scored} != source rows {rows}")
    manifest={
        "status":"COMPLETED_FULL_CORPUS_UNSUPERVISED_CLUSTERING","input":str(input_path.resolve()),"output":str(out_path.resolve()),
        "rows_scaled":rows,"rows_used_for_cluster_updates":fit_rows,"rows_scored":scored,"rows_filtered":0,"rows_sampled_by_pipeline":0,
        "features":FEATURES,"clusters":n_clusters,"random_state":27,"cluster_counts":{str(int(k)):int(v) for k,v in sorted(cluster_counts.items())},
        "score":"Euclidean distance to nearest standardized feature-space centroid; exploratory distance, not calibrated anomaly probability",
        "last_fit_batch_inertia":float(model.inertia_),"iterations":int(model.n_steps_),"score_min":min_score,"score_max":max_score,"score_mean":score_sum/max(scored,1),
        "score_std_population":float(max(0.0,score_sq/max(scored,1)-(score_sum/max(scored,1))**2)**0.5),
        "runtime_seconds":round(time.time()-t0,3),
        "limits":["This model finds feature-space outliers relative to fitted clusters; outlier status does not establish new physics.","The input record contains a simulated Standard Model mixture and no per-event hidden-signal truth labels; supervised detection efficiency cannot be measured.","All source events enter scaler fitting, repeated minibatch updates and scoring; mini-batch clustering is the algorithm, not dataset truncation."],
    }
    (out_path.parent/'cluster_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2));return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,default=DEFAULT_INPUT);ap.add_argument('--out',type=Path,default=DEFAULT_OUT);ap.add_argument('--batch-rows',type=int,default=25000);ap.add_argument('--clusters',type=int,default=8)
    a=ap.parse_args();run(a.input,a.out,a.batch_rows,a.clusters)
if __name__=='__main__':main()
