"""Shared helpers for SVD-based validation: NSP->WAV conversion (once,
cached to disk, reused across every test run) and stratified sampling
over tests/svd_manifest.csv.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

import nspfile
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "tests" / "svd_manifest.csv"
WAV_CACHE_DIR = ROOT / "tests" / "svd_wav_cache"

MIN_CS_VOICED_SECONDS = 1.0  # below this, mark the sample incomplete rather than silently proceed


def nsp_to_wav_cached(nsp_relative_path: str) -> Path:
    """Convert an SVD .nsp file to canonical WAV exactly once; reuse the
    cached file on every subsequent call/run. Returns the WAV path."""
    nsp_path = ROOT / nsp_relative_path
    wav_path = WAV_CACHE_DIR / (Path(nsp_relative_path).stem + ".wav")
    if wav_path.exists():
        return wav_path

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    fs, data = nspfile.read(str(nsp_path))
    data1d = data[:, 0] if data.ndim == 2 else data
    sf.write(str(wav_path), data1d, fs, subtype="PCM_16")
    return wav_path


def load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["is_sentence"] = row["is_sentence"] == "True"
        row["condition_pathology_mismatch"] = row["condition_pathology_mismatch"] == "True"
        row["sample_rate"] = int(row["sample_rate"])
        row["duration_s"] = float(row["duration_s"])
    return rows


def build_recording_index(rows: list[dict]) -> dict[str, dict]:
    """Group manifest rows by recording_id, keeping only what we need for
    AVQI/ABI analysis: the normal-pitch sustained vowel [a] (SV) and the
    read-aloud phrase (CS). Recordings missing either, or with a CS
    shorter than MIN_CS_VOICED_SECONDS, are marked incomplete rather than
    silently skipped or padded."""
    by_id: dict[str, dict] = {}
    for row in rows:
        rid = row["recording_id"]
        entry = by_id.setdefault(rid, {
            "recording_id": rid,
            "condition": row["condition"],
            "sex": row["sex"],
            "diagnosis": row["diagnosis"],
            "sv_row": None,
            "cs_row": None,
        })
        if row["vowel"] == "a" and row["pitch"] == "normal":
            entry["sv_row"] = row
        if row["is_sentence"]:
            entry["cs_row"] = row

    complete: dict[str, dict] = {}
    for rid, entry in by_id.items():
        sv_row, cs_row = entry["sv_row"], entry["cs_row"]
        if sv_row is None or cs_row is None:
            entry["incomplete_reason"] = "missing SV (a, normal pitch) or CS (phrase) file"
            continue
        if cs_row["duration_s"] < MIN_CS_VOICED_SECONDS:
            entry["incomplete_reason"] = f"CS duration {cs_row['duration_s']}s < {MIN_CS_VOICED_SECONDS}s minimum"
            continue
        entry["incomplete_reason"] = None
        complete[rid] = entry
    return complete


def analyze_recording(entry: dict) -> dict:
    """Convert (cached) + run the full app pipeline on one SVD recording.
    Returns single parameters + AVQI/ABI + the recording's condition/sex
    metadata, all in one flat dict."""
    from analysis.audio_io import load_wav_bytes, concatenate
    from analysis.parselmouth_metrics import analyze_single_parameters
    from analysis.indices import compute_avqi, compute_abi

    sv_wav = nsp_to_wav_cached(entry["sv_row"]["file_path"])
    cs_wav = nsp_to_wav_cached(entry["cs_row"]["file_path"])

    sv_sound = load_wav_bytes(sv_wav.read_bytes())
    cs_sound = load_wav_bytes(cs_wav.read_bytes())
    combined = concatenate(sv_sound, cs_sound)

    params = analyze_single_parameters(sv_sound, cs_sound, combined).as_dict()
    avqi_result = compute_avqi(combined)
    abi_result = compute_abi(combined)

    return {
        "recording_id": entry["recording_id"],
        "condition": entry["condition"],
        "sex": entry["sex"],
        "diagnosis": entry["diagnosis"],
        **params,
        "avqi": avqi_result.avqi,
        "abi": abi_result.abi,
        **{f"avqi_sub_{k}": v for k, v in avqi_result.as_dict()["components"].items()},
        **{f"abi_sub_{k}": v for k, v in abi_result.as_dict()["components"].items()},
    }


def stratified_sample(complete_index: dict[str, dict], n_per_condition: int, seed: int = 42) -> list[dict]:
    """Evenly sample across conditions and, within each condition, across
    sex, for a reproducible (seeded) stratified subset."""
    rng = random.Random(seed)
    by_condition: dict[str, list[dict]] = {}
    for entry in complete_index.values():
        by_condition.setdefault(entry["condition"], []).append(entry)

    sample: list[dict] = []
    for condition, entries in by_condition.items():
        by_sex: dict[str, list[dict]] = {}
        for e in entries:
            by_sex.setdefault(e["sex"], []).append(e)
        take_per_sex = max(1, n_per_condition // max(1, len(by_sex)))
        for sex, sex_entries in by_sex.items():
            rng.shuffle(sex_entries)
            sample.extend(sex_entries[:take_per_sex])
    return sample
