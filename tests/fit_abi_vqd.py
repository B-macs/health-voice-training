"""Fit ABI against REAL continuous perceptual breathiness ratings (VQD:
GRBAS-Breathiness, 0-3 scale, averaged across 3-4 expert raters x 2 trials
each; ICC .844 interrater / .884 intrarater). This is much closer to
Barsties' actual original methodology (regression against perceptual
ratings) than the SVD-based binary-label logistic model, which had to
substitute a coarse diagnosis category for the real construct because SVD
provides no perceptual ratings.

Also reports, for comparison on the SAME real ground truth:
  - the published Barsties ABI formula's correlation with real breathiness
    (re-checking whether it's genuinely broken, or was just evaluated
    against the wrong construct via SVD's diagnosis labels)
  - the SVD-fitted logistic model's correlation with real breathiness
before deciding which approach analysis/indices.py should use.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "tests" / "vqd_results.csv"
MODEL_PATH = ROOT / "analysis" / "abi_vqd_model.json"

FEATURES = [
    "abi_sub_cpps_db", "abi_sub_jitter_local_pct", "abi_sub_gne_max",
    "abi_sub_hf_noise_6000_db", "abi_sub_hnr_d_db", "abi_sub_h1_h2_db",
    "abi_sub_shimmer_local_db", "abi_sub_shimmer_local_pct", "abi_sub_psd_s",
]


def load_data():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r["grbas_breathiness_avg"] not in ("", None)]
    X = np.array([[float(r[f]) for f in FEATURES] for r in rows])
    y = np.array([float(r["grbas_breathiness_avg"]) for r in rows])
    y_capev = np.array([float(r["cape_v_breathiness_avg"]) for r in rows])
    abi_published = np.array([float(r["abi_published_formula"]) for r in rows])
    abi_svd = np.array([float(r["abi_svd_fitted"]) for r in rows])
    return X, y, y_capev, abi_published, abi_svd, rows


def report_correlation(name, values, target, target_name):
    mask = np.isfinite(values) & np.isfinite(target)
    r_pearson, p_pearson = pearsonr(values[mask], target[mask])
    r_spearman, p_spearman = spearmanr(values[mask], target[mask])
    print(f"{name} vs {target_name}: Pearson r={r_pearson:.3f} (p={p_pearson:.1e}), "
          f"Spearman rho={r_spearman:.3f} (p={p_spearman:.1e}), n={mask.sum()}")
    return r_pearson, r_spearman


def main():
    X, y_grbas, y_capev, abi_published, abi_svd, rows = load_data()
    print(f"n={len(y_grbas)}")
    print(f"GRBAS-B range: {y_grbas.min():.2f}-{y_grbas.max():.2f}, mean={y_grbas.mean():.2f}")

    print("\n--- Does the PUBLISHED formula correlate with REAL breathiness? ---")
    report_correlation("published ABI formula", abi_published, y_grbas, "GRBAS-B")
    report_correlation("published ABI formula", abi_published, y_capev, "CAPE-V-B")

    print("\n--- Does the SVD-fitted logistic model correlate with REAL breathiness? ---")
    report_correlation("SVD-fitted ABI", abi_svd, y_grbas, "GRBAS-B")
    report_correlation("SVD-fitted ABI", abi_svd, y_capev, "CAPE-V-B")

    print("\n--- Fitting a NEW linear regression directly on VQD GRBAS-B ratings ---")
    pipeline = make_pipeline(StandardScaler(), LinearRegression())
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_pred = cross_val_predict(pipeline, X, y_grbas, cv=cv)
    r_cv, _ = pearsonr(cv_pred, y_grbas)
    rmse_cv = np.sqrt(np.mean((cv_pred - y_grbas) ** 2))
    print(f"5-fold CV: Pearson r={r_cv:.3f}, RMSE={rmse_cv:.3f} (GRBAS-B scale is 0-3)")

    final_pipeline = make_pipeline(StandardScaler(), LinearRegression())
    final_pipeline.fit(X, y_grbas)
    scaler: StandardScaler = final_pipeline.named_steps["standardscaler"]
    reg: LinearRegression = final_pipeline.named_steps["linearregression"]

    fitted_0_3 = final_pipeline.predict(X)
    # Rescale predicted GRBAS-B (roughly 0-3, can go slightly outside) to a
    # 0-10 index for interface compatibility with the existing convention.
    scale_0_3_to_0_10 = 10.0 / 3.0

    model = {
        "features": FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": reg.coef_.tolist(),
        "intercept": float(reg.intercept_),
        "output_scale_0_3_to_0_10": scale_0_3_to_0_10,
        "cv_pearson_r": float(r_cv),
        "cv_rmse_grbas_scale": float(rmse_cv),
        "n_train": len(y_grbas),
        "method": "linear_regression_vqd_grbas_breathiness",
        "note": (
            "Fit directly on VQD real perceptual GRBAS-Breathiness ratings "
            "(continuous, 0-3, averaged across 3-4 expert raters x 2 trials; "
            "ICC .844 interrater/.884 intrarater) -- the same KIND of target "
            "Barsties' original ABI was fit against (though not the same "
            "raters/samples/scale calibration, so still not a reproduction "
            "of the validated ABI). See tests/fit_abi_vqd.py and "
            "analysis/indices.py."
        ),
    }
    MODEL_PATH.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"\nwrote model to {MODEL_PATH}")

    print("\n--- sanity: does fitted score track GRBAS-B category? ---")
    by_cat: dict[str, list[float]] = {}
    for r, pred in zip(rows, fitted_0_3 * scale_0_3_to_0_10):
        by_cat.setdefault(r["grbas_breathiness_category"], []).append(pred)
    for cat in ("Normal", "Mild", "Moderate", "Severe"):
        if cat in by_cat:
            vals = by_cat[cat]
            print(f"  {cat}: median={np.median(vals):.2f} (n={len(vals)})")


if __name__ == "__main__":
    main()
