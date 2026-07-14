import io

import numpy as np
import parselmouth
import pytest
import soundfile as sf
from scipy import signal

SR = 44100


def synth_voice(dur_s: float, f0: float = 150.0, n_harmonics: int = 25,
                 breathiness: float = 0.08, jitter_amt: float = 0.0,
                 shimmer_amt: float = 0.0, seed: int = 0) -> np.ndarray:
    """A more realistic-than-a-pure-tone synthetic vowel: harmonic series
    with -6dB/octave rolloff (typical glottal source shape) optionally
    mixed with high-pass 'aspiration' noise to simulate breathiness."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur_s)
    t = np.arange(n) / SR
    phase = 2 * np.pi * f0 * t
    if jitter_amt:
        phase = phase + np.cumsum(jitter_amt * rng.standard_normal(n))
    sig = np.zeros(n)
    for k in range(1, n_harmonics):
        amp = 1.0 / k
        if shimmer_amt:
            amp = amp * (1 + shimmer_amt * rng.standard_normal())
        sig += amp * np.sin(k * phase)
    sig = sig / np.max(np.abs(sig)) * 0.5
    if breathiness > 0:
        noise = rng.standard_normal(n)
        sos = signal.butter(4, 1500, btype="highpass", fs=SR, output="sos")
        aspiration = signal.sosfilt(sos, noise)
        aspiration = aspiration / np.max(np.abs(aspiration)) * 0.5
        sig = (1 - breathiness) * sig + breathiness * aspiration
    return sig


@pytest.fixture
def clean_sv():
    return parselmouth.Sound(synth_voice(3.0, f0=150.0, seed=10), sampling_frequency=SR)


@pytest.fixture
def clean_cs():
    return parselmouth.Sound(synth_voice(6.0, f0=140.0, seed=11), sampling_frequency=SR)


@pytest.fixture
def breathy_sv():
    return parselmouth.Sound(
        synth_voice(3.0, f0=150.0, breathiness=0.35, jitter_amt=0.002, shimmer_amt=0.03, seed=20),
        sampling_frequency=SR,
    )


@pytest.fixture
def breathy_cs():
    return parselmouth.Sound(
        synth_voice(6.0, f0=140.0, breathiness=0.35, jitter_amt=0.002, shimmer_amt=0.03, seed=21),
        sampling_frequency=SR,
    )


def sound_to_wav_bytes(sound: parselmouth.Sound) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, sound.values.T, int(sound.sampling_frequency), format="WAV", subtype="PCM_16")
    return buf.getvalue()
