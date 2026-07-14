"""One-time SVD manifest builder.

Walks the four SVD condition folders (healthy, Hyperfunktionelle Dysphonie,
Hypofunktionelle Dysphonie, Internusschwaeche), reads each .nsp file's
header only (no full audio decode -- fast over ~13k files), cross-references
each recording against that condition's overview.csv (joined on AufnahmeID,
which is what the per-speaker folder/file names actually are -- NOT
SprecherID, verified empirically: folder "1037" under Hyperfunktionelle
Dysphonie matches overview.csv's AufnahmeID column, where SprecherID for
that same row is a different number, 1533), and writes
tests/svd_manifest.csv.

Run manually: python tests/build_svd_manifest.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import nspfile

ROOT = Path(__file__).resolve().parent.parent

CONDITIONS = [
    "healthy",
    "Hyperfunktionelle Dysphonie",
    "Hypofunktionelle Dysphonie",
    "Internusschwäche",
]

VOWEL_PITCH_RE = re.compile(r"^(?P<id>\d+)-(?P<vowel>[aiu])_(?P<pitch>n|h|l|lhl)$")
IAU_RE = re.compile(r"^(?P<id>\d+)-iau$")
PHRASE_RE = re.compile(r"^(?P<id>\d+)-phrase$")

PITCH_LABELS = {"n": "normal", "h": "high", "l": "low", "lhl": "rising-falling"}

MANIFEST_COLUMNS = [
    "file_path", "condition", "condition_folder", "recording_id", "speaker_id", "sex",
    "diagnosis", "pathology_label", "condition_pathology_mismatch",
    "vowel", "pitch", "is_sentence", "sample_rate", "duration_s",
]


def load_overview(condition_dir: Path) -> dict[str, dict]:
    """Merge all overview*.csv in a condition folder, keyed by AufnahmeID.
    (Hyperfunktionelle Dysphonie ships an extra, mislabeled overview_1.csv
    containing Hypofunktionelle Dysphonie rows -- harmless to merge in since
    we join by AufnahmeID and record any condition/label mismatch per row.)
    """
    rows: dict[str, dict] = {}
    for csv_path in sorted(condition_dir.glob("overview*.csv")):
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows[row["AufnahmeID"]] = row
    return rows


def parse_stem(stem: str) -> tuple[str, str | None, str | None, bool] | None:
    """Returns (recording_id, vowel, pitch, is_sentence) or None if the
    filename doesn't match any known SVD naming pattern (e.g. it's an -egg
    companion or something unexpected -- caller should skip and count it)."""
    m = PHRASE_RE.match(stem)
    if m:
        return m.group("id"), None, None, True
    m = IAU_RE.match(stem)
    if m:
        return m.group("id"), "iau", None, False
    m = VOWEL_PITCH_RE.match(stem)
    if m:
        return m.group("id"), m.group("vowel"), PITCH_LABELS[m.group("pitch")], False
    return None


def build_manifest() -> tuple[list[dict], list[str]]:
    manifest_rows: list[dict] = []
    skipped: list[str] = []

    for condition in CONDITIONS:
        condition_dir = ROOT / condition
        if not condition_dir.is_dir():
            skipped.append(f"condition folder missing entirely: {condition}")
            continue

        overview = load_overview(condition_dir)

        nsp_paths = sorted(condition_dir.glob("*/vowels/*.nsp")) + sorted(condition_dir.glob("*/sentences/*.nsp"))
        for nsp_path in nsp_paths:
            parsed = parse_stem(nsp_path.stem)
            if parsed is None:
                skipped.append(f"unrecognized filename pattern: {nsp_path}")
                continue
            recording_id, vowel, pitch, is_sentence = parsed

            try:
                header = nspfile.read(str(nsp_path), just_header=True)
            except Exception as exc:
                skipped.append(f"failed to read NSP header for {nsp_path}: {exc}")
                continue

            meta = overview.get(recording_id)
            pathology_label = meta.get("Pathologien", "") if meta else ""
            mismatch = bool(meta) and condition not in pathology_label and pathology_label != ""
            # Ground-truth condition is the recording's OWN metadata label,
            # not the folder it happened to ship in (see dedupe_manifest).
            true_condition = pathology_label if pathology_label else condition

            manifest_rows.append({
                "file_path": str(nsp_path.relative_to(ROOT)),
                "condition": true_condition,
                "condition_folder": condition,
                "recording_id": recording_id,
                "speaker_id": meta.get("SprecherID", "") if meta else "",
                "sex": meta.get("Geschlecht", "") if meta else "",
                "diagnosis": meta.get("Diagnose", "") if meta else "",
                "pathology_label": pathology_label,
                "condition_pathology_mismatch": mismatch,
                "vowel": vowel or "",
                "pitch": pitch or "",
                "is_sentence": is_sentence,
                "sample_rate": header["rate"],
                "duration_s": round(header["length"] / header["rate"], 4),
            })

    return manifest_rows, skipped


def dedupe_manifest(manifest_rows: list[dict]) -> tuple[list[dict], int]:
    """Some recordings are physically duplicated across condition folders
    (verified: 16 recording_ids / 224 files are byte-identical copies
    present in BOTH 'Hyperfunktionelle Dysphonie' and 'Hypofunktionelle
    Dysphonie' -- a real SVD download-packaging quirk, not a bug in this
    script). Keep only the copy whose condition_folder matches the
    recording's own ground-truth condition (from its metadata row); if
    neither/both match (shouldn't happen), keep the first seen."""
    best: dict[tuple[str, str, str, bool], dict] = {}
    for row in manifest_rows:
        key = (row["recording_id"], row["vowel"], row["pitch"], row["is_sentence"])
        existing = best.get(key)
        if existing is None:
            best[key] = row
            continue
        this_matches = row["condition_folder"] == row["condition"]
        existing_matches = existing["condition_folder"] == existing["condition"]
        if this_matches and not existing_matches:
            best[key] = row
    deduped = list(best.values())
    return deduped, len(manifest_rows) - len(deduped)


def main():
    manifest_rows, skipped = build_manifest()
    manifest_rows, n_deduped = dedupe_manifest(manifest_rows)
    print(f"removed {n_deduped} duplicate rows (recordings shipped in multiple condition folders)")

    out_path = ROOT / "tests" / "svd_manifest.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"wrote {len(manifest_rows)} rows to {out_path}")
    print(f"skipped {len(skipped)} files")
    for s in skipped[:20]:
        print("  SKIPPED:", s)
    if len(skipped) > 20:
        print(f"  ... and {len(skipped) - 20} more")

    by_condition: dict[str, int] = {}
    for row in manifest_rows:
        by_condition[row["condition"]] = by_condition.get(row["condition"], 0) + 1
    print("counts by condition:", by_condition)

    mismatches = [r for r in manifest_rows if r["condition_pathology_mismatch"]]
    print(f"condition/pathology-label mismatches: {len(mismatches)}")


if __name__ == "__main__":
    main()
