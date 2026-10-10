#!/usr/bin/env python3
"""Hadoop Streaming mapper. Input TSV: event_row_id, n_jets, met_pt, ht_jets, sum_lepton_pt."""
import csv
import math
import sys

for line_no, line in enumerate(sys.stdin, start=1):
    row = next(csv.reader([line.rstrip("\n")], delimiter="\t"))
    if len(row) != 5:
        raise ValueError(f"line {line_no}: expected 5 tab-separated fields; got {len(row)}")
    try:
        int(row[0])
        n_jets = int(row[1])
        met_pt, ht_jets, sum_lepton_pt = map(float, row[2:5])
    except ValueError as exc:
        raise ValueError(f"line {line_no}: invalid numeric field") from exc
    if n_jets < 0 or not all(math.isfinite(v) for v in (met_pt, ht_jets, sum_lepton_pt)):
        raise ValueError(f"line {line_no}: invalid key or nonfinite feature")
    # Key = jet multiplicity. Value = count, sum(HT), sum(MET), sum(lepton scalar pT).
    print(f"{n_jets}\t1\t{ht_jets:.9g}\t{met_pt:.9g}\t{sum_lepton_pt:.9g}")
