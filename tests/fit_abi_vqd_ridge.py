"""Refit ABI with ridge regression instead of plain OLS, to test whether
regularization fixes the multicollinearity sign-flip found investigating a
real user's case: shimmer_local_db and shimmer_local_pct correlate at
r=0.985 in VQD yet get large, opposite-signed OLS coefficients (+0.646 /
-0.480), and CPPS/HNR/GNE (r=0.71-0.75) show a smaller version of the same
pattern. Ridge shrinks correlated predictors toward sharing credit instead
of letting them cancel, without dropping any feature outright.

Mirrors tests/fit_abi_vqd.py's exact data loading and CV protocol (same
5-fold split, same random_state=42) so the two are directly comparable.
Writes to analysis/abi_vqd_model_ridge.json (NOT the production
abi_vqd_model.json) -- promote manually only if this genuinely validates
better and fixes the sign issue. Not a pytest test -- run manually:
python tests/fit_abi_vqd_ridge.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from fit_abi_vqd import FEATURES, load_data, ROOT

MODEL_PATH = ROOT / "analysis" / "abi_vqd_model_ridge.json"
ALPHAS = np.logspace(-2, 3, 25)


def main():
    X, y_grbas, y_capev, abi_published, abi_svd, rows = load_data()
    print(f"n={len(y_grbas)}")

    print("\n--- Ridge (regularized) regression, same 5-fold CV protocol as OLS ---")
    pipeline = make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS))
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_pred = cross_val_predict(pipeline, X, y_grbas, cv=cv)
    r_cv, _ = pearsonr(cv_pred, y_grbas)
    rmse_cv = np.sqrt(np.mean((cv_pred - y_grbas) ** 2))
    print(f"5-fold CV: Pearson r={r_cv:.3f}, RMSE={rmse_cv:.3f} (GRBAS-B scale is 0-3)")
    print(f"(for comparison, existing OLS model: r=0.814, RMSE=0.451)")

    final_pipeline = make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS))
    final_pipeline.fit(X, y_grbas)
    scaler: StandardScaler = final_pipeline.named_steps["standardscaler"]
    reg: RidgeCV = final_pipeline.named_steps["ridgecv"]
    print(f"selected alpha: {reg.alpha_:.4f}")

    print("\n--- Coefficients: OLS vs Ridge (does the sign-flip resolve?) ---")
    ols_coefs = {
        "abi_sub_cpps_db": -0.21868605268851055,
        "abi_sub_jitter_local_pct": 0.04276929967346321,
        "abi_sub_gne_max": -0.35877551766734955,
        "abi_sub_hf_noise_6000_db": 0.06946103210366902,
        "abi_sub_hnr_d_db": 0.1281988232259717,
        "abi_sub_h1_h2_db": 0.07527204700475537,
        "abi_sub_shimmer_local_db": 0.6455316604860771,
        "abi_sub_shimmer_local_pct": -0.47959385853869446,
        "abi_sub_psd_s": -0.07114367145836603,
    }
    print(f"{'feature':28s} {'OLS coef':>10s} {'Ridge coef':>12s}")
    for f, c in zip(FEATURES, reg.coef_):
        print(f"{f:28s} {ols_coefs[f]:10.3f} {c:12.3f}")

    fitted_0_3 = final_pipeline.predict(X)
    scale_0_3_to_0_10 = 10.0 / 3.0

    model = {
        "features": FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": reg.coef_.tolist(),
        "intercept": float(reg.intercept_),
        "ridge_alpha": float(reg.alpha_),
        "output_scale_0_3_to_0_10": scale_0_3_to_0_10,
        "cv_pearson_r": float(r_cv),
        "cv_rmse_grbas_scale": float(rmse_cv),
        "n_train": len(y_grbas),
        "method": "ridge_regression_vqd_grbas_breathiness",
        "note": (
            "Same VQD GRBAS-Breathiness target and 9 sub-measures as the "
            "OLS model (tests/fit_abi_vqd.py), refit with ridge regression "
            "(alpha cross-validated) to address a found multicollinearity "
            "sign-flip: shimmer_local_db/shimmer_local_pct correlate at "
            "r=0.985 in training yet got opposite-signed OLS coefficients. "
            "See tests/fit_abi_vqd_ridge.py."
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
