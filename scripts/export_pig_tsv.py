#!/usr/bin/env python3
"""Export all Parquet event rows as a small-column TSV projection for Pig Latin."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pyarrow.dataset as ds
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INPUT=ROOT/"data/processed/events.parquet"
DEFAULT_OUT=ROOT/"outputs/pig/events.tsv"
COLS=["event_row_id","n_jets","met_pt","ht_jets","sum_lepton_pt"]

def run(src:Path,out:Path,batch_rows:int=25000):
    if not src.exists(): raise FileNotFoundError(f"Input {src} missing; run ETL first")
    out.parent.mkdir(parents=True,exist_ok=True)
    part=out.with_suffix(out.suffix+'.part');part.unlink(missing_ok=True)
    ds_obj=ds.dataset(src,format="parquet")
    written=0
    try:
        with part.open("w",encoding="utf-8",newline="") as f:
            for batch in ds_obj.to_batches(columns=COLS,batch_size=batch_rows):
                frame=batch.to_pandas()
                frame.to_csv(f,sep="\t",header=False,index=False,lineterminator="\n",float_format="%.7g")
                written+=len(frame)
        part.replace(out)
    except Exception:
        part.unlink(missing_ok=True);raise
    report={"status":"COMPLETED_FULL_ROW_PIG_EXPORT","input":str(src.resolve()),"output":str(out.resolve()),"rows_written":written,"rows_filtered":0,"rows_sampled":0,"columns":COLS,"bytes":out.stat().st_size,"scope":"Five-column projection of every event row; use for Pig aggregation."}
    (out.parent/"pig_export_manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2));return report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,default=DEFAULT_INPUT);ap.add_argument('--out',type=Path,default=DEFAULT_OUT);ap.add_argument('--batch-rows',type=int,default=25000);a=ap.parse_args();run(a.input,a.out,a.batch_rows)
if __name__=='__main__':main()
