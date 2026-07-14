"""Run AVQI/ABI analysis over all 296 VQD recordings, caching results to
tests/vqd_results.csv for correlation analysis against real perceptual
breathiness ratings. Not a pytest test -- run manually:
python tests/run_vqd_batch.py
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.vqd_utils import ROOT, load_manifest, analyze_vqd_recording

RESULTS_PATH = ROOT / "tests" / "vqd_results.csv"


def main():
    rows = load_manifest()
    print(f"analyzing {len(rows)} VQD recordings...")

    results = []
    errors = []
    t0 = time.time()
    for i, row in enumerate(rows):
        try:
            results.append(analyze_vqd_recording(row))
        except Exception as exc:
            errors.append((row["file_id"], str(exc)))
        if (i + 1) % 30 == 0:
            print(f"  {i+1}/{len(rows)} done, {time.time()-t0:.0f}s elapsed")

    print(f"done in {time.time()-t0:.0f}s, {len(results)} ok, {len(errors)} errors")
    for fid, err in errors[:10]:
        print("  ERROR", fid, err)

    if results:
        fieldnames = list(results[0].keys())
        with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"wrote {len(results)} rows to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
