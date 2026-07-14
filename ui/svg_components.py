"""Lightweight, dependency-free SVG components matching the Oura visual
language: a thin-stroke hero ring, gradient headline bars, honest range-bar
rows for directional norms, and the hexagonal Voice Profile radar.
"""
from __future__ import annotations

import math

from ui.styles import COLORS

# ---------------------------------------------------------------------------
# Hero ring
# ---------------------------------------------------------------------------

def hero_ring(score: float, color_hex: str, size: int = 176, stroke: int = 14) -> str:
    """Thin-stroke ring, animates its fill in on mount. `score` is 0-100.

    NOTE: the fill animation is driven by the GLOBAL `.vx-ring-fill`
    keyframe/class in ui/styles.py via CSS custom properties, not a
    per-call inline <style>/@keyframes block -- embedding a nested <style>
    tag inside a div-in-a-div here breaks Streamlit's markdown/HTML
    renderer (verified: it silently falls back to rendering the whole
    block as escaped literal text instead of HTML)."""
    r = (size - stroke) / 2
    circumference = 2 * math.pi * r
    target_offset = circumference * (1 - max(0.0, min(100.0, score)) / 100.0)
    cx = cy = size / 2

    return f"""
<div class="vx-hero-ring-wrap" style="width:{size}px;height:{size}px;">
  <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
            stroke="rgba(255,255,255,0.08)" stroke-width="{stroke}" />
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
            stroke="{color_hex}" stroke-width="{stroke}" stroke-linecap="round"
            stroke-dasharray="{circumference:.2f}"
            stroke-dashoffset="{circumference:.2f}"
            transform="rotate(-90 {cx} {cy})"
            class="vx-ring-fill"
            style="--vx-ring-target:{target_offset:.2f};" />
  </svg>
</div>
"""


# ---------------------------------------------------------------------------
# Gradient headline bar (AVQI / ABI)
# ---------------------------------------------------------------------------

def gradient_bar(value: float, domain_max: float, cutoff: float | None, marker_color: str) -> str:
    """Full-width green->red gradient track with a marker dot at the
    measured value's position, and a subtle tick at the norm cutoff."""
    pos_pct = max(0.0, min(100.0, (value / domain_max) * 100.0)) if domain_max else 0.0
    cutoff_pct = max(0.0, min(100.0, (cutoff / domain_max) * 100.0)) if (cutoff and domain_max) else None

    tick_html = ""
    if cutoff_pct is not None:
        tick_html = f"""<div style="position:absolute;left:{cutoff_pct:.1f}%;top:-3px;bottom:-3px;
            width:2px;background:rgba(255,255,255,0.55);"></div>"""

    return f"""
<div style="position:relative;height:8px;border-radius:4px;margin:0.35rem 0 0.15rem 0;
     background:linear-gradient(90deg,{COLORS['optimal']} 0%,{COLORS['warning']} 55%,{COLORS['bad']} 100%);
     opacity:0.85;">
  {tick_html}
  <div style="position:absolute;left:{pos_pct:.1f}%;top:50%;width:14px;height:14px;
       transform:translate(-50%,-50%);border-radius:50%;background:{marker_color};
       border:2px solid #0B0F14;box-shadow:0 0 0 1px rgba(255,255,255,0.5);"></div>
</div>
"""


# ---------------------------------------------------------------------------
# Range bar (individual parameter rows) -- position from goodness (direction-
# aware, always anchored so the norm boundary sits at 50%), color from the
# authoritative in_range boolean already computed by analysis/norms.py.
# ---------------------------------------------------------------------------

def range_bar(goodness_pct: float | None, in_range: bool | None) -> str:
    if goodness_pct is None:
        pos_pct = 50.0
    else:
        pos_pct = max(2.0, min(98.0, goodness_pct))

    if in_range is True:
        marker_color = COLORS["optimal"]
    elif in_range is False:
        marker_color = COLORS["bad"]
    else:
        marker_color = COLORS["muted"]

    return f"""
<div style="position:relative;height:6px;border-radius:3px;background:rgba(255,255,255,0.08);margin-top:0.4rem;">
  <div style="position:absolute;left:50%;right:0;top:0;bottom:0;border-radius:0 3px 3px 0;
       background:rgba(94,234,212,0.10);"></div>
  <div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:rgba(255,255,255,0.25);"></div>
  <div style="position:absolute;left:{pos_pct:.1f}%;top:50%;width:11px;height:11px;
       transform:translate(-50%,-50%);border-radius:50%;background:{marker_color};
       border:2px solid #0B0F14;"></div>
</div>
"""


