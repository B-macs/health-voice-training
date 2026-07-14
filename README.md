# Voxplot prototype (standalone voice-acoustics analysis, Oura-style dashboard)

Captures a sustained vowel [a:] and a German continuous-speech passage via
browser mic or `.wav` upload. New recordings use a documented, quality-checked
three-second window from each user-approved sample, then run the existing
acoustic analysis (14 single parameters + AVQI-like overall index + Voxplot
breathiness estimate). Every session logs non-audio provenance and presents
results as a dark, Oura-style dashboard: a composite "Voice Quality" hero
ring, a 30-day trend, an acoustic-insights list, and the hexagonal Voice
Profile radar. No AI. A technical-record expander is available for
verification. UI language and analysis language are deliberately separate in
`config.py`.

Read [the measurement policy](docs/voice_quality_measurement_policy.md)
before interpreting a score. It records the exact Voice Quality recipe,
capture protocol, historical-data policy, known limitations, and required
validation work.

Read [the training activity catalogue](docs/training_activity_catalogue.md)
before changing the training plan. It documents the separate 22-card Training
Library, the unchanged 10-day baseline, patient-profile accommodations, the
latest quality-limited recording context, and stop rules.

See `PLAN.md` for the full architecture, the AVQI/ABI sourcing decision and
its real-data validation, Praat call recipes, and validation-gate status.
See `CHANGELOG.md` for root-cause notes on every fix made along the way.

## Dashboard UI

`app.py` is presentation only -- it reads the same `analysis/`/`storage/`
output this project always produced and renders it; it does not reinvent
any DSP or touch the AVQI/ABI computation.

- **`config.py`** -- adds dashboard strings (tab labels, friendly metric
  names, status words) and `METRIC_META`/`RADAR_AXES`/`COMPOSITE_METRICS`,
  the single source of truth for which parameters group under Hoarseness
  ("Heiserkeit") vs. Breathiness ("Behauchtheit") vs. General ("Allgemein"),
  and which 6 feed the Voice Profile radar's axes.
- **`ui/scoring.py`** -- the retained composite "Voice Quality" score
  (0-100, higher = better). It is a personal acoustic trend: 50% AVQI-like
  overall index + 50% Voxplot breathiness estimate, and requires both
  components rather than silently becoming a one-component score.
  Voice metrics are mixed-direction (lower is better for AVQI/ABI/jitter/
  shimmer, higher is better for HNR/GNE/CPPS) and judged against a
  configured reference boundary, not a natural 0-100 scale, so every value is mapped
  through `goodness()`: 100 far better than its own norm cutoff, 50 exactly
  at the cutoff, →0 far worse. The composite score is built from AVQI+ABI
  only, not all 16 raw numbers -- they're themselves regression composites
  of most of the others, so including both layers would double-count the
  same signal. `abnormality()` (`100 - goodness`) drives the radar, where
  distance from center means "how far from normal", not "how good".
- **`ui/svg_components.py`** -- dependency-free SVG: the hero ring, the
  AVQI/ABI gradient headline bars, range-bar rows (marker position from
  `goodness`, color from the actual `norms.py` `in_range` boolean -- position
  and pass/fail are deliberately decoupled), the hexagonal radar, and the
  trend/area chart.
- **`ui/aggregation.py`** -- Day/Week/Month rollups over the configured
  voice-history store. Same-day retakes are reduced to a median with recorded
  spread/count; trends only compare matching protocol/scoring versions and
  quality-usable sessions.
  Every record is immutable and keyed by its ISO-8601 timestamp already;
  the ISO year-week and calendar year-month are derived here, on read, with
  no schema change. The norm used to flag each record is read from that
  record's own `norms` field, not recomputed from the current config, so a
  threshold line stays correct even if norms are re-tuned later.
- **`ui/mock_data.py`** -- lets the dashboard be built/previewed with zero
  real sessions logged yet. `app.py`'s `get_records()` calls the configured
  record store first and only falls
  back to the mock fixture if that's empty -- **once you've logged one real
  session, the mock data stops being used automatically**, no flag to flip.
  The mock "current" session uses Brian McAuliffe's real values from the
  reference `VOXplot_Profile_06_Nov25.pdf` export wherever that PDF gives
  one; four parameters it doesn't report (f0, shimmer apq11) are clearly-
  marked estimated placeholders. In/out-of-range status is computed from
  *this app's own* validated German norms, not the reference PDF's
  (different, stricter) cutoffs -- mixing norm systems would be incoherent.
  This is also why the composite score reads "Auffällig" (concerning), not
  the design mockup's illustrative "Optimal": the brief was explicit that
  the score must not be dishonestly rosy, and ABI/CPPS genuinely breach our
  norms for these real values. The 29 sessions before it are synthetic (a
  plausible, mildly-declining month) -- there's no real history yet.

