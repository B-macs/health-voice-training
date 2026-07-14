"""Mock result fixture, so the dashboard can be built/previewed before
being wired to a live analysis session.

The "current" record uses Brian McAuliffe's REAL values from the reference
VOXplot PDF export (VOXplot_Profile_06_Nov25.pdf) wherever that PDF gives
one. Four parameters aren't in that PDF at all (it doesn't report f0 or
shimmer apq11) -- those four are clearly-marked ESTIMATED PLACEHOLDERS, not
real measurements. In/out-of-range status is computed from THIS app's own
versioned reference boundaries (analysis/norms.py), not the reference PDF's
norms (which used a different, stricter cutoff -- e.g. AVQI < 1.17 vs. this
app's 2.70 personal-trend boundary) -- mixing norm systems would be
incoherent. This is
also why the composite score below reads "Auffaellig" (concerning), not the
mockup's illustrative "Optimal": ABI and CPPS genuinely breach OUR norms
for these real values, and the brief was explicit that the score must not
be dishonestly rosy.

The 29 preceding sessions are entirely SYNTHETIC (a plausible, mildly-
declining month leading up to the real current session) -- there is no real
history to draw on yet. Swap `build_mock_log()`'s output for
`ui.aggregation.load_records("voice_log.jsonl")` once real sessions exist.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from analysis.norms import get_norms, flag_all

# Real, from VOXplot_Profile_06_Nov25.pdf
REAL_PARAMETERS = {
    "jitter_local_pct": 0.31,
    "jitter_ppq5_pct": 0.18,
    "shimmer_local_pct": 4.15,
    "shimmer_local_db": 0.36,
    "hnr_db": 23.05,
    "gne": 0.94,
    "h1_h2_db": 3.83,
    "ltas_slope_db": -13.88,
    "ltas_tilt_db": -13.88,
    "cpps_sv_db": 13.92,
}
REAL_INDICES = {"avqi": 2.24, "abi": 3.73}

# NOT in the reference PDF -- estimated placeholders for an adult male
# speaker, clearly separated so nobody mistakes them for measurements.
ESTIMATED_PLACEHOLDERS = {
    "f0_mean_hz": 118.0,
    "f0_sd_hz": 2.6,
    "f0_sd_st": 0.4,
    "shimmer_apq11_pct": 4.6,
    "cpps_cs_db": 11.5,  # continuous-speech CPPS is typically lower than sustained-vowel CPPS
}

CURRENT_PARAMETERS = {**REAL_PARAMETERS, **ESTIMATED_PLACEHOLDERS}
CURRENT_INDICES = dict(REAL_INDICES)


def _build_record(timestamp: datetime, parameters: dict, indices: dict) -> dict:
    norms = get_norms("de")
    flagged = flag_all({**parameters, **indices}, norms)
    return {
        "timestamp": timestamp.isoformat(),
        "sample_meta": {"sv_seconds": 3.0, "cs_seconds": 8.5, "sample_rate_hz": 44100},
        "parameters": parameters,
        "indices": indices,
        "norms": flagged,
    }


def build_mock_log(n_sessions: int = 29, seed: int = 42) -> list[dict]:
    """Synthetic history + the one real current session, oldest first."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    records = []
    for i in range(n_sessions, 0, -1):
        # Mildly declining over the month (drifting toward today's real,
        # concerning values) with session-to-session noise -- plausible,
        # not a real clinical trajectory.
        progress = 1.0 - (i / n_sessions)  # 0 (a month ago) -> ~1 (yesterday)
        drift = 0.35 * progress  # values get a bit worse as we approach today

        params = {}
        for key, target in CURRENT_PARAMETERS.items():
            noise = rng.gauss(0, abs(target) * 0.06 + 0.01)
            baseline = target * (1 - drift * 0.5)  # a month ago, somewhat better
            params[key] = baseline + noise

        indices = {}
        for key, target in CURRENT_INDICES.items():
            noise = rng.gauss(0, 0.25)
            baseline = target * (1 - drift)
            indices[key] = max(0.0, baseline + noise)

        timestamp = now - timedelta(days=i, hours=rng.randint(0, 10))
        records.append(_build_record(timestamp, params, indices))

    records.append(_build_record(now, CURRENT_PARAMETERS, CURRENT_INDICES))
    return records
