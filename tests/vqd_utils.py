"""Shared helpers for VQD-based ABI validation.

Each VQD recording is a single WAV containing sustained /a/, /i/, and the
CAPE-V sentences concatenated -- already a natural analogue of this app's
own "combined_sound" (sustained vowel + continuous speech), so it's fed
directly to compute_avqi/compute_abi without needing to segment it.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "tests" / "vqd_manifest.csv"

# The published Barsties ABI formula, recomputed from the 9 sub-measures
# for comparison purposes only -- analysis/indices.py no longer uses this
# (see its module docstring); kept here so we can test it against REAL
# perceptual breathiness ratings rather than just SVD diagnosis labels.
PUBLISHED_ABI_INTERCEPT = 5.0447740915
PUBLISHED_ABI_SCALE = 2.9257400394
PUBLISHED_ABI_COEFS = {
    "cpps_db": -0.172,
    "jitter_local_pct": -0.193,
    "gne_max": -1.283,
    "hf_noise_6000_db": -0.396,
    "hnr_d_db": 0.01,
    "h1_h2_db": 0.017,
    "shimmer_local_db": 1.473,
    "shimmer_local_pct": -0.088,
    "psd_s": -68.295,
}


def published_abi_formula(components: dict) -> float:
    raw = PUBLISHED_ABI_INTERCEPT + sum(
        coef * components[name] for name, coef in PUBLISHED_ABI_COEFS.items()
    )
    return float(np.clip(raw * PUBLISHED_ABI_SCALE, 0.0, 10.0))


def load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["duration_s"] = float(row["duration_s"])
        row["sample_rate"] = int(row["sample_rate"])
        row["grbas_breathiness_avg"] = float(row["grbas_breathiness_avg"]) if row["grbas_breathiness_avg"] else float("nan")
        row["cape_v_breathiness_avg"] = float(row["cape_v_breathiness_avg"]) if row["cape_v_breathiness_avg"] else float("nan")
        row["cape_v_breathiness_sd"] = float(row["cape_v_breathiness_sd"]) if row["cape_v_breathiness_sd"] else float("nan")
    return rows


def analyze_vqd_recording(row: dict) -> dict:
    from analysis.audio_io import load_wav_file
    from analysis.indices import compute_avqi, compute_abi

    combined = load_wav_file(str(ROOT / row["file_path"]))

    avqi_result = compute_avqi(combined)
    abi_result = compute_abi(combined)
    abi_components = abi_result.as_dict()["components"]

    return {
        "file_id": row["file_id"],
        "grbas_breathiness_avg": row["grbas_breathiness_avg"],
        "grbas_breathiness_category": row["grbas_breathiness_category"],
        "cape_v_breathiness_avg": row["cape_v_breathiness_avg"],
        "avqi": avqi_result.avqi,
        # Whatever analysis.indices.compute_abi currently returns -- at the
        # time tests/run_vqd_batch.py was first run, this was the SVD-fitted
        # logistic model (hence "abi_svd_fitted" in tests/vqd_results.csv,
        # kept as historical column name for that one-time, valid
        # out-of-sample comparison). indices.py now uses the VQD-fitted
        # model instead. CAUTION if re-running this batch: scoring VQD data
        # with a model fit ON VQD data is circular, not a fresh validation.
        "abi_svd_fitted": abi_result.abi,
        "abi_published_formula": published_abi_formula(abi_components),
        **{f"abi_sub_{k}": v for k, v in abi_components.items()},
    }
