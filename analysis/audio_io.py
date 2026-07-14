"""Load audio from bytes/paths and normalize to a fixed analysis format.

All analysis in this project assumes mono, 44.1 kHz audio so metrics are
comparable across recording sessions/devices/browsers.
"""
from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call

TARGET_SR = 44100


def ensure_wav_bytes(data: bytes) -> bytes:
    """Browsers record audio as WebM/Opus (Streamlit's own audio_input
    widget picks the first MediaRecorder mimeType the browser supports from
    ["audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/mp3"] --
    on Chrome/Edge that's always audio/webm), not WAV, regardless of the
    ".wav" filename the widget gives it. libsndfile (soundfile's backend)
    can't decode WebM at all, so a live mic recording that reaches
    load_wav_bytes unchanged fails with "Format not recognised" -- uploaded
    .wav files are unaffected since they're already real WAV.

    Transcodes via the ffmpeg binary bundled by imageio-ffmpeg (no system
    ffmpeg install required) whenever the bytes aren't already something
    soundfile can read directly; a no-op (returns `data` unchanged) for
    already-valid input, so this is safe to call unconditionally."""
    try:
        sf.read(io.BytesIO(data), frames=1)
        return data
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "input"
        dst_path = Path(tmp_dir) / "output.wav"
        src_path.write_bytes(data)
        result = subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(src_path),
                "-ar", str(TARGET_SR), "-ac", "1", str(dst_path),
            ],
            capture_output=True,
        )
        if result.returncode != 0 or not dst_path.exists():
            stderr_tail = result.stderr.decode(errors="replace")[-500:]
            raise ValueError(f"ffmpeg failed to transcode recorded audio: {stderr_tail}")
        return dst_path.read_bytes()


def _to_parselmouth_sound(samples: np.ndarray, sr: int) -> parselmouth.Sound:
    if samples.ndim == 1:
        data = samples[np.newaxis, :]
    else:
        # soundfile returns (n_frames, n_channels); parselmouth wants (n_channels, n_frames)
        data = samples.T
    return parselmouth.Sound(data.astype(np.float64), sampling_frequency=sr)


def normalize_sound(sound: parselmouth.Sound) -> parselmouth.Sound:
    """Ensure mono + TARGET_SR, regardless of the source's original format."""
    if sound.n_channels > 1:
        sound = call(sound, "Convert to mono")
    if abs(sound.sampling_frequency - TARGET_SR) > 1e-6:
        sound = call(sound, "Resample", TARGET_SR, 50)
    return sound


def load_wav_bytes(data: bytes) -> parselmouth.Sound:
    data = ensure_wav_bytes(data)
    samples, sr = sf.read(io.BytesIO(data), dtype="float64", always_2d=False)
    sound = _to_parselmouth_sound(np.asarray(samples), sr)
    return normalize_sound(sound)


def load_wav_file(path: str) -> parselmouth.Sound:
    with open(path, "rb") as f:
        return load_wav_bytes(f.read())


def concatenate(*sounds: parselmouth.Sound) -> parselmouth.Sound:
    """Concatenate normalized sounds end-to-end (used to build the AVQI/ABI sample)."""
    normalized = [normalize_sound(s) for s in sounds]
    return call(normalized, "Concatenate")
