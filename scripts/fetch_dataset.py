#!/usr/bin/env python3
"""Fetch complete Zenodo 40 MHz SM training file and verify repository checksum."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
from urllib.request import Request, urlopen

RECORD_ID = "5046428"
FILENAME = "background_for_training.h5"
EXPECTED_MD5 = "08cb4801229f9d480567f8d3f5cac134"
EXPECTED_EVENTS = 4_000_000
USER_AGENT = "SIT-BDA-CA3-40MHz/1.0 (reproducible research project)"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/raw"


def sha(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--record-id", default=RECORD_ID)
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    target = out / FILENAME
    try:
        metadata = get_json(f"https://zenodo.org/api/records/{args.record_id}")
        matched = [f for f in metadata.get("files", [])
                   if f.get("key") == FILENAME and
                   str(f.get("checksum", "")).lower().replace("md5:", "") == EXPECTED_MD5]
        if len(matched) != 1:
            raise RuntimeError(
                f"Zenodo record {args.record_id} did not contain exactly one {FILENAME} "
                f"with expected MD5 {EXPECTED_MD5}. Check record version/metadata."
            )
        item = matched[0]
        expected_size = int(item.get("size", 0))
        url = f"https://zenodo.org/records/{args.record_id}/files/{FILENAME}?download=1"
        if target.exists():
            got = sha(target, "md5")
            if got != EXPECTED_MD5:
                raise RuntimeError(f"Existing {target} checksum mismatch: {got}; refusing overwrite.")
            if expected_size and target.stat().st_size != expected_size:
                raise RuntimeError(f"Existing {target} byte count {target.stat().st_size} != Zenodo API size {expected_size}.")
            status = "existing file size- and checksum-verified"
        else:
            fd, tmp_name = tempfile.mkstemp(prefix=FILENAME + ".", suffix=".part", dir=out)
            os.close(fd)
            tmp = Path(tmp_name)
            try:
                req = Request(url, headers={"User-Agent": USER_AGENT})
                downloaded = 0
                with urlopen(req, timeout=180) as response, tmp.open("wb") as dest:
                    while True:
                        block = response.read(4 * 1024 * 1024)
                        if not block:
                            break
                        dest.write(block)
                        downloaded += len(block)
                        if downloaded and downloaded // (128 * 1024 * 1024) != (downloaded-len(block)) // (128 * 1024 * 1024):
                            print(f"Downloaded {downloaded/1e6:.0f} MB", flush=True)
                got = sha(tmp, "md5")
                if got != EXPECTED_MD5:
                    raise RuntimeError(f"MD5 mismatch: downloaded={got}, Zenodo={EXPECTED_MD5}; file rejected.")
                if expected_size and tmp.stat().st_size != expected_size:
                    raise RuntimeError(f"Size mismatch: downloaded={tmp.stat().st_size}, API={expected_size}; file rejected.")
                tmp.replace(target)
                status = "downloaded full file and checksum-verified"
            except Exception:
                tmp.unlink(missing_ok=True)
                raise
        result = {
            "status": status,
            "source_record_url": f"https://zenodo.org/records/{args.record_id}",
            "record_id": args.record_id,
            "title": metadata.get("metadata", {}).get("title"),
            "filename": FILENAME,
            "local_path": str(target.resolve()),
            "bytes": target.stat().st_size,
            "MB_decimal": round(target.stat().st_size / 1_000_000, 3),
            "MiB": round(target.stat().st_size / (1024**2), 3),
            "md5": sha(target, "md5"),
            "expected_md5": EXPECTED_MD5,
            "sha256": sha(target, "sha256"),
            "events_reported_in_dataset_paper": EXPECTED_EVENTS,
            "scope": "one complete SM training record; no rows/bytes removed; signal and blackbox records not included",
            "limitations": ["This is the complete main training file, not all six records in the wider challenge release."]
        }
        (out / "verified_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"FETCH FAILED: {type(exc).__name__}: {exc}\nNo partial file is accepted. Check network, then rerun.", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
