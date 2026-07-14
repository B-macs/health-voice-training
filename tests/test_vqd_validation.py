"""ABI validation against VQD's real perceptual breathiness ratings --
the authoritative ABI validation for this project (see analysis/indices.py
module docstring for the full three-stage investigation this superseded).

CAUTION -- these are in-sample regression/sanity checks, not a fresh
held-out validation: the deployed model (analysis/abi_vqd_model.json) was
fit on all 296 VQD recordings, and the sample analyzed here is drawn from
that same 296, so scores here will look better than true generalization
performance. The honest, held-out estimate is the 5-fold cross-validated
result reported by tests/fit_abi_vqd.py (Pearson r=0.814, AUC=0.894) --
these tests exist to catch a future regression in the deployed model/code,
not to re-establish its real-world accuracy.

Skips (does not fail) if the VQD dataset isn't present locally -- this
suite depends on external data that isn't vendored into the repo.
"""
from __future__ import annotations

import random

import numpy as np
import pytest
from scipy.stats import pearsonr
from sklearn.metrics import roc_auc_score

from tests.vqd_utils import MANIFEST_PATH, load_manifest, analyze_vqd_recording

pytestmark = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="VQD dataset / manifest not present locally -- run tests/build_vqd_manifest.py first",
)

N_PER_CATEGORY = 10


@pytest.fixture(scope="module")
def vqd_sample_results():
    rows = load_manifest()
    by_category: dict[str, list[dict]] = {}
    for row in rows:
        by_category.setdefault(row["grbas_breathiness_category"], []).append(row)

    rng = random.Random(7)
    sample = []
    for category, category_rows in by_category.items():
        rng.shuffle(category_rows)
        sample.extend(category_rows[:N_PER_CATEGORY])

    return [analyze_vqd_recording(row) for row in sample]


def test_abi_correlates_with_real_grbas_breathiness(vqd_sample_results):
    abi = np.array([r["abi_svd_fitted"] for r in vqd_sample_results])
    grbas = np.array([r["grbas_breathiness_avg"] for r in vqd_sample_results])
    r, p = pearsonr(abi, grbas)
    assert r > 0.5, f"ABI vs. real GRBAS-Breathiness correlation too weak: r={r:.3f} (p={p:.1e})"


def test_abi_correlates_with_real_cape_v_breathiness(vqd_sample_results):
    abi = np.array([r["abi_svd_fitted"] for r in vqd_sample_results])
    capev = np.array([r["cape_v_breathiness_avg"] for r in vqd_sample_results])
    r, p = pearsonr(abi, capev)
    assert r > 0.5, f"ABI vs. real CAPE-V-Breathiness correlation too weak: r={r:.3f} (p={p:.1e})"


def test_abi_category_medians_monotonic(vqd_sample_results):
    by_cat: dict[str, list[float]] = {}
    for r in vqd_sample_results:
        by_cat.setdefault(r["grbas_breathiness_category"], []).append(r["abi_svd_fitted"])

    order = ["Normal", "Mild", "Moderate", "Severe"]
    medians = [np.median(by_cat[c]) for c in order if c in by_cat]
    assert medians == sorted(medians), f"ABI category medians not monotonic: {dict(zip(order, medians))}"


def test_abi_auc_for_any_breathiness(vqd_sample_results):
    abi = np.array([r["abi_svd_fitted"] for r in vqd_sample_results])
    grbas = np.array([r["grbas_breathiness_avg"] for r in vqd_sample_results])
    y_true = (grbas > 0.5).astype(int)
    if len(set(y_true)) < 2:
        pytest.skip("sample has only one class for 'any breathiness present' at this sample size")
    auc = roc_auc_score(y_true, abi)
    assert auc > 0.75, f"AUC for detecting any breathiness too low: {auc:.3f}"


def test_published_formula_does_not_correlate_positively(vqd_sample_results):
    """Documents WHY the published Barsties formula isn't used anymore
    (see analysis/indices.py docstring): it doesn't just have unverified
    sub-measures, it has essentially no positive relationship with real
    perceptual breathiness. This is a regression guard, not a design goal --
    if this starts failing, someone has "fixed" the published-formula path
    without re-validating it against real ratings."""
    published = np.array([r["abi_published_formula"] for r in vqd_sample_results])
    grbas = np.array([r["grbas_breathiness_avg"] for r in vqd_sample_results])
    r, _ = pearsonr(published, grbas)
    assert r < 0.3, f"Published formula correlates better than expected (r={r:.3f}) -- re-examine before reverting the VQD-fitted model"
