"""Fit a bespoke breathiness/dysphonia discriminant on real SVD-labeled
data, to replace the broken Barsties-ABI-formula reimplementation.

IMPORTANT METHODOLOGICAL NOTE: this is NOT a reproduction of Barsties'
published ABI. Barsties' ABI was fit by OLS regression against continuous
perceptual GRBAS-B (breathiness) ratings from expert listeners. The SVD
provides diagnosis labels only, no perceptual ratings (see PLAN.md ground
truth rules), so the best available target here is a coarser binary label
(healthy vs. any diagnosed dysphonia). This script fits a logistic
regression against that binary label, using the same 9 conceptual
sub-measures Barsties used as inputs (so the feature *set* still reflects
the published science) with coefficients learned from real data instead of
guessed sub-measure definitions. Output is rescaled to 0-10 for interface
compatibility with the existing "index" convention, but it is a distinct,
locally-fit model -- documented as such everywhere, not passed off as the
validated ABI.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "tests" / "svd_results.csv"
MODEL_PATH = ROOT / "analysis" / "abi_svd_model.json"

FEATURES = [
    "abi_sub_cpps_db", "abi_sub_jitter_local_pct", "abi_sub_gne_max",
    "abi_sub_hf_noise_6000_db", "abi_sub_hnr_d_db", "abi_sub_h1_h2_db",
    "abi_sub_shimmer_local_db", "abi_sub_shimmer_local_pct", "abi_sub_psd_s",
]


def load_data():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Internusschwaeche has n=1 -- too small to be a meaningful class member;
    # score it later as a held-out informational point, not a training row.
    rows = [r for r in rows if r["condition"] != "Internusschwäche"]

    X = np.array([[float(r[f]) for f in FEATURES] for r in rows])
    y = np.array([0 if r["condition"] == "healthy" else 1 for r in rows])
    return X, y, rows


def main():
    X, y, rows = load_data()
    print(f"n={len(y)}, healthy={sum(y==0)}, pathological={sum(y==1)}")

    pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))

    # Cross-validated, honest generalization estimate (5-fold stratified).
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_proba = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")[:, 1]
    cv_auc = roc_auc_score(y, cv_proba)
    print(f"5-fold cross-validated AUC: {cv_auc:.3f}")

    fpr, tpr, thresholds = roc_curve(y, cv_proba)
    youden = tpr - fpr
    best_idx = np.argmax(youden)
    best_threshold = thresholds[best_idx]
    sens, spec = tpr[best_idx], 1 - fpr[best_idx]
    print(f"Youden-optimal probability threshold: {best_threshold:.3f} (sens={sens:.2f}, spec={spec:.2f})")

    # Final model fit on ALL available data (more data -> better-calibrated
    # coefficients; CV above already gave the honest performance estimate).
    final_pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    final_pipeline.fit(X, y)
    scaler: StandardScaler = final_pipeline.named_steps["standardscaler"]
    clf: LogisticRegression = final_pipeline.named_steps["logisticregression"]

    model = {
        "features": FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": clf.coef_[0].tolist(),
        "intercept": float(clf.intercept_[0]),
        "probability_threshold": float(best_threshold),
        "cv_auc": float(cv_auc),
        "cv_sensitivity_at_threshold": float(sens),
        "cv_specificity_at_threshold": float(spec),
        "n_train": len(y),
        "method": "logistic_regression_svd_binary_label",
        "note": (
            "Bespoke discriminant fit on SVD healthy-vs-any-dysphonia "
            "labels, NOT Barsties' published ABI (which was fit against "
            "continuous perceptual GRBAS-B ratings, unavailable here). "
            "See tests/fit_abi_svd.py and PLAN.md."
        ),
    }
    MODEL_PATH.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"wrote model to {MODEL_PATH}")

    # Sanity: does the fitted probability, rescaled 0-10, separate conditions?
    proba_all = final_pipeline.predict_proba(X)[:, 1]
    score_0_10 = proba_all * 10
    by_cond: dict[str, list[float]] = {}
    for r, s in zip(rows, score_0_10):
        by_cond.setdefault(r["condition"], []).append(s)
    for cond, vals in by_cond.items():
        print(f"  {cond}: median score {np.median(vals):.2f} (n={len(vals)})")


if __name__ == "__main__":
    main()
