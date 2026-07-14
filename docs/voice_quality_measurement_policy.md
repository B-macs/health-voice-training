# Voice Quality measurement policy

Updated 2026-07-14 after `voxplot_review_audit.md` and the accuracy review.
This is the source of truth for what Voxplot's voice score means, what the
current capture protocol does, and which calculation changes are deliberately
deferred pending validation.

## Decision: retain Voice Quality

**Voice Quality remains in the app.** It is useful as Brian's familiar,
personal baseline reading and its numerical recipe remains unchanged:

```text
Voice Quality v1 = mean(
  reference-mapped AVQI-like overall acoustic index,
  reference-mapped Voxplot breathiness estimate
)
```

Each component has 50% weight. It intentionally does not add jitter,
shimmer, CPPS, HNR, or related inputs a second time because those features
already feed one or both component indices. Voice Quality is a **personal
acoustic trend**, not a percentage of vocal health, a diagnosis, or a
treatment recommendation. A full score now requires both components; a
missing component produces `Not scored`, never a misleading zero or a
silently reweighted one-component score.

The UI calls the two component measures `AVQI-like overall index` and
`Voxplot breathiness estimate`. The latter is a VQD-trained Lasso model, not
the published Barsties ABI formula.

## Capture protocol v2

New recordings use `de_windowed_3s_v2`:

1. The person manually selects a clean target utterance of at least 3 s.
2. Voxplot deterministically selects one **contiguous, activity-rich 3 s
   window** from the selected sustained vowel and one from the selected
   connected-speech sample. It favours the middle only when activity is tied,
   which avoids taking a vowel onset/offset by default.
3. Mechanical quality checks record duration, active-signal fraction, RMS,
   peak, clipping fraction, and a conservative signal/noise estimate. Very
   short, silent, mostly inactive, or heavily clipped selections are rejected
   before analysis. Limited-but-analysable captures remain visible but are
   excluded from the default comparable trend.