### A Streamlit gotcha that cost real debugging time

Two, if you're building more of this UI:

1. `st.markdown('<div class="card">')` ... other `st.*` calls ... `st.markdown('</div>')`
   does **not** nest the calls in between inside that div. Each
   `st.markdown()` call is an independently-parsed DOM fragment -- the
   unclosed `<div>` self-closes immediately and everything "inside" renders
   as an empty, invisible sibling. Every "card" is a real
   `st.container(key="card_...")` block instead, styled via the
   `div[class*="st-key-card_"]` CSS attribute-selector in `ui/styles.py`.
2. Streamlit's own responsive breakpoint stacks every `st.columns()` row
   vertically below ~640px -- exactly this app's mobile-first target width.
   `ui/styles.py` forces `div[data-testid="stHorizontalBlock"]` to
   `flex-wrap: nowrap` and its `div[data-testid="stColumn"]` children to
   `min-width: 0` so multi-column rows (the tab bar, the hero, the capture
   flow's buttons) stay side-by-side.

### Verifying the dashboard visually

There's no `chromium-cli` in this environment, so verification here used
Playwright directly:
```bash
pip install playwright && playwright install chromium
```
then a small script driving `http://localhost:<port>` (`page.goto`,
`page.screenshot`, `page.get_by_role("button", name=...).click()`) -- see
git history / ask for the driver script if you need to re-verify a change.
`page.evaluate()` with `getBoundingClientRect()`/`getComputedStyle()` was
what actually diagnosed both gotchas above; a screenshot alone showed *that*
something was broken, not *why*.

## Setup

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

Open the printed local URL -- it lands on **STIMMANALYSE** with the mock
data fixture (see "Dashboard UI" above) until a real session is logged.
Click **Neue Aufnahme** to record/upload both samples, then
**Analysieren & protokollieren**; you're returned to the dashboard showing
that real session. Check the **DETAILS** tab's "QA (Debug)" expander to see
the raw logged JSON.

## Persistent Streamlit Cloud history (Supabase)

Without configuration, Voxplot keeps its append-only history in the local,
gitignored `voice_log.jsonl` file. For Streamlit Cloud, configure the
server-side Supabase store through Streamlit secrets -- never commit these
values or expose the secret key in browser code:

```toml
[voxplot_supabase]
url = "https://your-project-ref.supabase.co"
secret_key = "sb_secret_..."
```

The Streamlit deployment must be **private or invite-only** before enabling
this store. The server-side secret has database access for this one-person
app, so a public deployment without user authentication could otherwise let
visitors view or add to the shared history. Add the same secret block in
Streamlit Cloud's **Settings → Secrets**; the local `.streamlit/secrets.toml`
file is intentionally gitignored and is not deployed.

The tracked migration at
`supabase/migrations/20260714000000_create_voice_sessions.sql` creates the
append-only `voice_sessions` table. It stores calculated metrics and sample
metadata only; raw audio is never retained. It enables RLS, gives no browser
role access, and grants the server-only `service_role` just `SELECT` and
`INSERT` access. Confirm that the Supabase GitHub integration has deployed
this migration for the `main` branch before using the app or importer.

To import pre-existing local history once the migration has been applied,
run the idempotent importer with explicit paths. It is safe to rerun: each
record has a deterministic hash and duplicates are ignored.

```powershell
python scripts/migrate_voice_history.py `
  --secrets "C:\path\to\Health_project\.streamlit\secrets.toml" `
  "C:\path\to\Voxplot\voice_log.jsonl" `
  "C:\path\to\Health_project\voice_training\voxplot\voice_log.jsonl"
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Core unit tests (`test_audio_io.py`, `test_metrics.py`, `test_indices.py`,
`test_logger.py`, `test_ui.py`) run standalone, no external data needed. One test
(`test_abi_direction_breathy_worse_than_clean`) is an expected `xfail` on a
hand-built synthetic signal -- see `analysis/indices.py`'s module docstring
for why (an extrapolation artifact of that specific synthetic fixture, not
a bug in the deployed model, which is validated on real recordings from two
independent external databases instead -- see below).

### Regression/snapshot test (run this after touching `analysis/`)

`test_regression_snapshot.py` is not a correctness check -- it's a
golden-master test that freezes today's output for fixed, deterministic
synthetic input (the same `clean_sv`/`clean_cs`/`breathy_sv`/`breathy_cs`
fixtures other tests use) and fails loudly if *any* of the 14 parameters or
AVQI/ABI drift, even slightly. The point is to catch an unintended side
effect from touching one sub-measure (e.g. editing H1-H2) silently shifting
something unrelated (e.g. CPPS) that you wouldn't otherwise notice.

```bash
pytest tests/test_regression_snapshot.py -v
```

If it fails and every value it lists is one you *meant* to change (and by
the amount you expect) -- refresh the saved snapshot and commit it
alongside your code change so the diff shows exactly what shifted:

```bash
UPDATE_SNAPSHOT=1 pytest tests/test_regression_snapshot.py -v
pytest tests/test_regression_snapshot.py -v   # confirm it's green again
```

If it fails and lists something you *didn't* touch, that's a real
regression -- go find it before committing.

Two slow, opt-in validation suites depend on external data not vendored
into the repo and skip automatically if that data isn't present locally:

**SVD** (Saarbruecken Voice Database) -- AVQI discrimination against real
diagnosis labels:
```bash
python tests/build_svd_manifest.py     # writes tests/svd_manifest.csv
python tests/run_svd_batch.py 200      # writes tests/svd_results.csv (~10-15 min)
python tests/fit_abi_svd.py            # (re)fits analysis/abi_svd_model.json (reference only, see below)
pytest tests/test_discrimination.py -v
python -m tests.test_discrimination    # regenerates reports/svd_validation_report.md
```

**VQD** (Perceptual Voice Qualities Database) -- ABI correlation against
real expert perceptual breathiness ratings, the authoritative ABI
validation (see `analysis/indices.py`'s module docstring):
```bash
python tests/build_vqd_manifest.py     # writes tests/vqd_manifest.csv
python tests/run_vqd_batch.py          # writes tests/vqd_results.csv (~55 min, 296 recordings)
python tests/fit_abi_vqd_lasso.py      # (re)fits analysis/abi_vqd_model.json -- the production breathiness model
pytest tests/test_vqd_validation.py -v # ~8 min (40-recording stratified sample)
python tests/generate_vqd_report.py    # regenerates reports/vqd_validation_report.md (full 296 recordings)
```

## Known limitations (read before treating output as clinical-grade)

- **No licensed reference script was ever obtainable** (Phonanium's AVQI/ABI
  Praat scripts are a paid product, ~€67, with no free/open-access version
  found). So neither AVQI nor ABI is validated as byte-for-byte parity with
  the official script that VOXplot wraps -- both are validated against real
  external databases instead. See PLAN.md's "Architecture decision".
- **AVQI-like overall index** uses the published Barsties v Latoszek
  coefficients, but is not proven byte-for-byte equivalent to the licensed
  reference script. The German v03.01 paper reports **1.85**, not 2.70, for
  its equalised/reference protocol. Voxplot retains 2.70 only as a versioned
  personal-trend reference until matched-output parity work is complete; it
  is not a German diagnostic cutoff. See the measurement policy.
- **ABI is NOT the published Barsties formula.** That reimplementation was
  built, then proved badly broken -- confirmed two ways: first against real
  SVD diagnosis labels (healthy voices scored worse than dysphonic ones),
  then decisively against VQD's real expert perceptual breathiness ratings
  (Pearson r = -0.154, negative). It has been replaced with a linear
  Lasso regression fit directly on VQD's continuous GRBAS-Breathiness ratings
  (`tests/fit_abi_vqd_lasso.py`), the actual construct ABI is supposed to
  predict -- five-fold CV Pearson r=0.809, AUC 0.888 for detecting any
  breathiness at the versioned 2.10 model threshold.
  This is a locally-calibrated breathiness discriminant validated against
  real expert ratings with published-grade inter/intra-rater reliability,
  not a certified reproduction of Barsties' validated ABI (different
  raters/samples/scale calibration) -- see `analysis/indices.py`'s module
  docstring for the full four-stage investigation.
- **Norms in `analysis/norms.py`** are reference boundaries, not exhaustively
  validated clinical cutoffs. The VQD custom-breathiness threshold is stored
  in its model artifact; the AVQI-like reference is intentionally frozen for
  personal-score continuity pending reference parity. Configurable per
  language via `get_norms(language)`.
- **G2 (browser mic capture)** could not be fully verified in this
  environment: the widget renders with no errors, but a live browser
  click-through needs manual verification (no browser-automation tool was
  available here).
