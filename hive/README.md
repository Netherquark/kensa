# Native Hive option

The core project uses Spark SQL in Docker. For a native Hive execution, make sure a Hive installation can access the shared directory containing `outputs/spark/events_by_n_jets`.

1. Run core pipeline through `make all`.
2. Put the repository at `/workspace` or update `LOCATION` in `register_events.hql` to the path visible from Hive.
3. Run `hive -f hive/register_events.hql`.
4. Set database `ca3_40mhz`; run `sql/*.sql` in lexical order. All seven queries operate on the registered `events` table.

Native Hive deployment, metastore, HDFS permissions and cluster services are external to the primary Docker image. Record the selected Hive version and execution mode if used in CA3.
