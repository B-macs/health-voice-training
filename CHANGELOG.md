# CHANGELOG

Root-cause notes for fixes made while validating against the Saarbruecken
Voice Database (SVD) and the Perceptual Voice Qualities Database (VQD).
See PLAN.md for the full architecture/gate status.

## SVD data-pipeline fixes

- **NSP format decoding.** The SVD ships `.nsp` (Kay Elemetrics CSL) audio,
  not `.wav`. Neither `soundfile` nor Praat/parselmouth's own `Sound()`
  constructor can read it directly (`"Not an audio file"`). Root cause:
  it's a legacy IFF-style chunked container (`FORM`/`DS16`/`HEDR`/`SDA_`),
  not one of Praat's recognized Kay-format variants. Fixed by using the
  `nspfile` package (PyPI, tikuma-lsuhsc) to decode to raw PCM, then
  writing a canonical WAV once via `soundfile` and reusing that WAV for
  all downstream analysis. Cross-verified the chunk layout `nspfile`
  implements against an independently-sourced format spec (McGill CSL
  format doc) before trusting it on real data.
- **Duplicate/mislabeled recordings across condition folders.** 16
  recordings (224 files, byte-identical, hash-verified) physically exist
  in *both* the `Hyperfunktionelle Dysphonie` and `Hypofunktionelle
  Dysphonie` folders, correctly labeled `Hypofunktionelle Dysphonie` in
  their own metadata row but shipped inside the wrong condition's zip. Root
  cause: an SVD download-packaging quirk, not a bug in our code --
  confirmed via SHA-256 comparison. Fixed in `tests/build_svd_manifest.py`
  by making the manifest's `condition` column authoritative from each
  recording's own `Pathologien` metadata field (not the folder it shipped
  in), and deduplicating so each recording is counted exactly once.
- **AufnahmeID vs SprecherID.** Per-speaker folder/file names are the
  recording's `AufnahmeID`, not `SprecherID` (verified: folder `1037`
  matches an `AufnahmeID` of 1037 whose `SprecherID` is a different
  number, 1533). The manifest joins metadata on `AufnahmeID`.

## AVQI/ABI implementation fixes

- **LTAS Tilt was ~1000x too small.** Originally computed as a raw
  per-Hz linear-regression slope over the LTAS (~-0.0003 dB/Hz), which is
  negligible next to the published Tilt coefficient's expected order of
  magnitude. Root cause: the AVQI/ABI "Tilt" is Praat's own
  `Ltas: Compute trend line...` + `Get slope` (dB, same convention as
  "Slope"), not a raw per-Hz regression slope. Fixed in
  `analysis/parselmouth_metrics.py::compute_ltas_slope_tilt`.
- **AVQI/ABI sub-measures were gain-dependent.** The same voice recorded
  louder/quieter gave different raw LTAS-level readings (verified:
  -27 dB vs -47 dB at 6 kHz for two amplitude-scaled copies of the same
  tone). Root cause: Praat's absolute LTAS level is referenced to the
  input signal's absolute amplitude, which is arbitrary for
  uncalibrated microphone recordings. Fixed by intensity-normalizing
  (`Scale intensity: 70`) a copy of the combined sample before computing
  any AVQI/ABI sub-measure (`analysis/indices.py::_intensity_normalized`).
- **GNE native Praat call segfaults on a fine step.** `To Harmonicity
  (gne)` with `step=10` Hz crashed the Python process outright (native
  Praat C code, not a catchable exception). Fixed by using Praat's own
  documented default `step=80` Hz.
