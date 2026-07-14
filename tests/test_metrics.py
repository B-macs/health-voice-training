"""G3 (runs end-to-end without exceptions) and G4 (finite, plausible values)."""
import math

import parselmouth

from analysis.audio_io import concatenate
from analysis.parselmouth_metrics import analyze_single_parameters


def _assert_finite(name, value):
    assert isinstance(value, float), f"{name} is not a float: {type(value)}"
    assert math.isfinite(value), f"{name} is not finite: {value}"


def test_synthetic_tone_smoke():
    """A pure dummy tone (no realistic voice model needed) must not crash
    and must produce finite numbers -- the minimal synthetic/dummy-tone gate."""
    sr = 44100
    import numpy as np
    t = np.arange(int(sr * 3.0)) / sr
    sv = parselmouth.Sound(0.3 * np.sin(2 * np.pi * 150 * t), sampling_frequency=sr)
    t2 = np.arange(int(sr * 6.0)) / sr
    cs = parselmouth.Sound(0.3 * np.sin(2 * np.pi * 140 * t2), sampling_frequency=sr)
    combined = concatenate(sv, cs)

    params = analyze_single_parameters(sv, cs, combined).as_dict()
    for name, value in params.items():
        _assert_finite(name, value)


def test_realistic_voice_all_14_parameters_plausible(clean_sv, clean_cs):
    combined = concatenate(clean_sv, clean_cs)
    params = analyze_single_parameters(clean_sv, clean_cs, combined).as_dict()

    # 15 dict keys represent the 14 conceptual parameters from the spec:
    # "F0 SD (Hz and semitones)" is one conceptual parameter reported as
    # two unit values (f0_sd_hz, f0_sd_st).
    assert len(params) == 15
    for name, value in params.items():
        _assert_finite(name, value)

    assert 50 < params["f0_mean_hz"] < 400
    assert params["jitter_local_pct"] >= 0
    assert params["shimmer_local_pct"] >= 0
    assert params["hnr_db"] > 0
    assert 0.0 <= params["gne"] <= 1.0


def test_breathy_voice_worse_cpps_and_hnr_than_clean(clean_sv, clean_cs, breathy_sv, breathy_cs):
    """Directional sanity check on the raw acoustic parameters (not the
    composite indices): a breathier voice should show lower CPPS and lower
    HNR than a clean voice. These are direct physical measurements, unlike
    AVQI/ABI's multivariate regression, so this check is far more reliable
    than trying to sanity-check the indices with single-factor synthetic
    perturbations (see analysis/indices.py docstring)."""
    clean_combined = concatenate(clean_sv, clean_cs)
    breathy_combined = concatenate(breathy_sv, breathy_cs)

    clean_params = analyze_single_parameters(clean_sv, clean_cs, clean_combined).as_dict()
    breathy_params = analyze_single_parameters(breathy_sv, breathy_cs, breathy_combined).as_dict()

    assert breathy_params["cpps_sv_db"] < clean_params["cpps_sv_db"]
    assert breathy_params["hnr_db"] < clean_params["hnr_db"]