This change is motivated by the German AVQI/ABI validation protocol, which
equalised a 3 s sustained vowel and 3 s voiced connected speech (27 syllables)
before calculating the indices. [The validation abstract](https://pubmed.ncbi.nlm.nih.gov/30217485/)
reports that protocol and its results. Voxplot does **not** claim reference-
script parity: its energy-based activity selection is a transparent,
deterministic approximation until it can be benchmarked against licensed
reference outputs.

The quality activity field is an energy-based speech-activity proxy, not a
linguistic voicing classifier. Streamlit does not expose reliable browser,
microphone, distance, AGC, or noise-suppression metadata to this server-side
app, so the record states that explicitly rather than inventing device data.
Use a quiet room, the same device, and similar mouth-to-mic distance for a
useful personal trend.

## Historical records and comparability

Raw audio is intentionally never stored in JSONL or Supabase. Therefore old
sessions cannot be re-sliced or rescored under this new protocol. Records
without provenance are presented as `legacy_manual_unversioned` and
`legacy / unknown` quality:

- They remain readable and preserve the existing baseline score.
- A legacy latest record continues to trend against legacy history.
- Once a v2 recording exists, the default trend compares only v2,
  `usable`-quality records with the same scoring version. Legacy or limited
  records are not silently mixed into that line.

Daily rollups now use the **median** of same-day sessions, retain min/max/n
spread metadata, and retain the latest raw record's saved norm snapshot.
Week/month values average these one-per-day medians. This prevents retries
from overweighting a calendar day while keeping their variability auditable.
Dates are grouped in the persisted `Europe/Berlin` recording timezone, not
by an arbitrary Streamlit Cloud UTC server date. "Previous week/month" means
the seven/thirty calendar days before the latest session, not the last seven
or thirty days that happened to have a recording.

## Provenance stored with every v2 record

The existing Supabase `sample_meta` JSONB column now carries an
`analysis_meta` object; no schema migration is required. It contains:

- schema, analysis, protocol, quality-rule, norm-set, and scoring versions;
- analysis language and reading-passage identity;
- selected/source durations, manual capture metadata, and the chosen local
  timezone;
- QC result and reasons, with `raw_audio_stored: false`;
- raw and display-clipped AVQI-like / breathiness values, sub-measures,
  feature z-scores, and a conservative `max |z| >= 3` model-range warning;
- model id/SHA-256, CPPS recipe, ParSelmouth/Praat/runtime versions, and the
  exact reference cutoffs used.

This lets a result be understood later without pretending it can be
recomputed from unavailable raw audio.

## Cutoff and DSP decisions deliberately not changed

### AVQI 2.70 versus 1.85

The audit correctly found that the cited German v03.01 paper reports an AVQI
threshold of **1.85** (72% sensitivity, 90% specificity), not 2.70. The
code/documentation now say so. Voxplot nevertheless retains its existing
2.70 boundary as a versioned **personal-trend reference**, not a German
diagnostic cutoff. Switching it to 1.85 without proving parity between this
coefficient/Praat implementation and the licensed reference script would
make the familiar score look clinically calibrated when it is not, and would
also break baseline continuity. Required investigation before a versioned
cutoff change: run the same recordings through both implementations and
compare AVQI plus every sub-measure.

### CPPS trend subtraction

The existing Praat `Get CPPS` setting, `subtract trend before smoothing=True`,
is now named, persisted, and regression-locked. Praat states that this choice
changes CPPS whenever smoothing is used. [Praat's CPPS documentation](https://www.fon.hum.uva.nl/praat/manual/PowerCepstrogram__Get_CPPS___.html)
does not make one setting universally correct. Changing it without the same
reference-parity test would change AVQI-like values and invalidate the
baseline, so it remains unchanged for now.

### Pitch bounds, H1*–H2*, and high-frequency noise

The fixed 75–500 Hz pitch bounds, uncorrected H1–H2 feature, and 6 kHz
high-frequency proxy remain explicitly limited implementation choices. Praat
recommends a cross-correlation pitch-to-point-process path for voice analysis
and careful pitch-range selection, but changing that path or bounds changes
the deployed feature distribution. [Praat's voice-analysis guidance](https://www.fon.hum.uva.nl/praat/manual/Voice_6__Automating_voice_analysis_with_a_script.html)
supports that caution. Formant-corrected H1*–H2* or a different noise feature
requires refitting and validating the VQD model, then a new model/protocol
version; it is not a safe small formula patch.

### Custom breathiness model and threshold

The active 2.10 decision threshold is now stored once in
`analysis/abi_vqd_model.json`; `analysis/norms.py` and the report generator
read that artifact instead of carrying stale copies. The next refit script
derives a threshold from five-fold out-of-fold predictions. This improves
internal bookkeeping, but it does **not** solve the open external-validation
question: a German, smartphone/browser-matched, clinician-rated cohort and
speaker-grouped/nested validation are still required before the estimate is
clinical.

## Change checklist

| Audit item | Result |
|---|---|
| Recording standardisation / silence gap | Implemented as versioned contiguous 3 s activity-rich windows + QC; not claimed as licensed-script parity. |
| AVQI citation error | Corrected in documentation; 1.85 recorded as the paper result, 2.70 retained only as legacy personal reference pending parity. |
| CPPS `True` flag | Investigated, documented, versioned, and intentionally unchanged pending parity. |
| ABI 2.0 vs 2.10 | 2.10 made a model-artifact single source of truth; generator fixed; stale report marked historical. |
| Voice Quality score | Retained with the same 50/50 formula; missing-score and clinical-language errors corrected. |
| Retry averaging / QC / provenance | Median rollups, explicit quality state, date handling, raw-vs-display values, model-range warning, and immutable provenance implemented. |

## Validation still required before clinical use

1. Licensed/reference AVQI v03.01 output comparison on matched German
   recordings, including the CPPS setting.
2. A finalized, test-retest study of this exact browser/device/room capture
   protocol to establish personal meaningful-change thresholds.
3. Independent German mobile-recording external validation of the custom
   breathiness estimate, with grouped/nested model selection and an untouched
   test set.
4. Device/codec/AGC and microphone-distance comparison against a calibrated
   reference setup.

Until then, use the app for consistent personal monitoring and discuss
persistent voice changes with an appropriate clinician rather than treating a
single app score as a diagnosis.
