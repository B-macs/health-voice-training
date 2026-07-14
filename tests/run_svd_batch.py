"""Run the analysis pipeline over a stratified SVD sample and cache raw
results to tests/svd_results.csv for both the discrimination report and
ad-hoc debugging (e.g. of the ABI issue). Not a pytest test itself --
run manually: python tests/run_svd_batch.py [n_per_condition]
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.svd_utils import load_manifest, build_recording_index, stratified_sample, analyze_recording

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "tests" / "svd_results.csv"


def main(n_per_condition: int = 50):
    rows = load_manifest()
    idx = build_recording_index(rows)

    total_recordings = len({r["recording_id"] for r in rows})
    print(f"total distinct recordings: {total_recordings}, complete (SV+CS ok): {len(idx)}")

    sample = stratified_sample(idx, n_per_condition=n_per_condition)
    print(f"analyzing {len(sample)} recordings...")

    results = []
    t0 = time.time()
    errors = []
    for i, entry in enumerate(sample):
        try:
            r = analyze_recording(entry)
            results.append(r)
        except Exception as exc:
            errors.append((entry["recording_id"], str(exc)))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(sample)} done, {time.time()-t0:.0f}s elapsed")

    print(f"done in {time.time()-t0:.0f}s, {len(results)} ok, {len(errors)} errors")
    for rid, err in errors[:10]:
        print("  ERROR", rid, err)

    if results:
        fieldnames = list(results[0].keys())
        with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"wrote {len(results)} rows to {RESULTS_PATH}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    main(n)
