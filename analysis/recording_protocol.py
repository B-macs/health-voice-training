"""Versioned, deterministic capture preparation for Voxplot.

The published German AVQI v03.01 validation equalised a sustained vowel and
voiced connected-speech sample to about three seconds each. Voxplot cannot
claim byte-for-byte parity with the licensed reference script, but it can
avoid feeding arbitrary 0.05--10 second manual trims into its trend model.

This module therefore selects one contiguous, activity-rich three-second
window from each user-approved sample, records transparent quality metadata,
and rejects only mechanically unusable audio. It does not retain audio bytes
and it does not silently change a historical session.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import parselmouth


PROTOCOL_VERSION = "de_windowed_3s_v2"
QUALITY_RULESET_VERSION = "recording_qc_v1"
TARGET_SECONDS = 3.0
FRAME_SECONDS = 0.020
HOP_SECONDS = 0.010
MIN_SIGNAL_DBFS = -50.0
MAX_CLIPPING_FRACTION = 0.02
WARNING_CLIPPING_FRACTION = 0.001
MIN_ACTIVITY_FRACTION = {"sv": 0.85, "cs": 0.55}


@dataclass(frozen=True)
class SampleQuality:
    """Non-audio quality summary for one selected recording."""

    status: str
    duration_seconds: float
    rms_dbfs: float | None
    peak: float
    clipping_fraction: float
    active_fraction: float
    active_seconds: float
    estimated_snr_db: float | None
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    # DETERMINISTIC: serialize non-audio quality findings; fallback is a JSON-safe summary.
    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "rms_dbfs": self.rms_dbfs,
            "peak": self.peak,
            "clipping_fraction": self.clipping_fraction,
            "active_fraction": self.active_fraction,
            "active_seconds": self.active_seconds,
            "estimated_snr_db": self.estimated_snr_db,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class StandardizedSample:
    """A selected three-second analysis window plus its transparent QC."""

    sample_type: str
    sound: parselmouth.Sound | None
    source_seconds: float
    selected_start_seconds: float | None
    selected_end_seconds: float | None
    quality: SampleQuality

    # DETERMINISTIC: expose provenance without returning or persisting audio samples.
    def as_dict(self) -> dict:
        return {
            "sample_type": self.sample_type,
            "source_seconds": self.source_seconds,
            "selected_start_seconds": self.selected_start_seconds,
            "selected_end_seconds": self.selected_end_seconds,
            "target_seconds": TARGET_SECONDS,
            "quality": self.quality.as_dict(),
        }


@dataclass(frozen=True)
class StandardizedPair:
    """The two protocol windows and their combined capture status."""

    sv: StandardizedSample
    cs: StandardizedSample

    # DETERMINISTIC: allow downstream analysis only when both task windows passed hard QC.
    @property
    def is_analysable(self) -> bool:
        return self.sv.sound is not None and self.cs.sound is not None

    # DETERMINISTIC: report the strictest pair-level QC status for provenance and UI.
    @property
    def status(self) -> str:
        statuses = {self.sv.quality.status, self.cs.quality.status}
        if "not_usable" in statuses:
            return "not_usable"
        if "limited" in statuses:
            return "limited"
        return "usable"

    # DETERMINISTIC: serialize pair-level QC; fallback records the strictest sample status.
    def as_dict(self) -> dict:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "quality_ruleset_version": QUALITY_RULESET_VERSION,
            "status": self.status,
            "analysis_allowed": self.is_analysable,
            "sv": self.sv.as_dict(),
            "cs": self.cs.as_dict(),
        }


class RecordingProtocolError(ValueError):
    """Raised only when the selected audio cannot produce a usable window."""


# DETERMINISTIC: reduce a normalized sound to one numeric channel; fallback is channel averaging.
def _mono_samples(sound: parselmouth.Sound) -> np.ndarray:
    values = np.asarray(sound.values, dtype=np.float64)
    if values.ndim == 1:
        return values
    return np.mean(values, axis=0)


# DETERMINISTIC: calculate frame RMS values for a simple energy-based activity proxy.
def _frame_rms(samples: np.ndarray, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    frame = max(1, int(round(FRAME_SECONDS * sample_rate)))
    hop = max(1, int(round(HOP_SECONDS * sample_rate)))
    if len(samples) <= frame:
        return np.array([float(np.sqrt(np.mean(samples ** 2)))]), np.array([0])
    starts = np.arange(0, len(samples) - frame + 1, hop, dtype=int)
    values = np.array([
        float(np.sqrt(np.mean(samples[start:start + frame] ** 2)))
        for start in starts
    ])
    return values, starts


# DETERMINISTIC: identify speech-active frames from relative signal energy; fallback marks silence inactive.
def _activity_mask(frame_rms: np.ndarray) -> np.ndarray:
    if frame_rms.size == 0:
        return np.zeros(0, dtype=bool)
    signal = float(np.percentile(frame_rms, 90))
    floor = float(np.percentile(frame_rms, 10))
    if not math.isfinite(signal) or signal <= 0:
        return np.zeros(frame_rms.shape, dtype=bool)
    threshold = max(10 ** (MIN_SIGNAL_DBFS / 20.0), floor + (signal - floor) * 0.20, signal * 0.10)
    active = frame_rms >= threshold
    # Fill or bridge isolated 10 ms gaps, without treating long silence as speech.
    if active.size >= 3:
        neighbours = np.convolve(active.astype(int), np.ones(3, dtype=int), mode="same")
        active = neighbours >= 2
    return active


# DETERMINISTIC: compute numeric quality evidence for a proposed contiguous window.
def _quality_from_window(
    samples: np.ndarray,
    sample_rate: float,
    sample_type: str,
    active_fraction: float,
) -> SampleQuality:
    duration = len(samples) / sample_rate if sample_rate else 0.0
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
    rms_dbfs = 20.0 * math.log10(rms) if rms > 0 else None
    clipping = float(np.mean(np.abs(samples) >= 0.999)) if samples.size else 0.0
    frame_rms, _ = _frame_rms(samples, sample_rate)
    active = _activity_mask(frame_rms)
    noise_floor = float(np.percentile(frame_rms, 10)) if frame_rms.size else 0.0
    signal_level = float(np.median(frame_rms[active])) if active.any() else 0.0
    if active.any() and noise_floor > 0 and signal_level > noise_floor * 1.10:
        estimated_snr = 20.0 * math.log10(
            max(signal_level, 1e-12) / max(noise_floor, 1e-12)
        )
    else:
        estimated_snr = None

    failures: list[str] = []
    warnings: list[str] = []
    required_activity = MIN_ACTIVITY_FRACTION[sample_type]
    if duration + 1e-9 < TARGET_SECONDS:
        failures.append(f"{sample_type} selection is shorter than {TARGET_SECONDS:g} seconds")
    if rms_dbfs is None or rms_dbfs < MIN_SIGNAL_DBFS:
        failures.append(f"{sample_type} signal is too quiet or silent")
    if active_fraction < required_activity:
        failures.append(
            f"{sample_type} has too little active signal ({active_fraction:.0%}; need {required_activity:.0%})"
        )
    if clipping >= MAX_CLIPPING_FRACTION:
        failures.append(f"{sample_type} is heavily clipped ({clipping:.1%})")
    elif clipping >= WARNING_CLIPPING_FRACTION:
        warnings.append(f"{sample_type} contains clipped samples ({clipping:.2%})")
    if estimated_snr is not None and estimated_snr < 10.0:
        warnings.append(f"{sample_type} has limited signal-to-noise separation ({estimated_snr:.1f} dB estimate)")

    status = "not_usable" if failures else ("limited" if warnings else "usable")
    return SampleQuality(
        status=status,
        duration_seconds=round(duration, 4),
        rms_dbfs=round(rms_dbfs, 2) if rms_dbfs is not None else None,
        peak=round(peak, 6),
        clipping_fraction=round(clipping, 8),
        active_fraction=round(active_fraction, 4),
        active_seconds=round(active_fraction * duration, 4),
        estimated_snr_db=round(estimated_snr, 2) if estimated_snr is not None else None,
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


# DETERMINISTIC: choose a contiguous 3-second window with the most active signal; fallback is no window.
def _best_window_start(
    samples: np.ndarray,
    sample_rate: float,
    target_samples: int,
) -> tuple[int, float] | None:
    if len(samples) < target_samples:
        return None
    frame_rms, frame_starts = _frame_rms(samples, sample_rate)
    active = _activity_mask(frame_rms)
    if not active.any():
        return 0, 0.0
    frame_centres = frame_starts + max(1, int(round(FRAME_SECONDS * sample_rate))) / 2.0
    hop = max(1, int(round(HOP_SECONDS * sample_rate)))
    starts = np.arange(0, len(samples) - target_samples + 1, hop, dtype=int)
    if starts[-1] != len(samples) - target_samples:
        starts = np.append(starts, len(samples) - target_samples)
    target_centre = len(samples) / 2.0
    best: tuple[float, float, int] | None = None
    for start in starts:
        in_window = (frame_centres >= start) & (frame_centres < start + target_samples)
        fraction = float(np.mean(active[in_window])) if in_window.any() else 0.0
        # Prefer the centre only when candidate windows have equal activity;
        # this avoids selecting a vowel onset/offset by accident.
        midpoint_distance = abs((start + target_samples / 2.0) - target_centre) / max(len(samples), 1)
        score = fraction - midpoint_distance * 1e-4
        candidate = (score, fraction, int(start))
        if best is None or candidate[0] > best[0]:
            best = candidate
    assert best is not None
    return best[2], best[1]


# DETERMINISTIC: standardize a manually approved sample; fallback reports a non-usable quality result.
def standardize_sample(sound: parselmouth.Sound, sample_type: str) -> StandardizedSample:
    if sample_type not in MIN_ACTIVITY_FRACTION:
        raise ValueError("sample_type must be 'sv' or 'cs'")
    samples = _mono_samples(sound)
    sample_rate = float(sound.sampling_frequency)
    source_seconds = len(samples) / sample_rate if sample_rate else 0.0
    target_samples = int(round(TARGET_SECONDS * sample_rate))
    selected = _best_window_start(samples, sample_rate, target_samples)
    if selected is None:
        quality = _quality_from_window(samples, sample_rate, sample_type, active_fraction=0.0)
        return StandardizedSample(sample_type, None, source_seconds, None, None, quality)

    start, active_fraction = selected
    window = samples[start:start + target_samples]
    quality = _quality_from_window(window, sample_rate, sample_type, active_fraction)
    if quality.status == "not_usable":
        return StandardizedSample(sample_type, None, source_seconds, start / sample_rate, (start + target_samples) / sample_rate, quality)
    standardized = parselmouth.Sound(window, sampling_frequency=sample_rate)
    return StandardizedSample(
        sample_type,
        standardized,
        source_seconds,
        start / sample_rate,
        (start + target_samples) / sample_rate,
        quality,
    )


# DETERMINISTIC: standardize both tasks together; fallback preserves per-sample failure evidence.
def standardize_pair(sv_sound: parselmouth.Sound, cs_sound: parselmouth.Sound) -> StandardizedPair:
    return StandardizedPair(
        sv=standardize_sample(sv_sound, "sv"),
        cs=standardize_sample(cs_sound, "cs"),
    )


# DETERMINISTIC: create a concise retry message from QC failures; fallback names the affected task.
def protocol_error_message(pair: StandardizedPair) -> str:
    failures = [
        *pair.sv.quality.failures,
        *pair.cs.quality.failures,
    ]
    detail = "; ".join(failures) if failures else "recording quality could not be established"
    return f"Recording not saved: {detail}. Please record again in a quiet room."
