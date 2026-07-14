"""Deterministic capture-protocol and non-audio quality checks."""
from __future__ import annotations

import numpy as np
import parselmouth

from analysis.recording_protocol import PROTOCOL_VERSION, TARGET_SECONDS, standardize_pair, standardize_sample


SR = 44_100


def _tone(seconds: float, *, amplitude: float = 0.25, leading_silence: float = 0.0) -> parselmouth.Sound:
    active_n = int(seconds * SR)
    t = np.arange(active_n) / SR
    active = amplitude * np.sin(2 * np.pi * 160 * t)
    silence = np.zeros(int(leading_silence * SR))
    return parselmouth.Sound(np.concatenate([silence, active, silence]), sampling_frequency=SR)


def test_protocol_selects_exact_three_second_activity_rich_windows():
    pair = standardize_pair(
        _tone(4.0, leading_silence=0.5),
        _tone(5.0, leading_silence=0.5),
    )

    assert pair.is_analysable
    assert pair.status == "usable"
    assert pair.as_dict()["protocol_version"] == PROTOCOL_VERSION
    assert pair.sv.sound is not None and pair.cs.sound is not None
    assert pair.sv.sound.duration == TARGET_SECONDS
    assert pair.cs.sound.duration == TARGET_SECONDS
    assert pair.sv.quality.active_fraction >= 0.85
    assert pair.cs.quality.active_fraction >= 0.55


def test_protocol_rejects_a_selection_shorter_than_three_seconds():
    result = standardize_sample(_tone(2.5), "sv")

    assert result.sound is None
    assert result.quality.status == "not_usable"
    assert any("shorter" in reason for reason in result.quality.failures)


def test_protocol_rejects_heavily_clipped_audio():
    clipped = parselmouth.Sound(np.ones(int(4 * SR)), sampling_frequency=SR)
    result = standardize_sample(clipped, "sv")

    assert result.sound is None
    assert result.quality.status == "not_usable"
    assert any("clipped" in reason for reason in result.quality.failures)
