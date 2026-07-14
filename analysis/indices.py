"""AVQI (v03.01) and ABI(-like) multiparametric indices.

## AVQI

Reimplemented directly from the published, peer-reviewed coefficients
(source: Barsties v Latoszek et al., open-access validation paper,
PMC10743486), NOT reinvented -- see PLAN.md "Architecture decision" for the
full rationale (the official Phonanium .praat script is a paid commercial
product and cannot legally be vendored here).

    AVQIv3 = [4.152 - 0.177*CPPs - 0.006*HNR - 0.037*Shim% + 0.941*ShdB
              + 0.01*Slope + 0.093*Tilt] * 2.8902

Validated on real data: on 362 real, professionally-diagnosed Saarbruecken
Voice Database (SVD) recordings, this formula scored healthy voices lower
than both Hyperfunktionelle and Hypofunktionelle Dysphonie (median 2.43 vs.
3.24 / 3.27). That is useful historical discrimination evidence, not
reference-script parity or a transferable clinical cutoff. Sub-measure Praat
settings not fully specified in the papers (CPPS window/quefrency averaging,
exact LTAS Tilt convention) use Praat's documented defaults -- see PLAN.md's
Praat call recipes table for what's tested/verified vs. approximated.

## ABI -- NOT Barsties' published formula (three-stage investigation, see below)

**Stage 1 -- published formula, reimplemented like AVQI.** Validation against
362 real SVD recordings proved it badly broken: healthy voices scored a
median of 6.09 (dysphonic conditions scored LOWER, 4.66), and the raw
pre-clip value saturated at the 0 or 10 boundary for 17-19% of all
recordings. At the time it was unclear whether the formula itself was
broken, or just evaluated against the wrong construct (SVD gives diagnosis
categories, not the perceptual breathiness ratings ABI is supposed to
predict -- e.g. "Hyperfunktionelle Dysphonie" is typically a STRAINED voice
quality, not a breathy one, so testing ABI against "any SVD dysphonia" may
never have been a fair test).

**Stage 2 -- SVD-fitted logistic discriminant.** Rather than keep guessing at
the ambiguous "Hno-6000Hz"/"HNR-D" sub-measure definitions, a logistic
regression was fit on SVD's binary diagnosis label (healthy vs. any
dysphonia), using the same 9 conceptual sub-measures as inputs
(tests/fit_abi_svd.py). 5-fold CV AUC 0.728, correct real-data ordering.
Still explicitly a stand-in, since SVD provides no perceptual ratings.

**Stage 3 -- resolved, using VQD's real perceptual ratings.** The user added
the Perceptual Voice Qualities Database (VQD): 296 recordings independently
rated by 3-4 expert clinicians (2 trials each) on GRBAS and CAPE-V,
including Breathiness specifically (ICC .844 interrater / .884 intrarater --
see "Voice Samples Direct Download/Introduction, Methods and
Reliability/database overview v2.pdf"). This is the actual target construct
Barsties' ABI was built to predict, and let three questions finally be
answered with real ground truth (see tests/fit_abi_vqd.py):

  1. Is the published formula really broken, or was Stage 1 just the wrong
     construct? -- Genuinely broken: Pearson r = -0.154 against real
     GRBAS-Breathiness (p=0.008), r = -0.187 against CAPE-V-Breathiness
     (p=0.001). Negative and weak either way -- confirmed broken, not a
     construct-mismatch artifact.
  2. Does the SVD-fitted logistic model (Stage 2) generalize to a
     completely different population (American English, different mic
     setup, continuous rather than binary target)? -- Reasonably well:
     r = 0.591 (GRBAS-B) / 0.584 (CAPE-V-B), both p < 1e-27.
  3. Does fitting directly on VQD's real ratings do better? -- Yes,
     substantially: 5-fold CV Pearson r = 0.814 against GRBAS-Breathiness
     (RMSE 0.451 on the 0-3 scale), AUC 0.894 for detecting any breathiness
     (GRBAS-B > 0.5, the database's own Normal/Mild boundary), and clean
     monotonic category separation: Normal median 1.10, Mild 2.57, Moderate
     6.07, Severe 7.03 (rescaled to 0-10).

**Stage 4 -- OLS's multicollinearity sign-flip, found via a real user's
case and fixed with Lasso.** A user with an ENT-confirmed incomplete
glottic closure (direct laryngoscopy -- a textbook cause of a breathy
voice) scored "in range" on Stage 3's OLS-fit model despite genuinely
elevated shimmer. Investigating why: shimmer_local_db and
shimmer_local_pct are two different units for the same underlying
quantity and correlate at r=0.985 across the 296 VQD recordings, yet OLS
gave them large, opposite-signed coefficients (+0.646 / -0.480) --
individually each correlates positively and sensibly with real
GRBAS-Breathiness (r=0.606 / r=0.582), so the joint OLS fit was cancelling
a real, unambiguous signal against itself. CPPS/HNR/GNE (r=0.71-0.75 with
each other) showed a smaller version of the same thing, leaving HNR with
a backwards-signed (+0.128) coefficient. This is textbook OLS
multicollinearity instability, not a code bug, and in-sample cross-
validation can't see it -- it only bites a voice whose feature *ratios*
differ from the training population's typical ratios.

Tried RidgeCV first (tests/fit_abi_vqd_ridge.py): doesn't fix it. The
CV-error-minimizing alpha stays tiny, because the wrong-signed split
genuinely does minimize error on this training population -- fixing this
requires deliberately trading a little in-sample fit for robustness, which
error-minimizing alpha selection will never choose on its own.

`compute_abi` now uses a Lasso fit instead (tests/fit_abi_vqd_lasso.py),
with alpha chosen as the smallest value where every nonzero coefficient's
sign matches its own univariate correlation with real breathiness.
shimmer_local_pct and hnr_d_db are cleanly zeroed out (not just shrunk and
still wrong). Cost: 5-fold CV Pearson r drops from 0.814 to 0.809 (RMSE
0.451 to 0.455) -- essentially free. The Youden-optimal "any breathiness"
threshold moved slightly too (2.00 -> 2.10 on the 0-10 scale; AUC
0.894 -> 0.888, see analysis/norms.py). Previous OLS model backed up at
analysis/abi_vqd_model_ols_v1_backup.json for reference/rollback.

This resolved a real, verifiable statistical flaw, but did NOT by itself
flip the triggering user's case to "flagged" when reconstructed from
logged proxy values -- see Investigation/01_Voice_Quality_Overview.html
for why (largely: compute_abi's CPPS/HNR/etc. are computed on the
combined vowel+passage recording, which isn't logged anywhere, so any
retrospective reconstruction from logged sustained-vowel-only values is
an approximation, and a duration-weighted CPPS estimate alone moved the
reconstructed score much closer to the threshold). The honest next step
for that specific case is a fresh recording through the live corrected
model, not further reconstruction.

`compute_abi` predicts continuous GRBAS-Breathiness (0-3) and rescales to
0-10 (coefficients in analysis/abi_vqd_model.json). This is still not a
reproduction of Barsties' validated ABI (different raters, samples, and
scale calibration), so treat it as a locally-calibrated breathiness
discriminant, not a certified clinical instrument.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import parselmouth
from parselmouth.praat import call

from analysis.parselmouth_metrics import (
    compute_cpps,
    compute_hnr,
    compute_jitter,
    compute_shimmer,
    compute_ltas_slope_tilt,
    compute_gne,
    compute_h1_h2,
    compute_psd_seconds,
    compute_f0_stats,
)


TARGET_INTENSITY_DB = 70.0
OOD_MAX_ABS_Z = 3.0


def _intensity_normalized(sound: parselmouth.Sound) -> parselmouth.Sound:
    """Return an intensity-normalized copy of `sound`.

    Discovered empirically while testing: Praat's LTAS-derived absolute
    level at a single frequency (used for the ABI 'Hfno' sub-measure) is
    NOT gain-invariant -- the same voice recorded louder/quieter gives a
    different raw dB reading (verified: two copies of the same tone at
    different amplitudes gave -27 dB vs -47 dB at 6 kHz before
    normalization, and identical values after). Since microphone gain is
    arbitrary and uncontrolled in this app, every AVQI/ABI sub-measure is
    computed on an intensity-normalized copy so results are reproducible
    across recording sessions/devices. (Slope/Tilt/H1-H2/HNR/jitter/shimmer
    are differences or ratios and are already gain-invariant by
    construction; normalizing them again is harmless.)
    """
    normalized = sound.copy()
    call(normalized, "Scale intensity", TARGET_INTENSITY_DB)
    return normalized


def compute_hf_noise_db(sound: parselmouth.Sound, freq_hz: float = 6000.0) -> float:
    """Approximation of ABI's 'high-frequency noise at 6000 Hz' (Hfno):
    the LTAS level (dB) at 6000 Hz, interpolated linearly. At typical adult
    F0s, spectral energy at 6 kHz is dominated by aperiodic/aspiration
    noise rather than harmonic content, so this is a reasonable proxy in
    the absence of the original script's exact noise-isolation method.
    APPROXIMATION -- see module docstring."""
    ltas = call(sound, "To Ltas", 100)
    return float(call(ltas, "Get value at frequency", freq_hz, "Linear"))


@dataclass
class AVQIResult:
    avqi: float
    raw_avqi: float
    was_clipped: bool
    cpps_db: float
    hnr_db: float
    shimmer_local_pct: float
    shimmer_local_db: float
    slope_db: float
    tilt_db: float

    def as_dict(self) -> dict:
        return {
            "avqi": self.avqi,
            "raw_avqi": self.raw_avqi,
            "was_clipped": self.was_clipped,
            "components": {
                "cpps_db": self.cpps_db,
                "hnr_db": self.hnr_db,
                "shimmer_local_pct": self.shimmer_local_pct,
                "shimmer_local_db": self.shimmer_local_db,
                "slope_db": self.slope_db,
                "tilt_db": self.tilt_db,
            },
        }


@dataclass
class ABIResult:
    abi: float
    raw_abi: float
    predicted_grbas_b: float
    was_clipped: bool
    feature_z_scores: dict[str, float]
    max_abs_feature_z: float | None
    out_of_distribution: bool
    cpps_db: float
    jitter_local_pct: float
    gne_max: float
    hf_noise_6000_db: float
    hnr_d_db: float
    h1_h2_db: float
    shimmer_local_db: float
    shimmer_local_pct: float
    psd_s: float

    def as_dict(self) -> dict:
        return {
            "abi": self.abi,
            "raw_abi": self.raw_abi,
            "predicted_grbas_b": self.predicted_grbas_b,
            "was_clipped": self.was_clipped,
            "feature_z_scores": self.feature_z_scores,
            "max_abs_feature_z": self.max_abs_feature_z,
            "out_of_distribution": self.out_of_distribution,
            "components": {
                "cpps_db": self.cpps_db,
                "jitter_local_pct": self.jitter_local_pct,
                "gne_max": self.gne_max,
                "hf_noise_6000_db": self.hf_noise_6000_db,
                "hnr_d_db": self.hnr_d_db,
                "h1_h2_db": self.h1_h2_db,
                "shimmer_local_db": self.shimmer_local_db,
                "shimmer_local_pct": self.shimmer_local_pct,
                "psd_s": self.psd_s,
            },
        }


def _clip_0_10(value: float) -> float:
    return float(np.clip(value, 0.0, 10.0))


_ABI_MODEL_PATH = Path(__file__).parent / "abi_vqd_model.json"
_abi_model = json.loads(_ABI_MODEL_PATH.read_text(encoding="utf-8")) if _ABI_MODEL_PATH.exists() else None


@dataclass(frozen=True)
class ABIScore:
    """Raw and display-safe output from the VQD-fitted breathiness model."""

    displayed: float
    raw: float
    predicted_grbas_b: float
    feature_z_scores: dict[str, float]
    max_abs_feature_z: float | None
    out_of_distribution: bool


# DETERMINISTIC: expose the exact VQD model identity for record provenance; fallback raises if missing.
def abi_model_metadata() -> dict:
    if _abi_model is None:
        raise RuntimeError("analysis/abi_vqd_model.json not found")
    return {
        "model_id": _abi_model.get("model_id", "vqd_lasso_grbas_breathiness_unversioned"),
        "model_sha256": hashlib.sha256(_ABI_MODEL_PATH.read_bytes()).hexdigest(),
        "decision_threshold_0_10": _abi_model.get("decision_threshold_0_10"),
        "method": _abi_model.get("method"),
    }


def _abi_vqd_score(feature_values: dict) -> ABIScore:
    """Score the 9 ABI sub-measures with the model fit directly on VQD's
    real perceptual GRBAS-Breathiness ratings (continuous, 0-3 scale,
    averaged across 3-4 expert raters x 2 trials; ICC .844 interrater/.884
    intrarater), NOT Barsties' published formula, which we verified is
    genuinely broken (see module docstring: negative correlation with real
    breathiness ratings, not just an artifact of SVD's coarse
    diagnosis-category proxy). Currently a Lasso fit (tests/fit_abi_vqd_lasso.py,
    module docstring "Stage 4") rather than the original OLS fit
    (tests/fit_abi_vqd.py), after a real user's case exposed an OLS
    multicollinearity sign-flip. Predicted GRBAS-B is rescaled 0-3 -> 0-10
    for interface compatibility. Returns NaN if any input is non-finite
    (e.g. pitch tracking failed)."""
    if _abi_model is None:
        raise RuntimeError(
            "analysis/abi_vqd_model.json not found -- run tests/fit_abi_vqd_lasso.py "
            "(requires tests/vqd_results.csv from tests/run_vqd_batch.py) to generate it."
        )
    x = np.array([feature_values[f] for f in _abi_model["features"]])
    if not np.all(np.isfinite(x)):
        return ABIScore(
            displayed=float("nan"),
            raw=float("nan"),
            predicted_grbas_b=float("nan"),
            feature_z_scores={},
            max_abs_feature_z=None,
            out_of_distribution=True,
        )
    x_scaled = (x - np.array(_abi_model["scaler_mean"])) / np.array(_abi_model["scaler_scale"])
    predicted_grbas_b = np.dot(x_scaled, _abi_model["coefficients"]) + _abi_model["intercept"]
    raw = float(predicted_grbas_b * _abi_model["output_scale_0_3_to_0_10"])
    displayed = _clip_0_10(raw)
    z_scores = {name: float(value) for name, value in zip(_abi_model["features"], x_scaled)}
    max_abs_z = max((abs(value) for value in z_scores.values()), default=None)
    return ABIScore(
        displayed=displayed,
        raw=raw,
        predicted_grbas_b=float(predicted_grbas_b),
        feature_z_scores=z_scores,
        max_abs_feature_z=max_abs_z,
        out_of_distribution=bool(max_abs_z is not None and max_abs_z >= OOD_MAX_ABS_Z),
    )


def compute_avqi(combined_sound: parselmouth.Sound) -> AVQIResult:
    combined_sound = _intensity_normalized(combined_sound)
    cpps = compute_cpps(combined_sound)
    hnr = compute_hnr(combined_sound)
    shimmer = compute_shimmer(combined_sound)
    ltas = compute_ltas_slope_tilt(combined_sound)

    raw = (
        4.152
        - 0.177 * cpps
        - 0.006 * hnr
        - 0.037 * shimmer["shimmer_local_pct"]
        + 0.941 * shimmer["shimmer_local_db"]
        + 0.01 * ltas["ltas_slope_db"]
        + 0.093 * ltas["ltas_tilt_db"]
    )
    raw_avqi = raw * 2.8902
    avqi = _clip_0_10(raw_avqi)

    return AVQIResult(
        avqi=avqi,
        raw_avqi=float(raw_avqi),
        was_clipped=not np.isclose(avqi, raw_avqi),
        cpps_db=cpps,
        hnr_db=hnr,
        shimmer_local_pct=shimmer["shimmer_local_pct"],
        shimmer_local_db=shimmer["shimmer_local_db"],
        slope_db=ltas["ltas_slope_db"],
        tilt_db=ltas["ltas_tilt_db"],
    )


def compute_abi(combined_sound: parselmouth.Sound) -> ABIResult:
    combined_sound = _intensity_normalized(combined_sound)
    cpps = compute_cpps(combined_sound)
    jitter = compute_jitter(combined_sound)
    gne = compute_gne(combined_sound)
    hf_noise = compute_hf_noise_db(combined_sound)
    hnr_d = compute_hnr(combined_sound)  # APPROXIMATION -- see module docstring
    f0 = compute_f0_stats(combined_sound)
    h1_h2 = compute_h1_h2(combined_sound, f0["f0_mean_hz"])
    shimmer = compute_shimmer(combined_sound)
    psd = compute_psd_seconds(combined_sound)

    abi_score = _abi_vqd_score({
        "abi_sub_cpps_db": cpps,
        "abi_sub_jitter_local_pct": jitter["jitter_local_pct"],
        "abi_sub_gne_max": gne,
        "abi_sub_hf_noise_6000_db": hf_noise,
        "abi_sub_hnr_d_db": hnr_d,
        "abi_sub_h1_h2_db": h1_h2,
        "abi_sub_shimmer_local_db": shimmer["shimmer_local_db"],
        "abi_sub_shimmer_local_pct": shimmer["shimmer_local_pct"],
        "abi_sub_psd_s": psd,
    })

    return ABIResult(
        abi=abi_score.displayed,
        raw_abi=abi_score.raw,
        predicted_grbas_b=abi_score.predicted_grbas_b,
        was_clipped=not np.isclose(abi_score.displayed, abi_score.raw, equal_nan=True),
        feature_z_scores=abi_score.feature_z_scores,
        max_abs_feature_z=abi_score.max_abs_feature_z,
        out_of_distribution=abi_score.out_of_distribution,
        cpps_db=cpps,
        jitter_local_pct=jitter["jitter_local_pct"],
        gne_max=gne,
        hf_noise_6000_db=hf_noise,
        hnr_d_db=hnr_d,
        h1_h2_db=h1_h2,
        shimmer_local_db=shimmer["shimmer_local_db"],
        shimmer_local_pct=shimmer["shimmer_local_pct"],
        psd_s=psd,
    )
