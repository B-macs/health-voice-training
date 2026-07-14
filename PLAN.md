# Voxplot Prototype — PLAN.md

Standalone voice-acoustics prototype. It captures a sustained vowel [a:] and
a continuous-speech sample, quality-checks and standardizes a three-second
window from each, computes 14 single acoustic parameters plus an AVQI-like
index and custom breathiness estimate, and logs one non-audio-provenanced
record per session. No AI. The app has a patient-facing dashboard, including
the retained personal Voice Quality score and a technical-record expander.
UI language and analysis language are separate `config.py` settings.

> **Audit correction, 2026-07-14:** read
> [`docs/voice_quality_measurement_policy.md`](docs/voice_quality_measurement_policy.md)
> before relying on older validation wording below. It supersedes the former
> claims that 2.70 was the German v03.01 cutoff and that this project has
> reference-script parity. It also records the protocol-v2, provenance,
> quality, legacy-history, and model-threshold decisions.

## Status legend
green = tested & verified · yellow = works but unverified/approximate · red = broken/unknown

## Architecture decision: AVQI / ABI sourcing (resolved 2026-07-08, revised 2026-07-08)

The "official" AVQI/ABI Praat script is a commercial product sold by Phonanium
(Youri Maryn), ~€67, not freely redistributable — vendoring it would be a
license violation, and none was obtainable this session either (confirmed:
`praat_scripts/` has no licensed script; none was found anywhere on disk).
Decision (user-approved): reimplement from the published, peer-reviewed
formulas, computing every sub-measure via `parselmouth.praat.call(...)`
against Praat's real DSP objects — not reinvented math, the actual published
coefficients. **Then validate that reimplementation against real,
professionally diagnosed audio (Saarbruecken Voice Database, SVD) instead of
byte-for-byte script parity, since no reference script/output was available.**

### AVQI — validated, working

```
AVQIv3 = [4.152 − 0.177·CPPs − 0.006·HNR − 0.037·Shim% + 0.941·ShdB
          + 0.01·Slope + 0.093·Tilt] × 2.8902
```
Source: Barsties v Latoszek et al., PMC10743486. On 362 real SVD recordings:
healthy median 2.43, Hyperfunktionelle Dysphonie 3.24, Hypofunktionelle
Dysphonie 3.27 on the historical SVD evaluation. This is useful
discrimination evidence, **not reference-script parity**. The German v03.01
paper reports a 1.85 cutoff for its equalised/reference protocol; Voxplot's
2.70 boundary remains a personal-trend reference only until matched-output
parity is demonstrated. **Status: yellow** (published coefficient
implementation and real-data discrimination exist; capture/DSP parity and
clinical cutoff transfer remain unverified).

### ABI — NOT the published formula; four-stage investigation

**Stage 1 — published formula**, reimplemented the same way as AVQI:
```
ABI = [5.0447740915 − 0.172·CPPs − 0.193·Jitter − 1.283·GNEmax(4500Hz)
       − 0.396·Hno(6000Hz) + 0.01·HNR-D + 0.017·H1-H2 + 1.473·ShdB
       − 0.088·Shim% − 68.295·PSD] × 2.9257400394
```
**Validating this against 362 real SVD recordings proved it badly broken**:
healthy median 6.09 (worse than the German cutoff 3.42), Hyperfunktionelle
Dysphonie median 4.66 (*lower*/better than healthy — backwards), and the raw
pre-clip value saturated at the 0 or 10 boundary for 17–19% of all recordings.
At the time it was unclear whether the formula itself was broken, or whether
SVD's diagnosis categories were simply the wrong construct (e.g.
"Hyperfunktionelle Dysphonie" is typically strained/pressed, not breathy).

**Stage 2 — SVD-fitted logistic discriminant.** Rather than keep guessing at
the ambiguous "Hno-6000Hz"/"HNR-D" sub-measure definitions, a logistic
regression was fit on SVD's binary diagnosis label, using the same 9
conceptual sub-measures (`tests/fit_abi_svd.py` → `analysis/abi_svd_model.json`).
5-fold CV AUC 0.728, correct real-data ordering. Still explicitly a stand-in,
since SVD provides no perceptual ratings.