- **ABI formula was wildly unstable / direction-inverted on real SVD
  data.** Validating the Barsties-formula reimplementation against 362 real
  SVD recordings showed healthy voices scoring *worse* (median 6.09) than
  Hyperfunktionelle Dysphonie (4.66), and the raw pre-clip value saturating
  at the 0/10 boundary for 17-19% of all recordings -- not a subtle
  ambiguity, a structurally unusable result. Root cause, as far as it was
  possible to isolate empirically: the "Hno-6000Hz" sub-measure (the paper's
  own text spells it "Hno", not "Hfno" -- suggesting a bounded
  harmonics-to-noise ratio) was approximated as a raw, unbounded LTAS dB
  level, which has a ~23 dB natural range on real recordings; its published
  coefficient (-0.396) alone turns that into a ~9-unit swing on a 0-10
  scale. Tested and disproved one alternative (GNE-style measure with a
  6 kHz bound -- gave degenerate, non-discriminating results). **First fix:**
  replaced the formula with a logistic regression fit on SVD diagnosis
  labels (`tests/fit_abi_svd.py` -> `analysis/abi_svd_model.json`). 5-fold
  CV AUC 0.728, correct real-data ordering. Still a stand-in, since SVD has
  no perceptual ratings (see next entry for the actual resolution).
- **ABI resolved for real using VQD's perceptual breathiness ratings.**
  The user added VQD (296 recordings independently rated by 3-4 expert
  clinicians on GRBAS/CAPE-V, including Breathiness -- ICC .844
  interrater/.884 intrarater), the actual construct ABI predicts. This
  answered three open questions with real ground truth
  (`tests/fit_abi_vqd.py`): (1) the published formula is genuinely broken,
  not just tested against the wrong SVD construct -- Pearson r=-0.154
  against real GRBAS-Breathiness, r=-0.187 against CAPE-V-Breathiness, both
  negative; (2) the SVD-fitted logistic model generalizes reasonably to
  this different population -- r=0.591/0.584; (3) fitting directly on VQD's
  real ratings does substantially better -- 5-fold CV Pearson r=0.814
  (RMSE 0.451 on the 0-3 GRBAS-B scale), AUC 0.894 for detecting any
  breathiness, clean monotonic category medians (Normal 1.10, Mild 2.57,
  Moderate 6.07, Severe 7.03 on a rescaled 0-10 scale). **Fix:**
  `analysis/indices.py::compute_abi` now loads `analysis/abi_vqd_model.json`
  (linear regression on GRBAS-Breathiness, same 9 conceptual sub-measures as
  inputs) instead of the SVD-fitted logistic model. German "abi" cutoff in
  `analysis/norms.py` updated to this model's own Youden-optimal threshold
  (2.0; sens 0.83/spec 0.80) since the old 3.42/4.07 cutoffs don't apply to
  a differently-fit model. See `analysis/indices.py` module docstring for
  the full three-stage investigation.
- **VQD manifest matching: inconsistent filename suffix spelling + 3
  database typos.** Audio filenames spell the "ENSS" suffix inconsistently
  (`" ENSS"`, `"_ENSS"`, `"ENSS"`, `"_E_NSS"`, mixed case) across otherwise
  consistent recording IDs. Fixed with a single regex stripping
  `[_\s]*E?[_\s]*NSS$` case-insensitively. Three remaining mismatches (a
  stray trailing period in one filename; two `SJ`/`ST` prefix mismatches
  between filename and ratings-sheet ID) were verified as source-database
  typos -- no conflicting file exists under either spelling -- and corrected
  explicitly in `tests/build_vqd_manifest.py::AUDIO_ID_CORRECTIONS`.

## German (P7) i18n

- Added `config.py` as the single source of truth: `LANGUAGE = "de"`
  drives the reading passage (verified IPA "Nordwind und Sonne" passage
  text against an academic phonetics source), every `app.py` UI string,
  and (via `analysis/norms.py::get_norms`) the AVQI/ABI cutoffs.
- Added German-validated AVQI cutoff (Barsties v Latoszek et al., German
  validation study): 2.70 (sens 79%/spec 92%, AUC 0.888). ABI's German
  literature cutoff (3.42) does NOT apply to the VQD-fitted model (see
  above) -- `analysis/norms.py` instead uses that model's own Youden-optimal
  threshold, 2.0 (AUC 0.894, sens 0.83/spec 0.80), not German-specific since
  VQD is American English.
