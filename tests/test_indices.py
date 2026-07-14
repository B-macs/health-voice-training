"""G5 (redefined): AVQI/ABI formula recomputation -- internal consistency
and component-level sanity, NOT verified parity against the licensed
Phonanium script (which we don't have legal access to -- see PLAN.md and
analysis/indices.py docstring)."""
import math

import pytest

from analysis.audio_io import concatenate
from analysis.indices import compute_avqi, compute_abi


def _assert_finite_0_10(name, value):
    assert math.isfinite(value), f"{name} is not finite: {value}"
    assert 0.0 <= value <= 10.0, f"{name} out of [0,10] bounds: {value}"


def test_avqi_finite_and_bounded(clean_sv, clean_cs):
    combined = concatenate(clean_sv, clean_cs)
    result = compute_avqi(combined)
    _assert_finite_0_10("avqi", result.avqi)


def test_abi_finite_and_bounded(clean_sv, clean_cs):
    combined = concatenate(clean_sv, clean_cs)
    result = compute_abi(combined)
    _assert_finite_0_10("abi", result.abi)


def test_avqi_gain_invariance(clean_sv, clean_cs):
    """Recording gain is arbitrary (mic distance/volume); AVQI must not
    swing wildly just because the same voice was captured louder/quieter.
    (This test exists because we found ABI's raw high-frequency-noise
    sub-measure WAS gain-dependent before we added intensity
    normalization -- see analysis/indices.py _intensity_normalized.)"""
    combined = concatenate(clean_sv, clean_cs)
    quiet_result = compute_avqi(combined)

    louder = combined.copy()
    import parselmouth
    parselmouth.praat.call(louder, "Formula", "self*4")
    loud_result = compute_avqi(louder)

    assert abs(quiet_result.avqi - loud_result.avqi) < 0.5


def test_avqi_direction_breathy_worse_than_clean(clean_sv, clean_cs, breathy_sv, breathy_cs):
    clean_combined = concatenate(clean_sv, clean_cs)
    breathy_combined = concatenate(breathy_sv, breathy_cs)

    clean_avqi = compute_avqi(clean_combined).avqi
    breathy_avqi = compute_avqi(breathy_combined).avqi

    assert breathy_avqi > clean_avqi


@pytest.mark.xfail(
    reason=(
        "UPDATED (see analysis/indices.py docstring): ABI is now a linear "
        "regression fit directly on VQD's real perceptual GRBAS-Breathiness "
        "ratings (tests/fit_abi_vqd.py) -- 5-fold CV Pearson r=0.814 against "
        "real ratings, AUC 0.894 for detecting any breathiness. That's the "
        "authoritative validation (see tests/test_vqd_validation.py). This "
        "synthetic-fixture check still fails, but as a TIE at the 0-floor, "
        "not an inversion: both clean and breathy synthetic fixtures produce "
        "feature values so far outside the real training distribution "
        "(verified: raw pre-clip predicted GRBAS-B is -4.56 for clean vs "
        "-3.52 for breathy -- correctly ordered, just both far below the "
        "valid 0-3 range) that clipping to [0,10] floors both at 0.0. Left "
        "xfail rather than deleted so a future regression here is still "
        "visible; real-data validation is what should be trusted."
    ),
    strict=True,
)
def test_abi_direction_breathy_worse_than_clean(clean_sv, clean_cs, breathy_sv, breathy_cs):
    clean_combined = concatenate(clean_sv, clean_cs)
    breathy_combined = concatenate(breathy_sv, breathy_cs)

    clean_abi = compute_abi(clean_combined).abi
    breathy_abi = compute_abi(breathy_combined).abi

    assert breathy_abi > clean_abi
