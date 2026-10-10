-- Run after Spark writes outputs/spark/events_by_n_jets.
-- LOCATION must map to the same shared path in the Hive execution environment.
CREATE DATABASE IF NOT EXISTS ca3_40mhz;
USE ca3_40mhz;
CREATE EXTERNAL TABLE IF NOT EXISTS events (
  event_row_id BIGINT,
  met_pt FLOAT,
  met_phi FLOAT,
  n_electrons SMALLINT,
  n_muons SMALLINT,
  n_objects SMALLINT,
  leading_electron_pt FLOAT,
  leading_muon_pt FLOAT,
  leading_jet_pt FLOAT,
  ht_jets FLOAT,
  sum_lepton_pt FLOAT,
  max_abs_eta FLOAT,
  has_nonfinite BOOLEAN,
  invalid_type_count SMALLINT,
  negative_pt_count SMALLINT,
  inconsistent_padding_count SMALLINT
)
PARTITIONED BY (n_jets SMALLINT)
STORED AS PARQUET
LOCATION '/workspace/outputs/spark/events_by_n_jets';
MSCK REPAIR TABLE events;
