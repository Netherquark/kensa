#!/usr/bin/env python3
"""Full-file HDF5 inventory and chunked data-quality audit. No row sampling."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from collections import Counter
from pathlib import Path
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "data/raw/background_for_training.h5"
DEFAULT_OUT = ROOT / "audit"
PT_EDGES = [0, 1, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 1000, 5000, 1_000_000]
TYPE_NAMES = {0: "padding", 1: "MET", 2: "electron", 3: "muon", 4: "jet"}


def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        return [decode(x) for x in value.tolist()]
    if isinstance(value, np.generic):
        return decode(value.item())
    if isinstance(value, list):
        return [decode(x) for x in value]
    return value


def checksum(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as src:
        for block in iter(lambda: src.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(file_path: Path, outdir: Path, chunk_rows: int) -> dict:
    if not file_path.is_file():
        raise FileNotFoundError(f"Dataset missing: {file_path}. Run `make download` first.")
    outdir.mkdir(parents=True, exist_ok=True)
    inv = []
    with h5py.File(file_path, "r") as h5:
        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                row = {
                    "key": "/" + name,
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "chunks": list(obj.chunks) if obj.chunks else None,
                    "compression": obj.compression,
                    "compression_opts": obj.compression_opts,
                    "size_bytes": int(obj.size * obj.dtype.itemsize),
                    "attrs": {str(k): decode(v) for k, v in obj.attrs.items()},
                }
                if obj.size <= 100:
                    row["small_values"] = decode(obj[()])
                inv.append(row)
        h5.visititems(visit)
        for req in ("Particles", "Particles_Names", "Particles_Classes"):
            if req not in h5:
                raise ValueError(f"Required HDF5 key /{req} missing. Actual keys: {list(h5.keys())}")
        ds = h5["Particles"]
        if ds.ndim != 3 or ds.shape[1:] != (19, 4):
            raise ValueError(f"Unexpected Particles shape {ds.shape}; expected (N, 19, 4). No automatic reshape attempted.")
        n, nslots, nfeatures = ds.shape
        names = decode(h5["Particles_Names"][()])
        classes = decode(h5["Particles_Classes"][()])
        slot_counts = Counter()
        mult_hist = {k: Counter() for k in ("electron", "muon", "jet")}
        pt_hist = {TYPE_NAMES[k]: np.zeros(len(PT_EDGES)-1, dtype=np.int64) for k in (1,2,3,4)}
        pt_under = Counter(); pt_over = Counter()
        finite_count = nan_count = posinf_count = neginf_count = 0
        negative_pt = invalid_type_code = noninteger_type_code = bad_padding = position_mismatch = 0
        phi_outside = 0
        padded_slots = occupied_slots = events_with_padding = 0
        schema_nonfinite_examples = []
        expected_slot_type = np.array([1] + [2]*4 + [3]*4 + [4]*10, dtype=np.int8)
        for start in range(0, n, chunk_rows):
            stop = min(n, start + chunk_rows)
            arr = np.asarray(ds[start:stop])
            xyz = arr[:, :, :3]
            typf = arr[:, :, 3]
            finite_mask = np.isfinite(arr)
            finite_count += int(finite_mask.sum())
            nan_count += int(np.isnan(arr).sum())
            posinf_count += int(np.isposinf(arr).sum())
            neginf_count += int(np.isneginf(arr).sum())
            if not finite_mask.all() and len(schema_nonfinite_examples) < 5:
                bad = np.argwhere(~finite_mask)
                for row in bad[:5-len(schema_nonfinite_examples)]:
                    schema_nonfinite_examples.append({"event_row": int(start + row[0]), "slot": int(row[1]), "field": int(row[2])})
            finite_type = np.isfinite(typf)
            rounded_type = np.rint(np.where(finite_type, typf, 0.0))
            integral_type = finite_type & (np.abs(typf-rounded_type) <= 1e-4)
            known_type = integral_type & np.isin(rounded_type, [0,1,2,3,4])
            noninteger_type_code += int(np.count_nonzero(finite_type & ~integral_type))
            invalid_type_code += int((~known_type).sum())
            # Convert only validated vocabulary values. Arbitrary large/corrupt floats cannot wrap to a valid int16 code.
            safe_type = np.where(known_type, rounded_type, -99).astype(np.int16)
            empty = safe_type == 0
            occupied = np.isin(safe_type, [1,2,3,4])
            padded_slots += int(empty.sum())
            occupied_slots += int(occupied.sum())
            events_with_padding += int(np.any(empty, axis=1).sum())
            bad_padding += int(np.count_nonzero(empty & np.any(np.nan_to_num(xyz, nan=0.0, posinf=0.0, neginf=0.0) != 0, axis=2)))
            position_mismatch += int(np.count_nonzero(occupied & (safe_type != expected_slot_type[None, :])))
            pt = xyz[:,:,0]
            eta = xyz[:,:,1]
            phi = xyz[:,:,2]
            negative_pt += int(np.count_nonzero((pt < 0) & occupied))
            phi_outside += int(np.count_nonzero((np.abs(phi) > math.pi + 1e-3) & occupied & np.isfinite(phi)))
            for code, label in TYPE_NAMES.items():
                mask = safe_type == code
                slot_counts[label] += int(mask.sum())
                if code == 0:
                    continue
                vals = pt[mask]
                vals = vals[np.isfinite(vals)]
                if vals.size:
                    hist, _ = np.histogram(vals, bins=np.asarray(PT_EDGES, dtype=float))
                    pt_hist[label] += hist.astype(np.int64)
                    pt_under[label] += int((vals < PT_EDGES[0]).sum())
                    pt_over[label] += int((vals >= PT_EDGES[-1]).sum())
            for code, label in ((2,"electron"),(3,"muon"),(4,"jet")):
                per_event = np.count_nonzero(safe_type == code, axis=1)
                for m, c in zip(*np.unique(per_event, return_counts=True)):
                    mult_hist[label][int(m)] += int(c)

        file_stats = file_path.stat()
        report = {
            "status": "COMPLETED_FULL_FILE_SCAN",
            "file": {"path": str(file_path.resolve()), "bytes": file_stats.st_size,
                     "MB_decimal": round(file_stats.st_size/1e6, 3), "MiB": round(file_stats.st_size/(1024**2), 3),
                     "md5": checksum(file_path, "md5"), "sha256": checksum(file_path, "sha256")},
            "schema": {"datasets": inv, "Particles_shape": list(ds.shape), "Particles_dtype": str(ds.dtype),
                       "Particles_Names": names, "Particles_Classes": classes,
                       "documented_feature_layout": ["pT", "eta", "phi", "particle_type_code"],
                       "documented_type_codes": {str(k):v for k,v in TYPE_NAMES.items()}},
            "scan": {"rows_read": int(n), "chunk_rows": int(chunk_rows), "event_rows_skipped": 0,
                     "slots_scanned": int(n*nslots), "scalar_values_scanned": int(n*nslots*nfeatures)},
            "quality": {
                "finite_scalar_count": finite_count, "nan_count": nan_count, "positive_infinity_count": posinf_count,
                "negative_infinity_count": neginf_count, "invalid_type_code_count": invalid_type_code,
                "noninteger_type_code_count": noninteger_type_code, "negative_pT_count_occupied_slots": negative_pt,
                "phi_outside_minus_pi_plus_pi_count_occupied_slots": phi_outside,
                "empty_slots_with_nonzero_kinematics_count": bad_padding,
                "valid_type_code_in_wrong_slot_count": position_mismatch,
                "occupied_slots": occupied_slots, "zero_padded_slots": padded_slots,
                "zero_padding_fraction": padded_slots/max(1,n*nslots),
                "events_with_any_padding": events_with_padding,
                "fraction_events_with_any_padding": events_with_padding/max(1,n),
                "nonfinite_coordinate_examples": schema_nonfinite_examples,
                "counts_by_particle_type": {k:int(v) for k,v in slot_counts.items()},
                "particle_type_slot_fractions": {k:round(int(v)/max(1,n*nslots),8) for k,v in slot_counts.items()},
                "pt_histogram_edges_GeV_as_documented": PT_EDGES,
                "pt_histogram_counts_by_type": {k:[int(x) for x in v] for k,v in pt_hist.items()},
                "pt_below_histogram_range_by_type": {k:int(v) for k,v in pt_under.items()},
                "pt_at_or_above_histogram_max_by_type": {k:int(v) for k,v in pt_over.items()},
                "multiplicity_distribution_by_event": {k:{str(i):int(c) for i,c in sorted(v.items())} for k,v in mult_hist.items()},
            },
            "interpretation": [
                "All N event rows were scanned in sequential chunks; no rows were sampled, dropped, or filtered.",
                "Particle type code 0 represents inclusive zero padding in the published schema; padded zeros are not measured particles.",
                "Particles has four values per slot: pT, eta, phi, particle type code. Validate names/classes above before interpreting units.",
                "Process-level signal/background labels are not documented as per-event labels in the main training file; no classification accuracy can be measured from this file alone.",
                "The 40 MHz phrase describes the real-time trigger use case; this file is a finite simulated offline training corpus, not a streaming telemetry capture."
            ],
        }
    (outdir / "raw_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (outdir / "hdf5_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        cols = ["key","shape","dtype","chunks","compression","compression_opts","size_bytes","attrs","small_values"]
        w=csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for item in inv:
            w.writerow({k: json.dumps(item.get(k), ensure_ascii=False) if isinstance(item.get(k),(dict,list)) else item.get(k) for k in cols})
    with (outdir / "quality_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["metric","value"])
        for k,v in report["quality"].items():
            if not isinstance(v,(dict,list)): w.writerow([k,v])
    print(json.dumps({"status":report["status"],"rows_scanned":n,"file_MB":report["file"]["MB_decimal"],"quality":{k:v for k,v in report["quality"].items() if not isinstance(v,(dict,list))}},indent=2))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file",type=Path,default=DEFAULT_FILE)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    ap.add_argument("--chunk-rows",type=int,default=25000)
    a=ap.parse_args()
    if a.chunk_rows < 1: ap.error("--chunk-rows must be positive")
    run(a.file,a.out,a.chunk_rows)

if __name__ == "__main__": main()
