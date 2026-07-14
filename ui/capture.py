"""Waveform preview + trim/select UI for the recording capture flow.

Mirrors the reference VOXplot desktop app's record-review step: after
capturing/uploading a sample, the user sees its waveform, drags a
two-handle range slider to select the target utterance within it, can
audition either the full clip or just the selection, and only advances
once they've explicitly accepted a selection (or re-recorded from
scratch). Every recording/upload is truncated server-side to `max_seconds`
before any of this renders -- there's no reliable way to force the
browser's own MediaRecorder to auto-stop from outside Streamlit's compiled
audio_input widget, so the equivalent "fixed recording window" behavior is
enforced here instead, after capture.
"""
from __future__ import annotations

import io

import numpy as np
import soundfile as sf
import streamlit as st

from config import t
from ui.styles import COLORS
from ui.html_utils import flatten
from analysis.audio_io import ensure_wav_bytes
from analysis.recording_protocol import TARGET_SECONDS


def wav_duration_seconds(audio_bytes: bytes) -> float:
    info = sf.info(io.BytesIO(audio_bytes))
    return float(info.frames) / float(info.samplerate)


# DETERMINISTIC: identify a coarse browser/upload container from magic bytes; fallback is "unknown".
def detect_audio_container(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
        return "wav"
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm_or_matroska"
    if audio_bytes.startswith(b"OggS"):
        return "ogg"
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "mp3"
    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return "mp4_or_m4a"
    return "unknown"


def _write_wav(data: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV")
    return buf.getvalue()


def truncate_to_max_seconds(audio_bytes: bytes, max_seconds: float) -> bytes:
    data, sr = sf.read(io.BytesIO(audio_bytes), always_2d=False)
    max_frames = int(max_seconds * sr)
    if len(data) <= max_frames:
        return audio_bytes
    return _write_wav(data[:max_frames], sr)


def trim_wav_bytes(audio_bytes: bytes, start_s: float, end_s: float) -> bytes:
    data, sr = sf.read(io.BytesIO(audio_bytes), always_2d=False)
    start_frame = max(0, int(start_s * sr))
    end_frame = min(len(data), int(end_s * sr))
    return _write_wav(data[start_frame:end_frame], sr)


def waveform_peaks(audio_bytes: bytes, n_buckets: int = 120) -> list[float]:
    data, _ = sf.read(io.BytesIO(audio_bytes), always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    chunk = max(1, len(data) // n_buckets)
    return [float(np.max(np.abs(data[i:i + chunk]))) for i in range(0, len(data), chunk)][:n_buckets]


def render_waveform_bars(audio_bytes: bytes) -> None:
    peaks = waveform_peaks(audio_bytes)
    if not peaks:
        return
    max_peak = max(peaks) or 1.0
    bars = "".join(
        f'<div style="flex:1;background:{COLORS["optimal"]};opacity:0.75;'
        f'height:{max(3, (p / max_peak) * 40):.0f}px;border-radius:2px;"></div>'
        for p in peaks
    )
    st.markdown(flatten(f"""
        <div class="vx-section-label">{t("capture_waveform_title")}</div>
        <div style="display:flex;align-items:flex-end;gap:2px;height:44px;">{bars}</div>
        """), unsafe_allow_html=True)


def _reset_sample_state(prefix: str) -> None:
    version = st.session_state.get(f"{prefix}_widget_version", 0)
    st.session_state[f"{prefix}_widget_version"] = version + 1
    for suffix in (
        "last_raw", "source_bytes", "trim", "accepted", "accepted_trim", "capture_meta",
        "source_kind", "source_container", "source_duration_seconds", "server_truncated",
    ):
        st.session_state.pop(f"{prefix}_{suffix}", None)
    st.session_state.pop("last_error", None)


def reset_capture_state(*prefixes: str) -> None:
    for prefix in prefixes:
        _reset_sample_state(prefix)


def clear_accepted(prefix: str) -> None:
    """Drop just the accepted/accepted_trim state for one sample, WITHOUT
    bumping its widget_version or clearing source_bytes/trim -- the
    recorded audio, waveform, and trim selection stay exactly as they
    were. Used when a later step (e.g. run_analysis) fails after this
    sample was accepted: render_sample_capture falls back to its
    "not yet accepted" state so the user can just hit Accept again to
    retry, instead of needing to re-record from scratch."""
    st.session_state.pop(f"{prefix}_accepted", None)
    st.session_state.pop(f"{prefix}_accepted_trim", None)


def render_sample_capture(
    prefix: str,
    record_label_key: str,
    upload_label_key: str,
    max_seconds: float = 10.0,
) -> bytes | None:
    """Renders mic/upload capture + waveform + trim-select + audition +
    accept for one sample (sustained vowel or continuous speech). Returns
    the accepted, trimmed WAV bytes once the user clicks Accept (and the
    selection hasn't changed since), else None."""
    version = st.session_state.get(f"{prefix}_widget_version", 0)
    mic = st.audio_input(t(record_label_key), key=f"{prefix}_mic_{version}")
    upload = st.file_uploader(t(upload_label_key), type=["wav"], key=f"{prefix}_upload_{version}")
    raw_bytes = upload.getvalue() if upload is not None else (mic.getvalue() if mic is not None else None)

    if raw_bytes is None:
        return None

    try:
        if st.session_state.get(f"{prefix}_last_raw") != raw_bytes:
            # Do all the fallible work on locals first -- only commit to
            # session_state once every step succeeds, so a failed attempt
            # (e.g. ffmpeg transcoding fails) doesn't get remembered as
            # "already handled" while leaving stale source/accepted state
            # from a previous, unrelated recording in place.
            wav_bytes = ensure_wav_bytes(raw_bytes)
            original_duration = wav_duration_seconds(wav_bytes)
            truncated = truncate_to_max_seconds(wav_bytes, max_seconds)
            duration = round(wav_duration_seconds(truncated), 2)

            st.session_state[f"{prefix}_last_raw"] = raw_bytes
            st.session_state[f"{prefix}_source_bytes"] = truncated
            st.session_state[f"{prefix}_trim"] = (0.0, duration)
            st.session_state[f"{prefix}_source_kind"] = "upload" if upload is not None else "microphone"
            st.session_state[f"{prefix}_source_container"] = detect_audio_container(raw_bytes)
            st.session_state[f"{prefix}_source_duration_seconds"] = round(original_duration, 4)
            st.session_state[f"{prefix}_server_truncated"] = original_duration > max_seconds
            st.session_state.pop(f"{prefix}_accepted", None)
            st.session_state.pop(f"{prefix}_accepted_trim", None)
            st.session_state.pop(f"{prefix}_capture_meta", None)

        source_bytes = st.session_state[f"{prefix}_source_bytes"]
        duration = round(wav_duration_seconds(source_bytes), 2)
    except Exception:
        st.error(t("capture_load_error"))
        return None

    render_waveform_bars(source_bytes)
    st.caption(t("capture_protocol_hint"))

    if duration <= 0.05:
        st.warning(t("capture_too_short"))
        return None

    start, end = st.slider(
        t("capture_trim_instruction"),
        min_value=0.0, max_value=duration,
        value=st.session_state[f"{prefix}_trim"],
        step=0.05, format="%.2fs",
        key=f"{prefix}_trim_slider_{version}",
    )
    st.session_state[f"{prefix}_trim"] = (start, end)
    selection_bytes = trim_wav_bytes(source_bytes, start, end)
    selection_seconds = end - start

    col1, col2 = st.columns(2)
    with col1:
        st.caption(t("capture_play_all"))
        st.audio(source_bytes)
    with col2:
        st.caption(t("capture_play_selection"))
        st.audio(selection_bytes)

    if st.session_state.get(f"{prefix}_accepted") is not None:
        if st.session_state.get(f"{prefix}_accepted_trim") != (start, end):
            st.session_state.pop(f"{prefix}_accepted", None)
            st.session_state.pop(f"{prefix}_accepted_trim", None)
            st.session_state.pop(f"{prefix}_capture_meta", None)

    if st.session_state.get(f"{prefix}_accepted") is not None:
        st.success(t("capture_accepted_label"))

    b1, b2 = st.columns(2)
    with b1:
        if st.button(t("capture_record_again"), key=f"{prefix}_again", use_container_width=True):
            _reset_sample_state(prefix)
            st.rerun()
    with b2:
        if st.button(t("capture_accept"), key=f"{prefix}_accept", type="primary", use_container_width=True):
            if selection_seconds + 1e-9 < TARGET_SECONDS:
                st.warning(t("capture_selection_too_short"))
            else:
                st.session_state[f"{prefix}_accepted"] = selection_bytes
                st.session_state[f"{prefix}_accepted_trim"] = (start, end)
                st.session_state[f"{prefix}_capture_meta"] = {
                    "source_kind": st.session_state.get(f"{prefix}_source_kind", "unknown"),
                    "source_container": st.session_state.get(f"{prefix}_source_container", "unknown"),
                    "source_duration_seconds": st.session_state.get(f"{prefix}_source_duration_seconds"),
                    "server_max_seconds": max_seconds,
                    "server_truncated": st.session_state.get(f"{prefix}_server_truncated", False),
                    "manual_selected_start_seconds": round(start, 4),
                    "manual_selected_end_seconds": round(end, 4),
                    "manual_selected_seconds": round(selection_seconds, 4),
                    "device_metadata": "not_available_from_streamlit",
                }
                st.rerun()

    return st.session_state.get(f"{prefix}_accepted")