# ---------------------------------------------------------------------------
# Voice Profile hexagon radar
# ---------------------------------------------------------------------------

_AXIS_ANGLES_DEG = {
    "avqi": -120,
    "hnr_db": 180,
    "jitter_ppq5_pct": 120,
    "abi": -60,
    "gne": 0,
    "cpps_sv_db": 60,
}
_AXIS_SHORT_LABELS = {
    "avqi": "AVQI",
    "hnr_db": "HNR",
    "jitter_ppq5_pct": "Jitter ppq5",
    "abi": "ABI",
    "gne": "GNE",
    "cpps_sv_db": "CPPS",
}
_BADGE_AXES = {"avqi": COLORS["gold"], "abi": COLORS["blue"]}


def _point(angle_deg: float, radius: float, cx: float, cy: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return cx + radius * math.cos(rad), cy + radius * math.sin(rad)


def _polygon_points(abnormalities: dict, r_max: float, cx: float, cy: float) -> str:
    pts = []
    for key, angle in _AXIS_ANGLES_DEG.items():
        a = abnormalities.get(key)
        radius = (max(0.0, min(100.0, a)) / 100.0) * r_max if a is not None else r_max * 0.5
        x, y = _point(angle, radius, cx, cy)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def radar_chart(
    current: dict,
    week_avg: dict | None,
    month_avg: dict | None,
    size: int = 320,
) -> str:
    """Each of `current`/`week_avg`/`month_avg` maps axis key -> abnormality
    (0-100, see ui.scoring.abnormality) for the 6 keys in _AXIS_ANGLES_DEG.
    The norm boundary is always the regular hexagon at 50% radius, by
    construction of the abnormality function."""
    cx = cy = size / 2
    r_max = size / 2 - 46  # leave room for axis labels

    grid_rings = "".join(
        f'<polygon points="{_polygon_points({k: pct for k in _AXIS_ANGLES_DEG}, r_max, cx, cy)}" '
        f'fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1" />'
        for pct in (25, 75, 100)
    )
    norm_boundary = (
        f'<polygon points="{_polygon_points({k: 50 for k in _AXIS_ANGLES_DEG}, r_max, cx, cy)}" '
        f'fill="none" stroke="{COLORS["optimal"]}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.8" />'
    )

    axis_lines = "".join(
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{_point(a, r_max, cx, cy)[0]:.1f}" '
        f'y2="{_point(a, r_max, cx, cy)[1]:.1f}" stroke="rgba(255,255,255,0.08)" stroke-width="1" />'
        for a in _AXIS_ANGLES_DEG.values()
    )

    labels = []
    for key, angle in _AXIS_ANGLES_DEG.items():
        lx, ly = _point(angle, r_max + 26, cx, cy)
        anchor = "middle"
        if math.cos(math.radians(angle)) > 0.3:
            anchor = "start"
        elif math.cos(math.radians(angle)) < -0.3:
            anchor = "end"
        if key in _BADGE_AXES:
            color = _BADGE_AXES[key]
            labels.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{color}" font-size="12" font-weight="700" '
                f'text-anchor="{anchor}" dominant-baseline="middle">{_AXIS_SHORT_LABELS[key]}</text>'
            )
        else:
            labels.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{COLORS["muted"]}" font-size="11" font-weight="500" '
                f'text-anchor="{anchor}" dominant-baseline="middle">{_AXIS_SHORT_LABELS[key]}</text>'
            )

    polygons = []
    if month_avg:
        polygons.append(
            f'<polygon points="{_polygon_points(month_avg, r_max, cx, cy)}" '
            f'fill="{COLORS["muted"]}" fill-opacity="0.10" stroke="{COLORS["muted"]}" stroke-width="1.5" opacity="0.7" />'
        )
    if week_avg:
        polygons.append(
            f'<polygon points="{_polygon_points(week_avg, r_max, cx, cy)}" '
            f'fill="{COLORS["gold"]}" fill-opacity="0.10" stroke="{COLORS["gold"]}" stroke-width="1.5" opacity="0.8" />'
        )
    polygons.append(
        f'<polygon points="{_polygon_points(current, r_max, cx, cy)}" '
        f'fill="{COLORS["bad"]}" fill-opacity="0.16" stroke="{COLORS["bad"]}" stroke-width="2" />'
    )

    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  {grid_rings}
  {norm_boundary}
  {axis_lines}
  {''.join(polygons)}
  {''.join(labels)}
