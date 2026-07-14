# CHANGELOG

Root-cause notes for fixes made while validating against the Saarbruecken
Voice Database (SVD) and the Perceptual Voice Qualities Database (VQD).
See PLAN.md for the full architecture/gate status.

## 2026-07-14 - separate voice-training library

- **Ten new activity cards, no new renderer or assets.** Added Supported Voice
  Reset, Lip Trill Ease, Voiced /v/ Flow, Nasal Resonance Ladder, Resonant
  Phrase Carryover, Small-Step Pitch Pattern, Gentle Phrase Pacing, Easy
  Articulation Practice, Chant-to-Speech Bridge, and Brief Voice Recovery
  Break. Each is an existing four-step countdown Activity, so it uses the
  same explanation, timer, results, and completion template as the original
  pool.
- **Separate library; original baseline restored.** The daily plan remains
  Days 1-10 and keeps its original 12-card schedule. All 22 cards (the 12
  original cards plus the ten above) are now available in a selectable
  Training Library, including after a daily plan is complete or locked until
  tomorrow. Future plans can mix and match these stable catalogue ids rather
  than duplicating activity definitions.
- **Completion isolation.** A library launch is explicitly marked as
  optional: finishing it returns to Training without changing the daily plan,
  XP, streak, progress history, or auto-starting the next planned card. Only
  an explicitly plan-launched card can call `mark_item_complete`; that method
  also rejects an activity id not assigned to the current plan day.
- **Supplied connected-speech text.** Reading, phrase, articulation, chant,
  and conversational carryover cards now show a stable three-sentence
  practice paragraph during the relevant explanation step and timer. It is a
  separate training prompt selected by analysis language, not the short,
  versioned recording-capture passage, so Voice Quality scoring and recording
  comparability remain unchanged. The quiet-rest-first recovery card remains
  intentionally limited to its optional single closing sentence.
- **Future activity-authoring rule.** Any connected-speech card must supply a
  purpose-selected paragraph at its speaking step and document why the text
  fits the target. Tongue-twister-style text is only for low-effort
  articulation precision; it is not a way to force vocal-fold effort,
  loudness, or range.
- **Patient-profile and recording-quality guardrails.** New cards allow a
  supported chair or easy neutral standing position, avoid a held
  posture-correction cue, and tell the user to change position rather than
  push through back symptoms. They use only comfortable pitch/loudness and
  include a recovery activity. The latest voice session was quality-limited
  by low SNR, so no card claims that a score changed or uses its score to
  progress the workload. See docs/training_activity_catalogue.md for
  rationale, sources, and stop/escalation rules.

## 2026-07-14 — measurement reliability and audit corrections

- **Voice Quality retained, not removed.** The existing equal-weight 0–100
  Voice Quality score remains the personal baseline trend. It now requires
  both declared components, so a missing AVQI-like or breathiness value is
  `Not scored` rather than a false zero or a silent one-component score.
  Status text now describes configured reference alignment rather than making
  a diagnosis.
- **Versioned 3 s capture protocol and recording QC.** New recordings use
  `de_windowed_3s_v2`: one activity-rich contiguous 3 s window is selected
  from each manually-approved vowel/speech clip. Silence/too-short/mostly
  inactive/heavily clipped selections are blocked; limited captures are
  retained but omitted from default comparable trends. This is an
  approximation to the German equal-duration protocol, not a claim of
  licensed-reference-script parity.
- **Provenance and statistical history handling.** New records retain
  non-audio protocol, raw/display indices, model hash/range warning, CPPS
  recipe, runtime, selected-duration, capture, and reference-cutoff metadata
  in existing `sample_meta` JSONB. Legacy recordings stay readable but are
  not silently mixed with v2 trends. Same-day retakes use a median with
  spread/count, stored norms stay immutable, JSONL history is time-sorted,
  and comparison windows are local-calendar days in Europe/Berlin.
- **Corrected AVQI citation without silently retuning the baseline.** The
  German AVQI v03.01 paper reports 1.85 (72% sensitivity/90% specificity),
  not the old documentation's 2.70 claim. 2.70 remains a versioned personal
  reference pending matched-output parity; it is no longer presented as that
  paper's clinical cutoff.
- **CPPS setting made explicit.** The pre-existing
  `subtract trend before smoothing=True` recipe is documented and persisted.
  It remains unchanged because Praat confirms it changes CPPS and no
  reference-parity evidence supports a baseline-breaking switch.
- **ABI 2.10 single source of truth.** The production VQD Lasso's model JSON
  now stores its 2.10 threshold/metrics. Norms and report generation read it;
  the fitting script derives future thresholds from out-of-fold predictions.
  The archived report is labelled pre-Lasso until VQD source results are
  available to regenerate it.

See `docs/voice_quality_measurement_policy.md` for the complete rationale,
validation boundaries, and required future investigations. Older entries
below are historical notes and may describe superseded OLS/2.0 or 2.70
claims.

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
