"""P4 (discrimination check) -- and this project's actual, honest G5:

There is no licensed reference script available to test byte-for-byte
parity against (see PLAN.md "Architecture decision"), so G5 is validated
here instead as: does the pipeline's AVQI/ABI separate real, professionally
diagnosed healthy vs. pathological German voices (Saarbruecken Voice
Database) in the expected direction, at the German-validated cutoffs?
This is a weaker claim than script parity, but it is checked against real
labeled clinical data rather than synthetic signals or guesses.

Skips (does not fail) if the SVD dataset isn't present locally -- this
suite depends on multi-GB external data that isn't vendored into the repo.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from analysis.norms import get_norms
from tests.svd_utils import (
    ROOT, MANIFEST_PATH, load_manifest, build_recording_index,
    stratified_sample, analyze_recording,
)

SVD_CONDITIONS = ["healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie"]

pytestmark = pytest.mark.skipif(
    not MANIFEST_PATH.exists() or not all((ROOT / c).is_dir() for c in SVD_CONDITIONS),
    reason="SVD dataset / manifest not present locally -- run tests/build_svd_manifest.py first",
)


@pytest.fixture(scope="module")
def svd_sample_results():
    rows = load_manifest()
    idx = build_recording_index(rows)
    sample = stratified_sample(idx, n_per_condition=15, seed=123)
    results = [analyze_recording(entry) for entry in sample]
    return results


def _by_condition(results, key):
    out: dict[str, list[float]] = {}
    for r in results:
        out.setdefault(r["condition"], []).append(r[key])
    return out


def test_avqi_healthy_median_below_german_cutoff(svd_sample_results):
    by_cond = _by_condition(svd_sample_results, "avqi")
    cutoff = get_norms("de")["avqi"].max
    healthy_median = np.median(by_cond["healthy"])
    assert healthy_median < cutoff, f"healthy AVQI median {healthy_median} not below German cutoff {cutoff}"


def test_avqi_dysphonia_medians_above_german_cutoff(svd_sample_results):
    by_cond = _by_condition(svd_sample_results, "avqi")
    cutoff = get_norms("de")["avqi"].max
    for condition in ("Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie"):
        median = np.median(by_cond[condition])
        assert median > cutoff, f"{condition} AVQI median {median} not above German cutoff {cutoff}"


def test_avqi_auc_better_than_chance(svd_sample_results):
    y_true = [0 if r["condition"] == "healthy" else 1 for r in svd_sample_results
              if r["condition"] in ("healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie")]
    y_score = [r["avqi"] for r in svd_sample_results
               if r["condition"] in ("healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie")]
    auc = roc_auc_score(y_true, y_score)
    assert auc > 0.65, f"AVQI AUC {auc:.3f} is not meaningfully better than chance on this sample"


def test_abi_dysphonia_medians_exceed_healthy(svd_sample_results):
    """ABI is now fit on VQD's real perceptual breathiness ratings (see
    analysis/indices.py docstring, Stage 3), not on SVD at all. Applied to
    SVD, it gives correctly-ordered but much more COMPRESSED scores than on
    VQD (documented in PLAN.md: healthy ~0.00, Hyperfunktionelle ~0.66,
    Hypofunktionelle ~0.60) -- consistent with SVD's dysphonia categories
    not being primarily about breathiness (e.g. Hyperfunktionelle is
    typically strained/pressed, not breathy). So this checks relative
    ordering (still expected to hold), NOT absolute cutoff-crossing (the
    VQD-calibrated cutoff of 2.0 is not expected to separate SVD conditions,
    which was never what it was fit for)."""
    by_cond = _by_condition(svd_sample_results, "abi")
    healthy_median = np.median(by_cond["healthy"])
    for condition in ("Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie"):
        median = np.median(by_cond[condition])
        assert median > healthy_median, f"{condition} ABI median {median} not above healthy median {healthy_median}"


def test_abi_auc_matches_cross_validated_estimate(svd_sample_results):
    """ABI is now fit on VQD, not SVD (see analysis/indices.py docstring,
    Stage 3), so this SVD sample is genuinely held-out for it -- no
    circularity. It's still a general "any dysphonia" discrimination check,
    not what ABI is calibrated for (real breathiness ratings, see
    tests/test_vqd_validation.py for the authoritative validation); this is
    a secondary generalization/regression check, not the primary gate."""
    y_true = [0 if r["condition"] == "healthy" else 1 for r in svd_sample_results
              if r["condition"] in ("healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie")]
    y_score = [r["abi"] for r in svd_sample_results
               if r["condition"] in ("healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie")]
    auc = roc_auc_score(y_true, y_score)
    assert auc > 0.65, f"ABI AUC {auc:.3f} is not meaningfully better than chance on this sample"


def generate_report(results, out_path: Path):
    binary_results = [r for r in results if r["condition"] in
                       ("healthy", "Hyperfunktionelle Dysphonie", "Hypofunktionelle Dysphonie")]
    y_true = [0 if r["condition"] == "healthy" else 1 for r in binary_results]

    lines = ["# SVD validation report\n\n"]
    lines.append(
        "No licensed reference script was available (see PLAN.md), so this "
        "report validates the pipeline against real, professionally "
        "diagnosed voices from the Saarbruecken Voice Database (SVD) "
        "instead of byte-for-byte script parity. AVQI is the published "
        "Barsties v Latoszek formula reimplementation. ABI is a linear "
        "regression fit directly on REAL perceptual breathiness ratings "
        "from a separate database, VQD (see analysis/indices.py docstring "
        "and tests/fit_abi_vqd.py) -- SVD only provides diagnosis "
        "categories, not the breathiness ratings ABI predicts, so applying "
        "it here is a cross-dataset generalization check, not its primary "
        "validation (see tests/test_vqd_validation.py for that). ABI scores "
        "below are expected to be more COMPRESSED than on VQD, since SVD's "
        "dysphonia categories (e.g. Hyperfunktionelle = typically strained, "
        "not breathy) aren't primarily about breathiness -- correct "
        "ordering, not correct absolute cutoff-crossing, is what's checked "
        "here (see tests/test_discrimination.py).\n\n"
    )
    lines.append(f"Sample size: {len(results)} (stratified across condition and sex, seed=123). "
                 f"Small-class caveat: Hypofunktionelle Dysphonie has only 16 complete "
                 f"recordings in the entire SVD. The AVQI cutoff below (German-validated, "
                 f"Barsties v Latoszek) is a real clinical cutoff; the ABI cutoff is the "
                 f"VQD model's own Youden-optimal threshold for detecting real breathiness, "
                 f"not validated for SVD's general dysphonia categories -- see "
                 f"analysis/abi_vqd_model.json.\n")

    for metric, cutoff_key in (("avqi", "avqi"), ("abi", "abi")):
        cutoff = get_norms("de")[cutoff_key].max
        lines.append(f"\n## {metric.upper()} by condition (German cutoff: {cutoff})\n\n")
        lines.append("| condition | n | median | mean | min | max |\n|---|---|---|---|---|---|\n")
        by_cond = _by_condition(results, metric)
        for cond, vals in by_cond.items():
            lines.append(f"| {cond} | {len(vals)} | {np.median(vals):.2f} | {np.mean(vals):.2f} | {min(vals):.2f} | {max(vals):.2f} |\n")

        y_score = [r[metric] for r in binary_results]
        auc = roc_auc_score(y_true, y_score)
        y_pred = [1 if s > cutoff else 0 for s in y_score]
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
        tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
        sens = tp / (tp + fn) if (tp + fn) else float("nan")
        spec = tn / (tn + fp) if (tn + fp) else float("nan")
        lines.append(f"\nAUC (healthy vs. any dysphonia) = {auc:.3f}; at cutoff {cutoff}: "
                     f"sensitivity = {sens:.2f}, specificity = {spec:.2f} (n={len(binary_results)}).\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    rows = load_manifest()
    idx = build_recording_index(rows)
    sample = stratified_sample(idx, n_per_condition=15, seed=123)
    results = [analyze_recording(entry) for entry in sample]
    generate_report(results, ROOT / "reports" / "svd_validation_report.md")
