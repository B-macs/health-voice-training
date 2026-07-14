"""Normal-range reference values and in/out-of-range flagging.

Defaults below are indicative values commonly cited in the voice-acoustics
literature (Praat's own voice-report thresholds; Maryn/Barsties AVQI & ABI
validation papers; standard clinical acoustics references such as Baken &
Orlikoff). They are NOT a substitute for locale/population-specific
clinical norms -- treat them as a configurable starting point, not a
diagnostic cutoff. Swap `DEFAULT_NORMS` (or pass an override dict) for
validated values in a specific language/population before clinical use.

A norm entry is either:
  - {"max": x}            -- in range if value <= x
  - {"min": x}             -- in range if value >= x
  - {"min": x, "max": y}   -- in range if x <= value <= y
  - {"max": x, "higher_is_better": False}  is the default direction; set
    "higher_is_better": True when a *low* value (not high) is the concern
    (e.g. HNR, CPPS, GNE: low is abnormal).
Norms with no established single cutoff are stored with "note" only and
`in_range` will be None (unknown), not guessed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import ANALYSIS_LANGUAGE


@dataclass
class NormRange:
    min: Optional[float] = None
    max: Optional[float] = None
    note: str = ""

    def in_range(self, value: float) -> Optional[bool]:
        if value is None or value != value:  # NaN check without importing math/numpy here
            return None
        if self.min is None and self.max is None:
            return None
        ok = True
        if self.min is not None:
            ok = ok and value >= self.min
        if self.max is not None:
            ok = ok and value <= self.max
        return ok

    def as_dict(self) -> dict:
        return {"min": self.min, "max": self.max, "note": self.note}


# Adult, language-unspecified, indicative defaults. sample_length here refers
# to the ~3s sustained vowel / ~6s continuous speech convention used by this
# app; norms sourced from short-sample clinical literature may not directly
# apply to much longer/shorter recordings.
DEFAULT_NORMS: dict[str, NormRange] = {
    "f0_mean_hz": NormRange(min=80, max=260, note="Wide adult male+female speaking-F0 band; prefer sex-specific norms (M ~100-146 Hz, F ~189-224 Hz)."),
    "f0_sd_hz": NormRange(max=20, note="Sustained-vowel F0 variability; running speech has intrinsically higher SD."),
    "f0_sd_st": NormRange(max=1.0, note="Sustained-vowel F0 variability in semitones."),
    "jitter_local_pct": NormRange(max=1.040, note="Commonly cited Praat voice-report upper bound for normal voices."),
    "jitter_ppq5_pct": NormRange(max=0.84, note="Commonly cited Praat voice-report upper bound."),
    "shimmer_local_pct": NormRange(max=3.81, note="Commonly cited Praat voice-report upper bound."),
    "shimmer_local_db": NormRange(max=0.35, note="Commonly cited Praat voice-report upper bound."),
    "shimmer_apq11_pct": NormRange(max=3.5, note="Approximate; less standardized than local/local_dB."),
    "hnr_db": NormRange(min=20.0, note="Below ~20 dB commonly associated with dysphonia (cc method)."),
    "cpps_sv_db": NormRange(min=14.0, note="Approximate; CPPS norms vary by corpus/implementation."),
    "cpps_cs_db": NormRange(min=8.0, note="Continuous speech CPPS is typically lower than sustained-vowel CPPS."),
    "ltas_slope_db": NormRange(note="No single universal cutoff; used comparatively/within AVQI, not as a standalone screening cutoff."),
    "ltas_tilt_db": NormRange(note="No single universal cutoff; used comparatively/within AVQI."),
    "gne": NormRange(min=0.5, note="Values closer to 1 = more periodic/less breathy; <0.5 often associated with breathiness."),
    "h1_h2_db": NormRange(note="No single universal cutoff; more positive = more breathy, but strongly register/gender dependent."),
    "avqi": NormRange(max=2.85, note="Widely cited international default cutoff (Maryn & Weenink); validated cutoffs vary by language (~1.8-3.5)."),
    "abi": NormRange(max=2.10, note="Youden-optimal threshold of our VQD-fitted Lasso regression (tests/fit_abi_vqd_lasso.py) for any perceived breathiness (AUC 0.888, sens 0.81, spec 0.82) -- NOT the Barsties published ABI's Dutch cutoff, which validated a formula this project no longer uses (proved broken against real ratings). See analysis/indices.py module docstring."),
}

# AVQI: German-validated cutoff (Barsties v Latoszek et al., "Validation of
# the Acoustic Voice Quality Index Version 03.01 and Acoustic Breathiness
# Index in German", J Voice 2020): sensitivity 79%, specificity 92%, AUC 0.888.
# ABI: NOT the German literature cutoff (3.42) -- that was validated for
# Barsties' published formula, which analysis/indices.py no longer uses
# (proved broken even against real perceptual breathiness ratings, not just
# SVD's coarse diagnosis labels -- see its module docstring). This is the
# Youden-optimal threshold (2.10 on the rescaled 0-10 scale) for detecting
# "any breathiness present" (GRBAS-Breathiness > 0.5) using our VQD-fitted
# Lasso regression (tests/fit_abi_vqd_lasso.py): AUC 0.888, sensitivity 0.81,
# specificity 0.82. Fit on real (American English) perceptual ratings, not
# German-specific, so used as the general default too (see DEFAULT_NORMS)
# pending a German-specific breathiness validation. Re-derive by re-running
# fit_abi_vqd_lasso.py if the model is refit again (previously
# tests/fit_abi_vqd.py's plain-OLS fit -- superseded after a real user's
# confirmed-breathy case exposed a multicollinearity sign-flip between
# shimmer_local_db/shimmer_local_pct; see analysis/indices.py docstring).
GERMAN_NORMS_OVERRIDE: dict[str, NormRange] = {
    "avqi": NormRange(max=2.70, note="German validation cutoff (Barsties v Latoszek et al. 2020, J Voice): sensitivity 79%, specificity 92%, AUC=0.888."),
    "abi": NormRange(max=2.10, note="Youden-optimal threshold of our VQD-fitted Lasso regression (tests/fit_abi_vqd_lasso.py) for detecting any perceived breathiness, NOT the Barsties German literature cutoff -- see analysis/indices.py module docstring. AUC 0.888, sensitivity 0.81, specificity 0.82. Not German-specific (VQD is American English)."),
}

NORMS_BY_LANGUAGE: dict[str, dict[str, NormRange]] = {
    "de": {**DEFAULT_NORMS, **GERMAN_NORMS_OVERRIDE},
}


def get_norms(language: str = ANALYSIS_LANGUAGE) -> dict[str, NormRange]:
    return NORMS_BY_LANGUAGE.get(language, DEFAULT_NORMS)


def flag(parameter: str, value: float, norms: dict[str, NormRange] = None) -> dict:
    norms = norms if norms is not None else get_norms()
    norm = norms.get(parameter)
    if norm is None:
        return {"norm": None, "in_range": None}
    return {"norm": norm.as_dict(), "in_range": norm.in_range(value)}


def flag_all(values: dict[str, float], norms: dict[str, NormRange] = None) -> dict[str, dict]:
    return {name: flag(name, value, norms) for name, value in values.items()}