</svg>
"""


# ---------------------------------------------------------------------------
# Trend chart (smooth filled area, Y-axis with clean tick numbers, an
# optional shaded "accepted range" band, and an optional dashed threshold
# line)
# ---------------------------------------------------------------------------

def _nice_ticks(v_min: float, v_max: float, count: int = 4) -> list[float]:
    """Evenly-spaced, round-numbered Y-axis ticks spanning [v_min, v_max]
    (never a raw fractional autoscale step -- see dataviz anti-patterns)."""
    if v_max <= v_min:
        return [v_min]
    raw_step = (v_max - v_min) / count
    magnitude = 10 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude
    if residual > 5:
        step = 10 * magnitude
    elif residual > 2:
        step = 5 * magnitude
    elif residual > 1:
        step = 2 * magnitude
    else:
        step = magnitude
    start = math.ceil(v_min / step) * step
    ticks = []
    v = start
    while v <= v_max + step * 1e-6:
        ticks.append(round(v, 10))
        v += step
    return ticks or [v_min, v_max]


def _format_tick(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}"
    if abs(v) >= 10:
        return f"{v:.0f}"
    if abs(v) >= 1:
        return f"{v:.1f}"
    return f"{v:.2f}"


def trend_chart(
    values: list[float],
    labels: list[str],
    x_positions: list[float] | None = None,
    norm_value: float | None = None,
    domain: tuple[float, float] | None = None,
    accepted_band: tuple[float, float] | None = None,
    width: int = 540,
    height: int = 160,
    color_hex: str | None = None,
) -> str:
    """Smooth filled-area line chart, Oura-style but with a real Y-axis.
    `values`/`labels` are parallel lists, oldest first.

    `x_positions`, if given (any monotonically increasing numbers, e.g. from
    ui.aggregation.period_to_ordinal), space points proportionally to real
    elapsed time instead of evenly by index -- a 4-month gap between
    sessions reads as a gap, not the same width as two sessions a day apart.

    `domain`, if given, fixes the Y-axis to that (min, max) instead of
    autoscaling to the visible data -- use this for any metric with a
    meaningful absolute scale (e.g. the 0-100 composite score), since
    autoscaling a narrow, low-lying window of values can make a genuinely
    bad score look like it's climbing to the top of the chart.

    `accepted_band`, if given, shades that (min, max) range (clipped to the
    visible domain; +-inf is fine for an open-ended bound) as the
    "accepted"/optimal zone, so it's visible at a glance whether a point is
    inside or outside it. `norm_value` still draws a single dashed threshold
    line (e.g. at the band's edge) -- dashing is reserved for a genuine
    threshold, never used for the axis gridlines themselves."""
    color = color_hex or COLORS["optimal"]
    if not values:
        return f'<svg width="{width}" height="{height}"></svg>'

    pad_left, pad_right, pad_top, pad_bottom = 34, 8, 14, 22
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    if domain is not None:
        v_min, v_max = domain
    else:
        all_vals = list(values) + ([norm_value] if norm_value is not None else [])
        v_min, v_max = min(all_vals), max(all_vals)
        if v_max - v_min < 1e-6:
            v_max = v_min + 1.0
        span = (v_max - v_min) * 1.15
        v_min -= span * 0.075
        v_max = v_min + span

    if x_positions and len(x_positions) == len(values) and max(x_positions) > min(x_positions):
        x_lo, x_hi = min(x_positions), max(x_positions)
        def frac(i: int) -> float:
            return (x_positions[i] - x_lo) / (x_hi - x_lo)
    else:
        def frac(i: int) -> float:
            return i / max(1, len(values) - 1)

    def xy(i: int, v: float) -> tuple[float, float]:
        x = pad_left + frac(i) * plot_w
        y = pad_top + (1 - (v - v_min) / (v_max - v_min)) * plot_h
        return x, y

    def y_of(v: float) -> float:
        return pad_top + (1 - (v - v_min) / (v_max - v_min)) * plot_h

    points = [xy(i, v) for i, v in enumerate(values)]

    # Straight segments, deliberately NOT a Catmull-Rom/Bezier smooth --
    # with time-proportional x positions, points can sit very unevenly
    # spaced (weeks apart, then months apart). A smoothed curve's tangents
    # are computed from neighboring points and can overshoot past a point
    # before turning to meet the next one, which briefly reverses the
    # curve's x-direction -- reading as the line looping backwards in time.
    # Straight segments can never do that: x is monotonic by construction,
    # since it's derived directly from the (already time-ordered) points.
    def line_path_from(pts: list[tuple[float, float]]) -> str:
        if len(pts) < 2:
            x, y = pts[0]
            return f"M {x:.1f},{y:.1f}"
        d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f} "
        for x, y in pts[1:]:
            d += f"L {x:.1f},{y:.1f} "
        return d

    line_path = line_path_from(points)
    area_path = line_path + f" L {points[-1][0]:.1f},{pad_top+plot_h:.1f} L {points[0][0]:.1f},{pad_top+plot_h:.1f} Z"

    band_rect = ""
    if accepted_band is not None:
        b_lo = max(v_min, accepted_band[0])
        b_hi = min(v_max, accepted_band[1])
        if b_hi > b_lo:
            y_top, y_bottom = y_of(b_hi), y_of(b_lo)
            band_rect = (
                f'<rect x="{pad_left}" y="{y_top:.1f}" width="{plot_w:.1f}" '
                f'height="{(y_bottom - y_top):.1f}" fill="{COLORS["optimal"]}" opacity="0.08" />'
            )

    ticks = _nice_ticks(v_min, v_max)
    axis_html = ""
    for tick in ticks:
        ty = y_of(tick)
        axis_html += (
            f'<line x1="{pad_left}" y1="{ty:.1f}" x2="{pad_left+plot_w}" y2="{ty:.1f}" '
            f'stroke="rgba(255,255,255,0.08)" stroke-width="1" />'
            f'<text x="{pad_left-6}" y="{ty+3:.1f}" fill="{COLORS["muted"]}" font-size="9" '
            f'text-anchor="end">{_format_tick(tick)}</text>'
        )

    norm_line = ""
    if norm_value is not None and v_min <= norm_value <= v_max:
        ny = y_of(norm_value)
        norm_line = (
            f'<line x1="{pad_left}" y1="{ny:.1f}" x2="{pad_left+plot_w}" y2="{ny:.1f}" '
            f'stroke="rgba(255,255,255,0.35)" stroke-width="1" stroke-dasharray="4,4" />'
        )

    n_ticks = min(4, len(labels))
    tick_labels = ""
    if n_ticks >= 2:
        for i in range(n_ticks):
            idx = round(i * (len(labels) - 1) / (n_ticks - 1))
            x, _ = xy(idx, values[idx])
            anchor = "start" if idx == 0 else ("end" if idx == len(labels) - 1 else "middle")
            tick_labels += (
                f'<text x="{x:.1f}" y="{height-6}" fill="{COLORS["muted"]}" font-size="10" '
                f'text-anchor="{anchor}">{labels[idx]}</text>'
            )

    uid = f"trend{abs(hash(tuple(values))) % 100000}"
    return f"""
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" style="display:block;width:100%;height:auto;">
  <defs>
    <linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.35" />
      <stop offset="100%" stop-color="{color}" stop-opacity="0.02" />
    </linearGradient>
  </defs>
  {band_rect}
  {axis_html}
  {norm_line}
  <path d="{area_path}" fill="url(#{uid})" stroke="none" />
  <path d="{line_path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" />
  <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="4" fill="{color}" stroke="#0B0F14" stroke-width="2" />
  {tick_labels}
</svg>
"""
