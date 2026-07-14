"""Refit ABI with Lasso instead of OLS -- the production model as of this
script, replacing tests/fit_abi_vqd.py's OLS fit.

Root cause this fixes: investigating a real user's case (confirmed
ENT-diagnosed incomplete glottic closure, a genuinely breathy voice) whose
ABI came back "in range" surfaced that the OLS model's two largest
coefficients belonged to shimmer_local_db (+0.646) and shimmer_local_pct
(-0.480) -- two different units for the same underlying quantity, r=0.985
correlated in the 296-recording VQD training set -- given large, opposite
signs. Individually each correlates positively and sensibly with real
GRBAS-Breathiness ratings (r=0.606 and r=0.582); only the joint OLS fit
cancels them. A smaller version of the same pattern gave HNR a positive
(backwards) coefficient, since it's correlated 0.71-0.75 with CPPS/GNE.

Tried first (tests/fit_abi_vqd_ridge.py): RidgeCV, letting cross-validation
pick alpha. Doesn't fix it -- CV-minimizing alpha stays tiny (0.75) because
the wrong-signed split genuinely does minimize error on THIS population;
the fix requires deliberately trading a little in-sample fit for
robustness, which CV-driven alpha selection will never choose on its own.

This script instead sweeps Lasso's alpha and picks the smallest value at
which every nonzero coefficient's sign matches its own univariate
correlation with real breathiness (see fit_abi_vqd_ridge.py's sweep
output for the full trace). alpha=0.01 is the answer: shimmer_local_pct
and hnr_d_db are cleanly zeroed out (not just shrunk-and-still-wrong), the
5-fold CV Pearson r moves from 0.814 to 0.809 (RMSE 0.451 to 0.455) -- a
trivial cost -- and the one remaining sign mismatch (psd_s, coefficient
~-0.01) has a univariate correlation of only r=0.086, i.e. essentially no
real signal to be "wrong" about.

Not a pytest test -- run manually: python tests/fit_abi_vqd_lasso.py
"""
from __future__ import annotations

import json

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import Lasso
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from fit_abi_vqd import FEATURES, load_data, MODEL_PATH

ALPHA = 0.01


def main():
    X, y_grbas, y_capev, abi_published, abi_svd, rows = load_data()
    print(f"n={len(y_grbas)}")

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    pipeline = make_pipeline(StandardScaler(), Lasso(alpha=ALPHA, max_iter=20000))
    cv_pred = cross_val_predict(pipeline, X, y_grbas, cv=cv)
    r_cv, _ = pearsonr(cv_pred, y_grbas)
    rmse_cv = np.sqrt(np.mean((cv_pred - y_grbas) ** 2))
    print(f"5-fold CV: Pearson r={r_cv:.3f}, RMSE={rmse_cv:.3f} (was r=0.814, RMSE=0.451 for OLS)")

    final_pipeline = make_pipeline(StandardScaler(), Lasso(alpha=ALPHA, max_iter=20000))
    final_pipeline.fit(X, y_grbas)
    scaler: StandardScaler = final_pipeline.named_steps["standardscaler"]
    reg: Lasso = final_pipeline.named_steps["lasso"]

    print("\ncoefficients:")
    for f, c in zip(FEATURES, reg.coef_):
        print(f"  {f:28s} {c:8.3f}")

    fitted_0_3 = final_pipeline.predict(X)
    scale_0_3_to_0_10 = 10.0 / 3.0

    model = {
        "features": FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": reg.coef_.tolist(),
        "intercept": float(reg.intercept_),
        "lasso_alpha": ALPHA,
        "output_scale_0_3_to_0_10": scale_0_3_to_0_10,
        "cv_pearson_r": float(r_cv),
        "cv_rmse_grbas_scale": float(rmse_cv),
        "n_train": len(y_grbas),
        "method": "lasso_regression_vqd_grbas_breathiness",
        "note": (
            "Supersedes the plain-OLS fit (see analysis/abi_vqd_model_ols_v1_backup.json "
            "and tests/fit_abi_vqd.py) after a real user's confirmed-breathy case exposed "
            "a multicollinearity sign-flip: shimmer_local_db/shimmer_local_pct correlate "
            "at r=0.985 in training yet OLS gave them large opposite-signed coefficients, "
            "and CPPS/HNR/GNE (r=0.71-0.75) produced a smaller version of the same thing. "
            "Refit with Lasso (alpha=0.01, chosen as the smallest value where every nonzero "
            "coefficient's sign matches its own univariate correlation with real "
            "GRBAS-Breathiness) -- shimmer_local_pct and hnr_d_db are cleanly zeroed rather "
            "than left as small wrong-signed residuals. 5-fold CV Pearson r=0.809 (was "
            "0.814 for OLS) -- a trivial cost for a materially more robust model. See "
            "tests/fit_abi_vqd_lasso.py and tests/fit_abi_vqd_ridge.py (documents why "
            "CV-tuned Ridge/Lasso alpha alone does NOT fix this -- minimizing in-sample "
            "CV error is what produced the sign-flip to begin with)."
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