**Stage 3 — resolved, using VQD's real perceptual ratings.** The user added
the Perceptual Voice Qualities Database (VQD): 296 recordings independently
rated by 3–4 expert clinicians (2 trials each) on GRBAS and CAPE-V, including
Breathiness (ICC .844 interrater / .884 intrarater). This is the actual
target construct Barsties' ABI predicts, letting all three open questions be
answered with real ground truth (`tests/fit_abi_vqd.py`):
  1. **Is the published formula really broken?** Yes — Pearson r = −0.154
     against real GRBAS-Breathiness (p=0.008), r = −0.187 against
     CAPE-V-Breathiness (p=0.001). Negative and weak either way; confirmed
     broken, not a construct-mismatch artifact.
  2. **Does the SVD-fitted model (Stage 2) generalize** to a different
     population (American English, different recording setup, continuous
     rather than binary target)? Reasonably well: r = 0.591 (GRBAS-B) /
     0.584 (CAPE-V-B), both p < 1e-27.
  3. **Does fitting directly on VQD's real ratings do better?** Yes,
     substantially: the original OLS fit had 5-fold CV Pearson r = 0.814
     (RMSE 0.451 on the 0–3 scale), AUC 0.894 for detecting any breathiness
     (GRBAS-B > 0.5), clean
     monotonic category separation (Normal 1.10, Mild 2.57, Moderate 6.07,
     Severe 7.03, rescaled to 0–10).

`compute_abi` now uses a VQD-fitted Lasso regression (coefficients in
`analysis/abi_vqd_model.json`), predicting continuous GRBAS-Breathiness and
rescaling 0–3 → 0–10. The Lasso refit is Stage 4: it avoids the OLS
multicollinearity sign flip and records its 2.10 operating threshold, AUC
0.888, sensitivity 0.81, and specificity 0.82 in the model JSON. It is not
German-specific (VQD is American English) and remains pending matched mobile
German external validation. Applying it back to SVD gives
correctly-ordered but compressed scores (healthy 0.00, Hyperfunktionelle
0.66, Hypofunktionelle 0.60), consistent with SVD's dysphonia categories not
being primarily about breathiness. **Status: green** — fit on the actual
target construct from real expert perceptual ratings with published-grade
reliability; still not a reproduction of Barsties' validated ABI (different
raters/samples/scale calibration), so treat as a locally-calibrated
breathiness discriminant. See `analysis/indices.py` module docstring for
full detail.

## SVD data-pipeline findings (see CHANGELOG.md for the fixes these drove)

- Audio ships as `.nsp` (Kay CSL), not `.wav` — decoded via the `nspfile`
  package (cross-verified against an independent format spec), converted to
  canonical WAV once and cached (`tests/svd_wav_cache/`).
- 16 recordings (224 files, SHA-256-verified byte-identical) are physically
  duplicated across `Hyperfunktionelle Dysphonie` and `Hypofunktionelle
  Dysphonie` folders — a real SVD download-packaging quirk. The manifest
  builder uses each recording's own diagnosis metadata as the authoritative
  condition label and deduplicates.
- Per-speaker folder/file names are `AufnahmeID`, not `SprecherID` (verified).
- `Hypofunktionelle Dysphonie.zip` had not been extracted; extracted during
  this session (136MB, 16 speakers, 224 files).

## VQD data-pipeline findings

- 296 recordings, each ONE WAV containing sustained /a/, /i/, and the
  CAPE-V sentences concatenated — already a natural analogue of this app's
  "combined_sound", fed directly to `compute_avqi`/`compute_abi` with no
  segmentation needed. 44.1kHz/16-bit WAV, no NSP conversion required.
  Ratings in `Voice Samples Direct Download/Ratings Spreadsheets/*.xlsx`.
- Two copies of every audio file exist (flat at the folder root, and again
  under `Audio Files/`) — verified byte-identical (SHA-256); `Audio Files/`
  used as canonical, per the user's own warning about duplicates.
