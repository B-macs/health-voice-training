import io

import numpy as np
import soundfile as sf

from analysis.audio_io import TARGET_SR, concatenate, load_wav_bytes


def test_load_wav_bytes_resamples_and_monos():
    sr = 22050
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    stereo = np.stack([np.sin(2 * np.pi * 150 * t), np.sin(2 * np.pi * 150 * t) * 0.8], axis=1)
    buf = io.BytesIO()
    sf.write(buf, stereo, sr, format="WAV")
    sound = load_wav_bytes(buf.getvalue())

    assert sound.n_channels == 1
    assert abs(sound.sampling_frequency - TARGET_SR) < 1e-6
    assert abs(sound.duration - 0.5) < 0.01


def test_concatenate_sums_durations():
    sr = 44100
    t1 = np.linspace(0, 1.0, sr, endpoint=False)
    t2 = np.linspace(0, 2.0, 2 * sr, endpoint=False)
    buf1, buf2 = io.BytesIO(), io.BytesIO()
    sf.write(buf1, np.sin(2 * np.pi * 150 * t1), sr, format="WAV")
    sf.write(buf2, np.sin(2 * np.pi * 140 * t2), sr, format="WAV")

    s1 = load_wav_bytes(buf1.getvalue())
    s2 = load_wav_bytes(buf2.getvalue())
    combined = concatenate(s1, s2)

    assert abs(combined.duration - 3.0) < 0.01
