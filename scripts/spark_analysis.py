#!/usr/bin/env python3
"""Run Spark SQL reports plus full-corpus key/value map-reduce aggregation."""
from __future__ import annotations
import argparse, csv, json, os, re, time
from pathlib import Path
from pyspark.sql import SparkSession

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_FEATURES=ROOT/"data/processed/events.parquet"
DEFAULT_OUT=ROOT/"outputs/spark"
SQL_DIR=ROOT/"sql"


def load_statements(path:Path):
    buf=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped=line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
    text="\n".join(buf)
    return [x.strip() for x in text.split(";") if x.strip()]


def run(features:Path,outdir:Path,master:str="local[6]",shuffle_partitions:int=12):
    if not features.exists(): raise FileNotFoundError(f"Parquet feature table missing: {features}. Run ETL first.")
    outdir.mkdir(parents=True,exist_ok=True)
    start=time.time()
    spark=(SparkSession.builder.appName("CA3-40MHz-LHC-Event-Analytics")
           .master(master)
           .config("spark.sql.shuffle.partitions",str(shuffle_partitions))
           .config("spark.sql.adaptive.enabled","true")
           .config("spark.sql.parquet.mergeSchema","false")
           .config("spark.sql.execution.arrow.pyspark.enabled","true")
           .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        df=spark.read.parquet(str(features))
        df.createOrReplaceTempView("events")
        total=df.count()
        if total == 0: raise RuntimeError("Parquet feature table has zero events")
        # Partition the complete corpus for query-pruning demonstrations; all rows written.
        part_path=outdir/"events_by_n_jets"
        (df.repartition(shuffle_partitions,"n_jets").write.mode("overwrite")
            .partitionBy("n_jets").option("compression","snappy").parquet(str(part_path)))
        # Read back persisted partitioned data and prove row preservation.
        part_df=spark.read.parquet(str(part_path))
        part_df.createOrReplaceTempView("events")
        partitioned_count=part_df.count()
        if partitioned_count != total:
            raise RuntimeError(f"Partitioning changed row count: {partitioned_count} != {total}")
        sql_out=outdir/"sql_results"
        sql_out.mkdir(parents=True,exist_ok=True)
        sql_manifest=[]
        for query_path in sorted(SQL_DIR.glob("*.sql")):
            for i,statement in enumerate(load_statements(query_path),start=1):
                result=spark.sql(statement)
                qname=query_path.stem if i==1 else f"{query_path.stem}_{i}"
                destination=sql_out/qname
                result.write.mode("overwrite").option("header","true").option("encoding","UTF-8").csv(str(destination))
                rows=result.count()
                # Compact console preview; full result remains in CSV output directory.
                print(f"\n=== {query_path.name} / result rows={rows} ===")
                result.show(12,truncate=120)
                sql_manifest.append({"query_file":query_path.name,"result_name":qname,"result_rows":int(rows),"output_path":str(destination.resolve())})
        # MapReduce-style aggregation on every event. Mapper emits key=jet multiplicity and sums.
        mapped=(part_df.select("n_jets","ht_jets","met_pt","sum_lepton_pt").rdd
            .map(lambda r: (int(r[0]), (1, float(r[1] or 0.0), float(r[2] or 0.0), float(r[3] or 0.0))) )
            .reduceByKey(lambda a,b:(a[0]+b[0],a[1]+b[1],a[2]+b[2],a[3]+b[3]),numPartitions=shuffle_partitions))
        agg=sorted(mapped.collect(),key=lambda x:x[0])
        mr_rows=[]
        for key,(n,sum_ht,sum_met,sum_lepton_pt) in agg:
            mr_rows.append({"n_jets":int(key),"event_count":int(n),"mean_ht_jets":sum_ht/n,"mean_met_pt":sum_met/n,"mean_sum_lepton_pt":sum_lepton_pt/n})
        mr_path=outdir/"mapreduce_jet_multiplicity.json"
        mr_path.write_text(json.dumps({"method":"RDD map -> reduceByKey full-corpus aggregation","events_processed":sum(r["event_count"] for r in mr_rows),"rows":mr_rows},indent=2),encoding="utf-8")
        if sum(r["event_count"] for r in mr_rows) != total:
            raise RuntimeError("MapReduce-style aggregation count does not match input count")
        manifest={
            "status":"COMPLETED_SPARK_ANALYTICS",
            "input_feature_table":str(features.resolve()),
            "input_rows":int(total),"partitioned_parquet_rows":int(partitioned_count),
            "partition_column":"n_jets","output_partitioned_parquet":str(part_path.resolve()),
            "sql_queries_executed":sql_manifest,
            "mapreduce_style_aggregation":{"rows_processed":int(total),"key":"n_jets","reducers":"reduceByKey","output":str(mr_path.resolve())},
            "spark_version":spark.version,"master":master,"shuffle_partitions":shuffle_partitions,
            "duration_seconds":round(time.time()-start,3),
            "note":"HiveQL-compatible SQL files are executed by Spark SQL. This does not claim a separate HiveServer2 engine or a multi-node Hadoop cluster.",
        }
        (outdir/"spark_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        print("\nSPARK RUN SUMMARY\n"+json.dumps({k:v for k,v in manifest.items() if k!="sql_queries_executed"},indent=2))
        return manifest
    finally:
        spark.stop()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features",type=Path,default=DEFAULT_FEATURES)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    ap.add_argument("--master",default="local[6]")
    ap.add_argument("--shuffle-partitions",type=int,default=int(os.environ.get("SPARK_SHUFFLE_PARTITIONS","12")))
    a=ap.parse_args(); run(a.features,a.out,a.master,a.shuffle_partitions)

if __name__=="__main__": main()