- 293/296 audio files matched ratings rows on a normalized ID (stripping
  the inconsistent `ENSS`/`_ENSS`/`_E_NSS` suffix spelling); the remaining
  3 were verified typos in the source database (a stray trailing period,
  and two `SJ`/`ST` prefix mismatches with no conflicting file under either
  spelling) and corrected explicitly in `tests/build_vqd_manifest.py`.

## File layout

- `app.py` — Streamlit capture UI/dashboard (mic via `st.audio_input`, `.wav` upload), technical record, independent UI/analysis language
- `config.py` — UI language, analysis language, reading passage, score and display metadata
- `analysis/parselmouth_metrics.py` — 14 single parameters
- `analysis/indices.py` — AVQI (formula reimplementation) + ABI (VQD-fitted regression, see above)
- `analysis/abi_svd_model.json` — Stage-2 SVD-fitted model (kept for reference/comparison, no longer used by `compute_abi`)
- `analysis/abi_vqd_model.json` — Stage-3 VQD-fitted model, the one `compute_abi` actually loads (regenerate via `tests/fit_abi_vqd.py`)
- `analysis/recording_protocol.py` — deterministic three-second window selection + non-audio recording QC
- `analysis/provenance.py` — model/runtime/protocol metadata stored with every v2 record
- `analysis/norms.py` — versioned reference boundaries + in/out-of-range flagging; `get_norms(language)` seam
- `storage/logger.py` — append structured record to JSONL; local-date-aware, chronology-sorted history
- `praat_scripts/` — kept for future drop-in of a licensed official script (currently empty + README); none exists to drop in as of this session
- `tests/` — unit tests (G3/G4/G6) + SVD/VQD validation suites (see below)
  - `build_svd_manifest.py` → `svd_manifest.csv` (P1); `svd_utils.py` — NSP→WAV cache, manifest loading, stratified sampling, `analyze_recording`; `run_svd_batch.py` → `svd_results.csv`; `fit_abi_svd.py` → `abi_svd_model.json` (Stage 2)
  - `build_vqd_manifest.py` → `vqd_manifest.csv` (joins audio to GRBAS-B/CAPE-V-B ratings + demographics); `vqd_utils.py` — manifest loading, `analyze_vqd_recording`, published-formula recomputation for comparison; `run_vqd_batch.py` → `vqd_results.csv`; `fit_abi_vqd.py` → `abi_vqd_model.json` (Stage 3, production model)
  - `test_discrimination.py` — pytest-wired SVD discrimination gate (P4/G5), skips if SVD not present; generates `reports/svd_validation_report.md` when run as `python -m tests.test_discrimination`
  - `test_vqd_validation.py` — pytest-wired VQD correlation/AUC gate (the authoritative ABI validation, in-sample regression check), skips if VQD not present locally
  - `generate_vqd_report.py` — regenerates `reports/vqd_validation_report.md` from the full 296-recording `vqd_results.csv` (no audio reprocessing needed)
- `reports/svd_validation_report.md`, `reports/vqd_validation_report.md` — per-condition/category AVQI/ABI stats, AUC/sens/spec, correlation with real ratings
- `requirements.txt` (app runtime), `requirements-dev.txt` (+ pytest, nspfile, scikit-learn, pandas, openpyxl for SVD/VQD validation only)
- `README.md`, `PLAN.md`, `CHANGELOG.md`

## Dependencies

App runtime (`requirements.txt`, pinned for reproducible DSP): streamlit 1.59.2 · praat-parselmouth 0.4.7 ·
numpy 2.4.3 · scipy 1.17.1 · soundfile 0.14.0 · imageio-ffmpeg 0.6.0. Dev/validation only
(`requirements-dev.txt`): pytest 9.1.1 · nspfile 0.2.0 · scikit-learn 1.9.0 ·
pandas 3.0.3 · openpyxl 3.1.5. Python 3.11.9, isolated venv at `.venv/`.

## Praat call recipes (empirically verified)

