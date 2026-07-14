"""Direction-aware normalization and the composite "Stimm-Score".

Voice metrics are mixed-direction (lower is better for AVQI/ABI/jitter/
shimmer; higher is better for HNR/GNE/CPPS) and judged against a published
threshold, not a natural 0-100 scale. A plain "value / max * 100" bar would
misread a bad AVQI as a good fill. Every metric is instead mapped through
`goodness()`, a smooth function anchored on its own norm cutoff:

    goodness == 100   far better than the cutoff
    goodness == 50    exactly at the cutoff (the norm boundary)
    goodness -> 0     far worse than the cutoff

This single function backs the hero ring, the gradient bars, the range-bar
rows, and the radar chart, so "the norm boundary" always means the same
thing everywhere in the UI.
"""
from __future__ import annotations

import math

from analysis.norms import NormRange
from config import COMPOSITE_METRICS, STATUS_THRESHOLDS, METRIC_META


def goodness(value: float, norm: NormRange, steepness: float = 2.0) -> float | None:
    """0-100 "how good is this value against its own norm", direction-aware.
    Returns None if the value is missing/NaN or the parameter has no
    established single cutoff (norm.min and norm.max both unset)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if norm is None:
        return None

    if norm.min is not None and norm.max is not None:
        # target band: 100 at the center, falling off towards either edge
        center = (norm.min + norm.max) / 2
        half_width = max((norm.max - norm.min) / 2, 1e-9)
        ratio = abs(value - center) / half_width
        return 100.0 / (1.0 + ratio ** steepness)

    if norm.max is not None:
        # lower is better; norm.max is the cutoff
        cutoff = norm.max
        if cutoff <= 0:
            return None
        ratio = max(value, 0.0) / cutoff
        return 100.0 / (1.0 + ratio ** steepness)

    if norm.min is not None:
        # higher is better; norm.min is the cutoff
        cutoff = norm.min
        if value <= 0:
            return 0.0
        ratio = cutoff / value
        return 100.0 / (1.0 + ratio ** steepness)

    return None  # no established cutoff -- don't guess


def abnormality(value: float, norm: NormRange, steepness: float = 2.0) -> float | None:
    """Inverse of goodness (0 = perfect, 50 = at the norm boundary, 100 =
    far outside it) -- used by the radar chart, where distance FROM the
    center represents how abnormal a value is, not how good it is."""
    g = goodness(value, norm, steepness)
    return None if g is None else 100.0 - g


def composite_stimm_score(values: dict, norms: dict, metrics: list[str] = None) -> float | None:
    """Composite 0-100 score (higher = better), averaged over the
    multiparametric indices (AVQI/ABI by default -- see config.COMPOSITE_METRICS).
    Not built from all 16 raw parameters: AVQI/ABI are themselves regression
    composites of most of the others, so including both layers would double
    -count the same underlying acoustic signal."""
    metrics = metrics or COMPOSITE_METRICS
    scores = []
    for name in metrics:
        norm = norms.get(name)
        norm_range = _as_norm_range(norm)
        g = goodness(values.get(name), norm_range)
        if g is not None:
            scores.append(g)
    if not scores:
        return None
    return sum(scores) / len(scores)


def group_score(values: dict, norms: dict, group: str) -> float | None:
    """Same composite-scoring logic as composite_stimm_score, applied to
    every metric config.METRIC_META tags with the given group (Hoarseness /
    Breathiness / General) instead of just AVQI+ABI -- a broader "how's
    this whole cluster doing" score. A single cherry-picked raw parameter
    (e.g. CPPS alone) can look fine while the cluster it belongs to is
    genuinely poor (shimmer and AVQI both out of range, say), which is
    exactly the misleading picture this is meant to replace."""
    members = [k for k, meta in METRIC_META.items() if meta["group"] == group]
    return composite_stimm_score(values, norms, metrics=members)


def status_word_key(score: float | None) -> str:
    """Returns the config.py UI_STRINGS key for the status word matching a score."""
    if score is None:
        return "status_attention"
    if score >= STATUS_THRESHOLDS["optimal"]:
        return "status_optimal"
    if score >= STATUS_THRESHOLDS["attention"]:
        return "status_attention"
    return "status_concerning"


def status_color_key(score: float | None) -> str:
    key = status_word_key(score)
    return {"status_optimal": "optimal", "status_attention": "warning", "status_concerning": "bad"}[key]


def _as_norm_range(norm) -> NormRange | None:
    """Accepts either a NormRange instance or the plain dict shape stored
    in logged JSONL records ({"min":..., "max":..., "note":...})."""
    if norm is None:
        return None
    if isinstance(norm, NormRange):
        return norm
    if isinstance(norm, dict):
        return NormRange(min=norm.get("min"), max=norm.get("max"), note=norm.get("note", ""))
    return None
