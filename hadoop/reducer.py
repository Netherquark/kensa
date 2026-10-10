#!/usr/bin/env python3
"""Hadoop Streaming reducer; expects mapper values sorted by integer jet-count key."""
import math
import sys

current_key = None
count = 0
sum_ht = 0.0
sum_met = 0.0
sum_lepton = 0.0


def emit(key, n, ht, met, lepton):
    if key is None:
        return
    print(f"{key}\t{n}\t{ht/n:.9g}\t{met/n:.9g}\t{lepton/n:.9g}")

for line_no, line in enumerate(sys.stdin, start=1):
    fields = line.rstrip("\n").split("\t")
    if len(fields) != 5:
        raise ValueError(f"line {line_no}: expected 5 mapper fields; got {len(fields)}")
    key = int(fields[0])
    n = int(fields[1])
    ht, met, lepton = map(float, fields[2:5])
    if n < 0 or not all(math.isfinite(v) for v in (ht, met, lepton)):
        raise ValueError(f"line {line_no}: invalid mapper value")
    if current_key is not None and key != current_key:
        emit(current_key, count, sum_ht, sum_met, sum_lepton)
        count = 0; sum_ht = 0.0; sum_met = 0.0; sum_lepton = 0.0
    current_key = key
    count += n
    sum_ht += ht
    sum_met += met
    sum_lepton += lepton
emit(current_key, count, sum_ht, sum_met, sum_lepton)