- F0 mean/SD (Hz & semitones): `Sound: To Pitch` → `Get mean/Get standard deviation` — green
- Jitter local/ppq5: `To PointProcess (periodic, cc)` → `Get jitter (local/ppq5)` — green
- Shimmer local/local_dB/apq11: `[Sound, PointProcess]` → `Get shimmer (...)` — green
- HNR: `To Harmonicity (cc)` → `Get mean` — green
- CPPS: `To PowerCepstrogram` → `Get CPPS` — green (values plausible on real data; exact clinical-script window params yellow/unverified)
- LTAS Slope: `To Ltas` → `Get slope` (0–1000 Hz vs 1000–Nyquist, "energy") — green
- LTAS Tilt: `To Ltas` → `Compute trend line` → `Get slope` (dB, NOT a raw per-Hz regression slope — that was ~1000x too small, see CHANGELOG) — green
- GNE: `To Harmonicity (gne)` (defaults 500/4500/1000/**80**) → max of resulting Matrix — green. Fine `step` (e.g. 10 Hz) segfaults the Praat GNE C code.
- H1-H2: `To Spectrum` → `Get band energy` around f0 and 2·f0, dB — green (recovered exact 6.02 dB on a synthetic 2:1 harmonic test); no formant correction
- PSD (period stdev, ABI input): `PointProcess: Get stdev period` — green
- Intensity normalization (`Scale intensity: 70`) before any AVQI/ABI sub-measure — green, fixes a real gain-dependence bug (see CHANGELOG)
- HNR-Dejonckere (ABI input): approximated with the same `To Harmonicity (cc)` HNR — yellow, undocumented exact method difference from Dejonckere's original; now an input to a fitted model rather than a fixed-formula term, so its exact definition matters less than before

## Validation gates

- G1 `streamlit run app.py` launches with zero errors — **green**, re-verified with German config
- G2 Mic capture (`st.audio_input`) + `.wav` upload both work — **yellow**: widget renders with no errors; live browser click-through not verified (no browser-automation tool available)
- G3 Analysis runs end-to-end on synthetic tone AND real audio, no exceptions — **green**, verified on 363 real SVD recordings + 296 real VQD recordings, 0 errors total
- G4 All 14 parameters finite, plausible-range numbers — **green**
- G5 Redefined as: does AVQI/ABI track real, expert-assessed voice quality/breathiness? **green** — AVQI: `reports/svd_validation_report.md` + `tests/test_discrimination.py` (diagnosis-category discrimination, 6/6 passing). ABI: `tests/test_vqd_validation.py` (correlation with real continuous perceptual GRBAS-B/CAPE-V-B ratings, 5/5 passing) — this is the stronger of the two validations, since VQD provides the actual target construct (perceptual ratings) rather than a diagnosis-category proxy. Not byte-for-byte script parity (no reference script available — see Architecture decision above).
- G6 Every recording appends a schema-valid JSONL row with norms/in-range flags — **green**
- G7 Fresh venv → `pip install -r requirements.txt` → app launches, no manual steps — **green**, re-verified

### P1–P7 (SVD validation session gates)

- P1 Manifest built, counts sane — **green** (SVD: 12,783 files / 917 recordings, `tests/svd_manifest.csv`; VQD: 296/296 recordings matched to ratings, `tests/vqd_manifest.csv`)
- P2 Validated AVQI/ABI scripts confirmed present — **N/A, confirmed absent**; session proceeded per user direction to fit from real data instead (see Architecture decision)
- P3 Parity harness — **N/A** (no reference script); replaced by the discrimination (P4) and VQD correlation (Stage 3 ABI) harnesses
- P4 Historical discrimination: SVD ordering and a saved report exist, but do **not** establish reference-script parity or a transferable German clinical cutoff; current status **yellow**. ABI's VQD evidence is separately documented, with its current Lasso model/threshold in `analysis/abi_vqd_model.json` and the policy document.
- P5 Large archives streamed, no OOM — **green** (individual `.nsp`/`.wav` files read one at a time; multi-GB zips pre-extracted to disk, never fully loaded into memory)
- P6 pytest green from fresh venv; G5 documented — **green**
- P7 Language/config: UI language and analysis language are deliberately separate in `config.py`; protocol, passage, and reference metadata are persisted with each record. This supersedes the former single-`LANGUAGE` statement.

## Phase 2 (not built now, not blocked)

Logged records are clean structured data (params + indices + norm flags) so a
deterministic rules engine can later map thresholds → voice-training exercise
suggestions, without touching this analysis layer.
