# Actual Hadoop Streaming MapReduce job

The core Docker pipeline demonstrates key-value aggregation through Spark RDD `map` / `reduceByKey`. These mapper/reducer programs provide the same aggregation as a true Hadoop Streaming job when a Hadoop installation with HDFS is available.

## Input contract

`make pig-export` writes `outputs/pig/events.tsv`: a five-column projection for **every event row**. Column order: `event_row_id`, `n_jets`, `met_pt`, `ht_jets`, `sum_lepton_pt`. No header. No row filtering. File can be large; preserve complete input.

## Run against Hadoop Streaming

Set `HADOOP_HOME` to your Hadoop installation. Use a writable HDFS path. Example:

```bash
make all
make pig-export
hdfs dfs -mkdir -p /ca3_40mhz/input
hdfs dfs -put -f outputs/pig/events.tsv /ca3_40mhz/input/events.tsv
STREAMING_JAR=$(find "$HADOOP_HOME/share/hadoop/tools/lib" -name 'hadoop-streaming-*.jar' | head -n 1)
hadoop jar "$STREAMING_JAR" \
  -D mapreduce.job.reduces=1 \
  -files hadoop/mapper.py,hadoop/reducer.py \
  -mapper 'python3 mapper.py' \
  -reducer 'python3 reducer.py' \
  -input /ca3_40mhz/input/events.tsv \
  -output /ca3_40mhz/output/jet_summary
hdfs dfs -cat /ca3_40mhz/output/part-*
```

Output fields: `n_jets`, `event_count`, `mean_ht_jets`, `mean_met_pt`, `mean_sum_lepton_pt`. Mapper validates fields and finite numeric values; malformed input fails the task. Reducer expects Hadoop's key sort, aggregates by key, emits one row per jet count. Sum of output `event_count` must equal ETL row count.

The supplied Compose stack has no Namenode/DataNode cluster. This job requires separate Hadoop services or an existing cluster. Do not describe a Spark local execution as an HDFS MapReduce run.
