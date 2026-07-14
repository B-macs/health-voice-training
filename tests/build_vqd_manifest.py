"""VQD (Perceptual Voice Qualities Database) manifest builder.

296 recordings, each a single WAV containing sustained /a/, /i/, and the
CAPE-V sentences concatenated, rated by 3-4 expert clinicians (2 trials
each) on both GRBAS and CAPE-V scales, including Breathiness -- real
continuous perceptual ground truth, unlike SVD's categorical diagnosis
labels. Source: "Voice Samples Direct Download/", see
"Introduction, Methods and Reliability/database overview v2.pdf".

Two copies of every audio file exist (flat at the folder root, and again
under "Audio Files/") -- verified byte-identical (SHA-256) for a sample;
"Audio Files/" is used as canonical, the flat top-level copies are ignored.

Run manually: python tests/build_vqd_manifest.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
VQD_DIR = ROOT / "Voice Samples Direct Download"
AUDIO_DIR = VQD_DIR / "Audio Files"
RATINGS_DIR = VQD_DIR / "Ratings Spreadsheets"

SUFFIX_RE = re.compile(r"[_\s]*E?[_\s]*NSS$", re.IGNORECASE)

# Verified typos in the source database (checked: no conflicting/duplicate
# file exists under either spelling, so these are unambiguously the same
# recording under two different labels, not two distinct recordings):
#   - "SJ1004._ENSS.wav" has a stray trailing period in the filename.
#   - Audio filenames "SJ1001"/"SJ2004" vs. ratings rows "ST1001"/"ST2004"
#     (a one-letter prefix typo somewhere in the original database).
AUDIO_ID_CORRECTIONS = {
    "SJ1004.": "SJ1004",
    "SJ1001": "ST1001",
    "SJ2004": "ST2004",
}

MANIFEST_COLUMNS = [
    "file_path", "file_id", "sample_rate", "duration_s",
    "grbas_breathiness_avg", "grbas_breathiness_category",
    "cape_v_breathiness_avg", "cape_v_breathiness_sd",
    "gender", "age", "diagnosis",
]


def normalize_id(raw) -> str:
    return str(raw).strip().upper()


def audio_stem_to_id(stem: str) -> str:
    file_id = normalize_id(SUFFIX_RE.sub("", stem))
    return AUDIO_ID_CORRECTIONS.get(file_id, file_id)


def load_ratings() -> pd.DataFrame:
    grbas = pd.read_excel(RATINGS_DIR / "grbas_breathiness_only.xlsx")
    capev = pd.read_excel(RATINGS_DIR / "cape_v_breathiness_only.xlsx")
    demo = pd.read_excel(RATINGS_DIR / "Demographics.xlsx")

    grbas = grbas.rename(columns={"Average Value": "grbas_breathiness_avg", "Category Value": "grbas_breathiness_category"})
    grbas["file_id"] = grbas["File"].astype(str).map(normalize_id)

    capev = capev.rename(columns={"Average Values": "cape_v_breathiness_avg", "Standard Deviation": "cape_v_breathiness_sd"})
    capev["file_id"] = capev["File"].astype(str).map(normalize_id)

    demo = demo.rename(columns={"Participant ID ": "file_id", "Gender": "gender", "Age": "age", "Diagnosis ": "diagnosis"})
    demo["file_id"] = demo["file_id"].astype(str).map(normalize_id)

    merged = grbas[["file_id", "grbas_breathiness_avg", "grbas_breathiness_category"]].merge(
        capev[["file_id", "cape_v_breathiness_avg", "cape_v_breathiness_sd"]], on="file_id", how="outer"
    ).merge(
        demo[["file_id", "gender", "age", "diagnosis"]], on="file_id", how="left"
    )
    return merged


def main():
    import soundfile as sf

    ratings = load_ratings()
    ratings_by_id = {row["file_id"]: row for _, row in ratings.iterrows()}

    manifest_rows = []
    skipped = []
    matched_ids = set()

    for wav_path in sorted(AUDIO_DIR.glob("*.wav")):
        file_id = audio_stem_to_id(wav_path.stem)
        row = ratings_by_id.get(file_id)
        if row is None:
            skipped.append(f"no ratings match for {wav_path.name} (normalized id {file_id!r})")
            continue
        matched_ids.add(file_id)

        info = sf.info(str(wav_path))
        manifest_rows.append({
            "file_path": str(wav_path.relative_to(ROOT)),
            "file_id": file_id,
            "sample_rate": info.samplerate,
            "duration_s": round(info.frames / info.samplerate, 4),
            "grbas_breathiness_avg": row["grbas_breathiness_avg"],
            "grbas_breathiness_category": row["grbas_breathiness_category"],
            "cape_v_breathiness_avg": row["cape_v_breathiness_avg"],
            "cape_v_breathiness_sd": row["cape_v_breathiness_sd"],
            "gender": row["gender"],
            "age": row["age"],
            "diagnosis": row["diagnosis"],
        })

    unmatched_ratings = set(ratings_by_id.keys()) - matched_ids
    for uid in sorted(unmatched_ratings):
        skipped.append(f"ratings row {uid!r} had no matching audio file")

    out_path = ROOT / "tests" / "vqd_manifest.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"wrote {len(manifest_rows)} rows to {out_path}")
    print(f"skipped/unmatched: {len(skipped)}")
    for s in skipped[:30]:
        print("  ", s)


if __name__ == "__main__":
    main()
