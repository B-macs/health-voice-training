"""Golden-master regression test: catches accidental side effects when
editing one part of the analysis pipeline (e.g. touching H1-H2 code
shouldn't silently shift CPPS or jitter too).

This is NOT a correctness test -- see test_metrics.py/test_indices.py for
sanity-bounds checks, and PLAN.md/CHANGELOG.md for the real external
validation (SVD/VQD, VoxPlot comparison). This test only freezes the
CURRENT output for fixed, deterministic synthetic input and fails loudly
if ANY of the 14 parameters or AVQI/ABI drift, even slightly, so an
unintended side effect from an unrelated change gets caught immediately
instead of shipping silently.

Workflow:
  1. Make your change.
  2. Run: pytest tests/test_regression_snapshot.py -v
  3. If a value you did NOT mean to touch changed -- stop, that's a
     regression, go find it.
  4. If only the value(s) you meant to change moved, by the amount you
     expect -- regenerate the snapshot:
       UPDATE_SNAPSHOT=1 pytest tests/test_regression_snapshot.py -v
     then re-run normally to confirm it's green, and commit the updated
     tests/snapshots/*.json file alongside your code change so the diff
     review shows exactly what shifted and why.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from analysis.audio_io import concatenate
from analysis.parselmouth_metrics import analyze_single_parameters
from analysis.indices import compute_avqi, compute_abi

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
REL_TOL = 1e-6


def _compute(sv_sound, cs_sound) -> dict:
    combined = concatenate(sv_sound, cs_sound)
    parameters = analyze_single_parameters(sv_sound, cs_sound, combined).as_dict()
    indices = {
        "avqi": compute_avqi(combined).avqi,
        "abi": compute_abi(combined).abi,
    }
    return {"parameters": parameters, "indices": indices}


def _isclose(a: float, b: float) -> bool:
    if isinstance(a, float) and a != a:  # NaN
        return isinstance(b, float) and b != b
    return abs(a - b) <= REL_TOL * max(abs(a), abs(b), 1e-12)


def _assert_matches_snapshot(name: str, actual: dict):
    path = SNAPSHOT_DIR / f"{name}.json"

    if os.environ.get("UPDATE_SNAPSHOT"):
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(actual, indent=2, sort_keys=True), encoding="utf-8")
        pytest.skip(f"Wrote new snapshot to {path} -- re-run without UPDATE_SNAPSHOT to verify.")

    if not path.exists():
        pytest.fail(f"No snapshot at {path} -- run with UPDATE_SNAPSHOT=1 to create it.")

    expected = json.loads(path.read_text(encoding="utf-8"))
    mismatches = []
    for section in ("parameters", "indices"):
        for key, exp_val in expected[section].items():
            if key not in actual[section]:
                mismatches.append(f"{section}.{key}: MISSING from current output (expected {exp_val})")
                continue
            act_val = actual[section][key]
            if not _isclose(act_val, exp_val):
                mismatches.append(f"{section}.{key}: expected {exp_val!r}, got {act_val!r}")
        for key in actual[section]:
            if key not in expected[section]:
                mismatches.append(f"{section}.{key}: NEW key not in snapshot ({actual[section][key]!r})")

    if mismatches:
        pytest.fail(
            f"{name}: {len(mismatches)} value(s) drifted from the snapshot. "
            "If this is an intentional change, refresh it with "
            "'UPDATE_SNAPSHOT=1 pytest tests/test_regression_snapshot.py' "
            "and commit the updated snapshot alongside your change:\n  "
            + "\n  ".join(mismatches)
        )


def test_clean_voice_snapshot(clean_sv, clean_cs):
    _assert_matches_snapshot("clean_voice", _compute(clean_sv, clean_cs))


def test_breathy_voice_snapshot(breathy_sv, breathy_cs):
    _assert_matches_snapshot("breathy_voice", _compute(breathy_sv, breathy_cs))
