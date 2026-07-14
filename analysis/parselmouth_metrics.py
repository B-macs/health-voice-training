"""The 14 single acoustic parameters, computed via parselmouth/Praat.

Convention (documented, since the spec doesn't pin every parameter to a
specific sample): period-based measures (F0, jitter, shimmer, HNR, GNE,
H1-H2) are computed on the sustained vowel [a:], since Praat's own
recommendations restrict these to sustained phonation. CPPS is computed
separately on both samples (CPPSsv, CPPScs) as explicitly requested. LTAS
Slope/Tilt are computed on the concatenated sample, matching the AVQI
convention (Maryn & Weenink 2015).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import parselmouth
from parselmouth.praat import call

PITCH_FLOOR = 75.0
PITCH_CEILING = 500.0
PERIOD_FLOOR = 0.0001
PERIOD_CEILING = 0.02
MAX_PERIOD_FACTOR = 1.3
MAX_AMPLITUDE_FACTOR = 1.6


def _point_process(sound: parselmouth.Sound) -> parselmouth.Data:
    return call(sound, "To PointProcess (periodic, cc)", PITCH_FLOOR, PITCH_CEILING)


def compute_f0_stats(sound: parselmouth.Sound) -> dict:
    pitch = call(sound, "To Pitch", 0.0, PITCH_FLOOR, PITCH_CEILING)
    mean_hz = call(pitch, "Get mean", 0, 0, "Hertz")
    sd_hz = call(pitch, "Get standard deviation", 0, 0, "Hertz")
    sd_st = call(pitch, "Get standard deviation", 0, 0, "semitones")
    return {
        "f0_mean_hz": float(mean_hz),
        "f0_sd_hz": float(sd_hz),
        "f0_sd_st": float(sd_st),
    }


def compute_jitter(sound: parselmouth.Sound) -> dict:
    pp = _point_process(sound)
    local = call(pp, "Get jitter (local)", 0, 0, PERIOD_FLOOR, PERIOD_CEILING, MAX_PERIOD_FACTOR)
    ppq5 = call(pp, "Get jitter (ppq5)", 0, 0, PERIOD_FLOOR, PERIOD_CEILING, MAX_PERIOD_FACTOR)
    return {
        "jitter_local_pct": float(local) * 100.0,
        "jitter_ppq5_pct": float(ppq5) * 100.0,
    }


def compute_shimmer(sound: parselmouth.Sound) -> dict:
    pp = _point_process(sound)
    args = (0, 0, PERIOD_FLOOR, PERIOD_CEILING, MAX_PERIOD_FACTOR, MAX_AMPLITUDE_FACTOR)
    local = call([sound, pp], "Get shimmer (local)", *args)
    local_db = call([sound, pp], "Get shimmer (local_dB)", *args)
    apq11 = call([sound, pp], "Get shimmer (apq11)", *args)
    return {
        "shimmer_local_pct": float(local) * 100.0,
        "shimmer_local_db": float(local_db),
        "shimmer_apq11_pct": float(apq11) * 100.0,
    }


def compute_hnr(sound: parselmouth.Sound) -> float:
    harmonicity = call(sound, "To Harmonicity (cc)", 0.01, PITCH_FLOOR, 0.1, 1.0)
    hnr = call(harmonicity, "Get mean", 0, 0)
    return float(hnr)


def compute_cpps(sound: parselmouth.Sound) -> float:
    pcg = call(sound, "To PowerCepstrogram", 60, 0.002, 5000, 50)
    cpps = call(
        pcg, "Get CPPS", True, 0.01, 0.001, 60, 330, 0.05,
        "parabolic", 0.001, 0, "Straight", "Robust",
    )
    return float(cpps)


def compute_ltas_slope_tilt(sound: parselmouth.Sound) -> dict:
    ltas = call(sound, "To Ltas", 100)
    nyquist = sound.sampling_frequency / 2.0
    slope = call(ltas, "Get slope", 0, 1000, 1000, nyquist, "energy")

    # Tilt = slope (0-1000 Hz vs 1000-Nyquist, dB) of the *trend line* fitted
    # through the LTAS -- Praat's native "Compute trend line" + "Get slope",
    # not a raw per-Hz regression slope (which is ~1000x too small to match
    # the published AVQI/ABI coefficient's expected order of magnitude).
    trend = call(ltas, "Compute trend line", 0, nyquist)
    tilt = call(trend, "Get slope", 0, 1000, 1000, nyquist, "energy")
    return {"ltas_slope_db": float(slope), "ltas_tilt_db": float(tilt)}


def compute_gne(sound: parselmouth.Sound) -> float:
    # step must stay coarse (Praat default 80 Hz) -- a fine step (e.g. 10 Hz)
    # segfaults Praat's native GNE implementation (verified empirically).
    gne_matrix = call(sound, "To Harmonicity (gne)", 500, 4500, 1000, 80)
    return float(np.max(gne_matrix.values))


def compute_h1_h2(sound: parselmouth.Sound, f0_hz: float, halfwidth_hz: float = 20.0) -> float:
    if not np.isfinite(f0_hz):
        return float("nan")
    spectrum = call(sound, "To Spectrum", "yes")

    def band_energy_db(center: float) -> float:
        energy = call(spectrum, "Get band energy", center - halfwidth_hz, center + halfwidth_hz)
        return 10.0 * np.log10(energy) if energy > 0 else float("-inf")

    h1 = band_energy_db(f0_hz)
    h2 = band_energy_db(2.0 * f0_hz)
    return float(h1 - h2)


def compute_psd_seconds(sound: parselmouth.Sound) -> float:
    """Period standard deviation, in seconds (used as an ABI sub-measure)."""
    pp = _point_process(sound)
    psd = call(pp, "Get stdev period", 0, 0, PERIOD_FLOOR, PERIOD_CEILING, MAX_PERIOD_FACTOR)
    return float(psd)


@dataclass
class SingleParameters:
    f0_mean_hz: float
    f0_sd_hz: float
    f0_sd_st: float
    jitter_local_pct: float
    jitter_ppq5_pct: float
    shimmer_local_pct: float
    shimmer_local_db: float
    shimmer_apq11_pct: float
    hnr_db: float
    cpps_sv_db: float
    cpps_cs_db: float
    ltas_slope_db: float
    ltas_tilt_db: float
    gne: float
    h1_h2_db: float

    def as_dict(self) -> dict:
        return {
            "f0_mean_hz": self.f0_mean_hz,
            "f0_sd_hz": self.f0_sd_hz,
            "f0_sd_st": self.f0_sd_st,
            "jitter_local_pct": self.jitter_local_pct,
            "jitter_ppq5_pct": self.jitter_ppq5_pct,
            "shimmer_local_pct": self.shimmer_local_pct,
            "shimmer_local_db": self.shimmer_local_db,
            "shimmer_apq11_pct": self.shimmer_apq11_pct,
            "hnr_db": self.hnr_db,
            "cpps_sv_db": self.cpps_sv_db,
            "cpps_cs_db": self.cpps_cs_db,
            "ltas_slope_db": self.ltas_slope_db,
            "ltas_tilt_db": self.ltas_tilt_db,
            "gne": self.gne,
            "h1_h2_db": self.h1_h2_db,
        }


def analyze_single_parameters(
    sv_sound: parselmouth.Sound,
    cs_sound: parselmouth.Sound,
    combined_sound: parselmouth.Sound,
) -> SingleParameters:
    f0 = compute_f0_stats(sv_sound)
    jitter = compute_jitter(sv_sound)
    shimmer = compute_shimmer(sv_sound)
    hnr = compute_hnr(sv_sound)
    cpps_sv = compute_cpps(sv_sound)
    cpps_cs = compute_cpps(cs_sound)
    ltas = compute_ltas_slope_tilt(combined_sound)
    gne = compute_gne(sv_sound)
    h1_h2 = compute_h1_h2(sv_sound, f0["f0_mean_hz"])

    return SingleParameters(
        f0_mean_hz=f0["f0_mean_hz"],
        f0_sd_hz=f0["f0_sd_hz"],
        f0_sd_st=f0["f0_sd_st"],
        jitter_local_pct=jitter["jitter_local_pct"],
        jitter_ppq5_pct=jitter["jitter_ppq5_pct"],
        shimmer_local_pct=shimmer["shimmer_local_pct"],
        shimmer_local_db=shimmer["shimmer_local_db"],
        shimmer_apq11_pct=shimmer["shimmer_apq11_pct"],
        hnr_db=hnr,
        cpps_sv_db=cpps_sv,
        cpps_cs_db=cpps_cs,
        ltas_slope_db=ltas["ltas_slope_db"],
        ltas_tilt_db=ltas["ltas_tilt_db"],
        gne=gne,
        h1_h2_db=h1_h2,
    )
