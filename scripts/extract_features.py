#!/usr/bin/env python3
"""Convert every HDF5 event into typed event-level Parquet features, chunkwise."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import h5py
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_FILE=ROOT/"data/raw/background_for_training.h5"
DEFAULT_OUT=ROOT/"data/processed/events.parquet"
EXPECTED_SHAPE=(19,4)

COLUMNS=[
    "event_row_id","met_pt","met_phi","n_electrons","n_muons","n_jets","n_objects",
    "leading_electron_pt","leading_muon_pt","leading_jet_pt","ht_jets","sum_lepton_pt","max_abs_eta",
    "has_nonfinite","invalid_type_count","negative_pt_count","inconsistent_padding_count"
]


def text_values(value):
    if isinstance(value,bytes): return value.decode("utf-8",errors="replace")
    if isinstance(value,np.ndarray): return [text_values(x) for x in value.tolist()]
    if isinstance(value,np.generic): return text_values(value.item())
    if isinstance(value,list): return [text_values(x) for x in value]
    return value


def validate_metadata(h5):
    if "Particles" not in h5: raise ValueError("HDF5 key /Particles missing")
    ds=h5["Particles"]
    if ds.ndim != 3 or tuple(ds.shape[1:]) != EXPECTED_SHAPE:
        raise ValueError(f"Unexpected schema {ds.shape}; expected (N,19,4)")
    names=text_values(h5["Particles_Names"][()]) if "Particles_Names" in h5 else None
    classes=text_values(h5["Particles_Classes"][()]) if "Particles_Classes" in h5 else None
    if names is None or classes is None:
        raise ValueError("Particles_Names or Particles_Classes missing; cannot verify documented fields")
    # Dataset publication documents features ordered pT, eta, phi, followed by type code.
    names_flat=names if isinstance(names,list) else [names]
    normalized=[str(x).lower().replace("_", "").replace(" ", "") for x in names_flat]
    joined=" ".join(normalized)
    if not any(k in joined for k in ("pt","p_t","transversemomentum")):
        raise ValueError(f"Cannot validate pT in Particles_Names metadata: {names!r}")
    return ds, names, classes


def derive_chunk(arr: np.ndarray, start_index: int) -> pd.DataFrame:
    """Return event-level variables for every row; source rows never filtered."""
    if arr.ndim != 3 or arr.shape[1:] != EXPECTED_SHAPE:
        raise ValueError(f"Bad tensor chunk shape {arr.shape}")
    pt0=arr[:,:,0]
    eta0=arr[:,:,1]
    phi0=arr[:,:,2]
    type_raw=arr[:,:,3]
    finite=np.isfinite(arr)
    finite_type=np.isfinite(type_raw)
    rounded_type=np.rint(np.where(finite_type,type_raw,0.0))
    integral_type=finite_type & (np.abs(type_raw-rounded_type)<=1e-4)
    known_type=integral_type & np.isin(rounded_type,[0,1,2,3,4])
    type_safe=np.where(known_type,rounded_type,-99).astype(np.int16)
    occupied=np.isin(type_safe,[1,2,3,4])
    electron=type_safe==2
    muon=type_safe==3
    jet=type_safe==4
    leptons=electron|muon
    pt=np.nan_to_num(pt0,nan=0.0,posinf=0.0,neginf=0.0)
    eta=np.nan_to_num(eta0,nan=0.0,posinf=0.0,neginf=0.0)
    phi=np.nan_to_num(phi0,nan=0.0,posinf=0.0,neginf=0.0)
    def masked_max(values, mask):
        result=np.max(np.where(mask,values,-np.inf),axis=1)
        return np.where(np.isfinite(result),result,0.0).astype(np.float32)
    pte=masked_max(pt,electron)
    ptm=masked_max(pt,muon)
    ptj=masked_max(pt,jet)
    n_e=electron.sum(axis=1).astype(np.int16)
    n_mu=muon.sum(axis=1).astype(np.int16)
    n_j=jet.sum(axis=1).astype(np.int16)
    event_count=arr.shape[0]
    empty=type_safe==0
    nonzero_kin=np.any(np.nan_to_num(arr[:,:,:3],nan=0,posinf=0,neginf=0)!=0,axis=2)
    return pd.DataFrame({
        "event_row_id":np.arange(start_index,start_index+event_count,dtype=np.int64),
        "met_pt":pt[:,0].astype(np.float32),
        "met_phi":phi[:,0].astype(np.float32),
        "n_electrons":n_e,
        "n_muons":n_mu,
        "n_jets":n_j,
        "n_objects":(electron|muon|jet).sum(axis=1).astype(np.int16),
        "leading_electron_pt":pte,
        "leading_muon_pt":ptm,
        "leading_jet_pt":ptj,
        "ht_jets":np.where(jet,pt,0).sum(axis=1,dtype=np.float64).astype(np.float32),
        "sum_lepton_pt":np.where(leptons,pt,0).sum(axis=1,dtype=np.float64).astype(np.float32),
        "max_abs_eta":np.where(leptons|jet,np.abs(eta),0).max(axis=1).astype(np.float32),
        "has_nonfinite":(~finite).any(axis=(1,2)),
        "invalid_type_count":(~known_type).sum(axis=1).astype(np.int16),
        "negative_pt_count":((pt0<0)&occupied).sum(axis=1).astype(np.int16),
        "inconsistent_padding_count":(empty&nonzero_kin).sum(axis=1).astype(np.int16),
    },columns=COLUMNS)


def run(file_path:Path,out_path:Path,chunk_rows:int,compression:str="snappy"):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if not file_path.is_file(): raise FileNotFoundError(f"Missing {file_path}; run download first")
    out_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=out_path.with_suffix(out_path.suffix+".part")
    tmp.unlink(missing_ok=True)
    total=0; writer=None
    try:
        with h5py.File(file_path,"r") as h5:
            ds,names,classes=validate_metadata(h5)
            for start in range(0,ds.shape[0],chunk_rows):
                stop=min(ds.shape[0],start+chunk_rows)
                chunk=np.asarray(ds[start:stop])
                frame=derive_chunk(chunk,start)
                schema=pa.schema([
                    pa.field("event_row_id",pa.int64()), pa.field("met_pt",pa.float32()), pa.field("met_phi",pa.float32()),
                    pa.field("n_electrons",pa.int16()), pa.field("n_muons",pa.int16()), pa.field("n_jets",pa.int16()), pa.field("n_objects",pa.int16()),
                    pa.field("leading_electron_pt",pa.float32()), pa.field("leading_muon_pt",pa.float32()), pa.field("leading_jet_pt",pa.float32()),
                    pa.field("ht_jets",pa.float32()), pa.field("sum_lepton_pt",pa.float32()), pa.field("max_abs_eta",pa.float32()),
                    pa.field("has_nonfinite",pa.bool_()), pa.field("invalid_type_count",pa.int16()), pa.field("negative_pt_count",pa.int16()),
                    pa.field("inconsistent_padding_count",pa.int16()),
                ])
                table=pa.Table.from_pandas(frame,schema=schema,preserve_index=False,safe=True)
                if writer is None:
                    writer=pq.ParquetWriter(tmp,schema,compression=compression,use_dictionary=True,write_statistics=True)
                writer.write_table(table,row_group_size=chunk_rows)
                total += len(frame)
                if total and total//250000 != (total-len(frame))//250000:
                    print(f"Transformed {total:,}/{ds.shape[0]:,} events",flush=True)
        if writer is None: raise RuntimeError("Dataset has zero event rows")
        writer.close(); writer=None
        os.replace(tmp,out_path)
    except Exception:
        if writer is not None: writer.close()
        tmp.unlink(missing_ok=True)
        raise
    pf=pq.ParquetFile(out_path)
    if total != pf.metadata.num_rows: raise RuntimeError(f"Output rows {pf.metadata.num_rows} != input rows {total}")
    manifest={
        "status":"COMPLETED_FULL_FILE_ETL",
        "input_file":str(file_path.resolve()),"output_parquet":str(out_path.resolve()),
        "input_rows_read":int(total),"output_rows_written":int(pf.metadata.num_rows),
        "rows_filtered":0,"rows_sampled":0,"rows_dropped":0,
        "chunk_rows":chunk_rows,"parquet_bytes":out_path.stat().st_size,
        "parquet_MB_decimal":round(out_path.stat().st_size/1e6,3),"compression":compression,
        "row_groups":pf.metadata.num_row_groups,"columns":COLUMNS,
        "metadata":{"Particles_Names":names,"Particles_Classes":classes},
        "feature_definitions":{
            "event_row_id":"zero-based row ordinal in source file; not a physical detector event ID",
            "met_pt":"pT-like magnitude at fixed slot 0, validated against metadata by schema gate",
            "n_electrons/n_muons/n_jets":"counts of type codes 2/3/4 across all 19 slots",
            "leading_*_pt":"maximum pT among occupied slots of given type",
            "ht_jets":"sum of pT across slots with type code 4",
            "sum_lepton_pt":"sum of pT across electron and muon slots",
            "max_abs_eta":"maximum absolute eta among electron, muon, jet slots; 0 when no such slots",
            "has_nonfinite/invalid_type_count/negative_pt_count/inconsistent_padding_count":"per-event data-quality flags/counters; source values remain unchanged",
        },
        "caveat":"Feature extraction replaces nonfinite values with zero only in derived aggregate calculations and retains per-event quality indicators. Raw source file is unchanged.",
    }
    (out_path.parent/"etl_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({k:manifest[k] for k in ("status","input_rows_read","output_rows_written","rows_filtered","rows_sampled","parquet_MB_decimal","row_groups")},indent=2))
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file",type=Path,default=DEFAULT_FILE)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    ap.add_argument("--chunk-rows",type=int,default=int(__import__('os').environ.get("ETL_CHUNK_ROWS","25000")))
    a=ap.parse_args()
    if a.chunk_rows<1: ap.error("--chunk-rows must be positive")
    run(a.file,a.out,a.chunk_rows)

if __name__=="__main__": main()
