"""Generate reports/vqd_validation_report.md from the cached, full
296-recording tests/vqd_results.csv (no audio reprocessing needed --
sub-measures are cached; scores are recomputed from them).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "tests" / "vqd_results.csv"
MODEL_PATH = ROOT / "analysis" / "abi_vqd_model.json"
OUT_PATH = ROOT / "reports" / "vqd_validation_report.md"


def main():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    features = model["features"]
    mean = np.array(model["scaler_mean"])
    scale = np.array(model["scaler_scale"])
    coefs = np.array(model["coefficients"])

    grbas = np.array([float(r["grbas_breathiness_avg"]) for r in rows])
    capev = np.array([float(r["cape_v_breathiness_avg"]) for r in rows])
    published = np.array([float(r["abi_published_formula"]) for r in rows])
    categories = [r["grbas_breathiness_category"] for r in rows]

    X = np.array([[float(r[f]) for f in features] for r in rows])
    Xz = (X - mean) / scale
    pred_0_3 = Xz @ coefs + model["intercept"]
    vqd_fitted = np.clip(pred_0_3 * model["output_scale_0_3_to_0_10"], 0, 10)

    lines = ["# VQD validation report\n\n"]
    lines.append(
        "The authoritative ABI validation for this project: 296 recordings "
        "from the Perceptual Voice Qualities Database (VQD), each "
        "independently rated by 3-4 expert clinicians (2 trials each) on "
        "GRBAS and CAPE-V, including Breathiness (ICC .844 interrater / "
        ".884 intrarater -- see 'Voice Samples Direct Download/Introduction, "
        "Methods and Reliability/database overview v2.pdf'). Unlike SVD, "
        "this provides the actual continuous perceptual construct ABI is "
        "supposed to predict, not a diagnosis-category proxy. See "
        "analysis/indices.py module docstring for the full four-stage "
        "investigation this resolved.\n\n"
        "NOTE: `vqd_fitted` below is in-sample (the deployed model was fit "
        "on all 296 of these recordings) -- the honest held-out estimate is "
        "the 5-fold CV figure reported by tests/fit_abi_vqd.py.\n\n"
    )

    lines.append(f"Sample size: {len(rows)}\n\n")

    lines.append("## Correlation with real perceptual ratings\n\n")
    lines.append("| model | vs GRBAS-Breathiness (r) | vs CAPE-V-Breathiness (r) |\n|---|---|---|\n")
    for name, values in (("published Barsties formula", published), ("VQD-fitted (deployed, in-sample)", vqd_fitted)):
        r_grbas, _ = pearsonr(values, grbas)
        r_capev, _ = pearsonr(values, capev)
        lines.append(f"| {name} | {r_grbas:.3f} | {r_capev:.3f} |\n")

    cv = model.get("cv_pearson_r")
    if cv is not None:
        lines.append(f"\n5-fold cross-validated (honest, held-out) Pearson r = {cv:.3f} "
                     f"(RMSE {model['cv_rmse_grbas_scale']:.3f} on the 0-3 GRBAS-B scale).\n")

    lines.append("\n## ABI (deployed model) by GRBAS-Breathiness category\n\n")
    lines.append("| category | n | median | mean | min | max |\n|---|---|---|---|---|---|\n")
    by_cat: dict[str, list[float]] = {}
    for cat, val in zip(categories, vqd_fitted):
        by_cat.setdefault(cat, []).append(val)
    for cat in ("Normal", "Mild", "Moderate", "Severe"):
        if cat in by_cat:
            vals = by_cat[cat]
            lines.append(f"| {cat} | {len(vals)} | {np.median(vals):.2f} | {np.mean(vals):.2f} | {min(vals):.2f} | {max(vals):.2f} |\n")

    y_true = (grbas > 0.5).astype(int)
    auc = roc_auc_score(y_true, vqd_fitted)
    threshold = float(model["decision_threshold_0_10"])
    y_pred = (vqd_fitted > threshold).astype(int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    lines.append(f"\nAUC (any breathiness present, GRBAS-B > 0.5) = {auc:.3f}; "
                 f"at cutoff {threshold:.2f} (0-10 scale): sensitivity = {sens:.2f}, specificity = {spec:.2f} (n={len(rows)}).\n")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
