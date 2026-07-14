"""VOXplot -- Oura-style dashboard for the standalone German voice-analysis
prototype.

Captures a sustained vowel [a:] and a German continuous-speech passage,
runs the existing headless acoustic analysis (analysis/, unchanged -- this
file is presentation only, it does not reinvent any DSP), logs every
session to Supabase when configured (otherwise local voice_log.jsonl), and renders the results as a dark, Oura-style
dashboard: a composite "Stimm-Score" hero ring, a 30-day trend, an acoustic
-insights list, and the hexagonal Voice Profile radar. A raw-data QA
expander is available for verification.

Interface text follows config.UI_LANGUAGE and the reading passage/AVQI/ABI
norm cutoffs follow config.ANALYSIS_LANGUAGE (see config.py) -- independent
settings, so the dashboard chrome can be read in one language while the
recorded passage and versioned reference boundaries stay tied to the
language/protocol they were defined for. They are trend references, not
clinical cutoffs.
This file reads a results dict / the immutable recording schema and renders it;
it falls back to ui/mock_data.py's fixture when no real sessions exist yet,
so the UI can be built/previewed before -- or independently of -- a live
capture. See README.md for how that fallback is wired and how to remove it.

IMPORTANT Streamlit gotcha (cost real debugging time, don't reintroduce it):
`st.markdown('<div class="card">')` ... other st.* calls ... `st.markdown('</div>')`
does NOT nest the calls in between inside that div. Each st.markdown() call
is an independently-parsed DOM fragment, so the unclosed <div> self-closes
immediately and everything "inside" renders as an empty, invisible sibling.
Every "card" here is a real `st.container(key="card_...")` block instead,
styled via the `div[class*="st-key-card_"]` CSS rule in ui/styles.py.
"""
from __future__ import annotations

import traceback

import streamlit as st

import config
from config import t, reading_passage, METRIC_META, RADAR_AXES, STATUS_THRESHOLDS
from ui.styles import inject as inject_css, COLORS
from ui.svg_components import hero_ring, gradient_bar, range_bar, radar_chart, trend_chart
from ui.scoring import goodness, abnormality, composite_stimm_score, group_score, status_word_key, status_color_key
from ui.aggregation import (
    aggregate, latest_and_prior_averages,
    period_to_ordinal, filter_to_window, trend_window_bounds,
    filter_comparable_records, incompatible_record_count, record_norms,
)
from ui.mock_data import build_mock_log
from ui.html_utils import flatten
from ui.capture import render_sample_capture, reset_capture_state, clear_accepted
from ui.training import render_training_tab
from ui.activities import render_activity_flow
from ui.training_plan import mark_item_complete, NEW_RECORDING

from analysis.audio_io import load_wav_bytes, concatenate
from analysis.parselmouth_metrics import analyze_single_parameters
from analysis.indices import compute_avqi, compute_abi
from analysis.provenance import build_analysis_metadata
from analysis.recording_protocol import protocol_error_message, standardize_pair
from analysis.norms import get_norms, flag_all
from storage.logger import JsonlRecordStore, log_session
from storage.daily_averages import DailyAverageStore
from storage.dates import sort_records
from storage.record_metadata import analysis_metadata, recording_quality_status
from storage.supabase import SupabaseConfig, SupabaseRecordStore, SupabaseStorageError

LOG_PATH = "voice_log.jsonl"
DAILY_LOG_PATH = "daily_averages.jsonl"
TREND_WINDOW = {"day": 30, "week": 16, "month": 12}


def md(html: str) -> None:
    """st.markdown(unsafe_allow_html=True), routed through flatten() -- see
    ui/html_utils.py for why every hand-built HTML block goes through this."""
    st.markdown(flatten(html), unsafe_allow_html=True)


def _ensure_session_state() -> None:
    """Initialise Voxplot-only UI state for standalone and embedded renders."""
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "voice_analysis"
    if "view" not in st.session_state:
        st.session_state.view = "dashboard"
    if "capture_step" not in st.session_state:
        st.session_state.capture_step = 1
    if "trend_granularity" not in st.session_state:
        st.session_state.trend_granularity = "day"
    if "trend_metric" not in st.session_state:
        st.session_state.trend_metric = "composite"


def _record_store() -> tuple[JsonlRecordStore | SupabaseRecordStore, DailyAverageStore | None]:
    """DETERMINISTIC: select configured Supabase storage; fallback stays local for standalone use."""
    try:
        secret_values = st.secrets.get("voxplot_supabase", {})
    except FileNotFoundError:
        secret_values = {}
    config = SupabaseConfig.from_mapping(secret_values)
    if config is not None:
        return SupabaseRecordStore(config), None
    return JsonlRecordStore(LOG_PATH), DailyAverageStore(DAILY_LOG_PATH)


def get_records() -> list[dict]:
    """DETERMINISTIC: load durable history; fallback uses fixtures only when no recordings exist."""
    store, _ = _record_store()
    real = store.read_all()
    return sort_records(real if real else build_mock_log())


# DETERMINISTIC: map persisted quality states to localized UI text; fallback is legacy / unknown.
def _quality_text_key(record: dict) -> str:
    return {
        "usable": "quality_usable",
        "limited": "quality_limited",
        "not_usable": "quality_not_usable",
        "legacy_unknown": "quality_legacy_unknown",
    }.get(recording_quality_status(record), "quality_legacy_unknown")


# DETERMINISTIC: render a metric value defensively; fallback is an em dash for unavailable output.
def _metric_value_text(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


# ===========================================================================
# Header + tab bar
# ===========================================================================

def render_header():
    md(f"""
        <div class="vx-header">
          <div class="vx-header-left">
            <span class="vx-app-name">{config.UI_STRINGS["de"]["app_name"]}</span>
            <span class="vx-app-version">{config.UI_STRINGS["de"]["app_version"]}</span>
          </div>
          <div class="vx-header-right">
            <span>Brian McAuliffe</span>
            <div class="vx-avatar">BM</div>
          </div>
        </div>
        """)


def render_tab_bar():
    tabs = [
        ("training", t("tab_training")),
        ("voice_analysis", t("tab_voice_analysis")),
        ("details", t("tab_details")),
    ]
    with st.container(key="tabbar"):
        cols = st.columns(len(tabs))
        for col, (key, label) in zip(cols, tabs):
            with col:
                is_active = st.session_state.active_tab == key
                if st.button(label, key=f"tabbtn_{key}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.active_tab = key
                    st.rerun()


# ===========================================================================
# VOICE ANALYSIS tab
# ===========================================================================

def render_hero(records: list[dict]):
    current = records[-1]
    values = {**current["parameters"], **current["indices"]}
    norms = record_norms(current)

    score = composite_stimm_score(values, norms)
    score_display = f"{score:.1f}".rstrip("0").rstrip(".") if score is not None else "—"
    status_text = t(status_word_key(score)) if score is not None else t("score_not_available")
    color = COLORS[status_color_key(score)]
    comparable = filter_comparable_records(records, current)

    _, week_avg, month_avg = latest_and_prior_averages(comparable, "composite")
    trend_arrow = ""
    if week_avg is not None and month_avg is not None:
        trend_arrow = "&uarr;" if week_avg >= month_avg else "&darr;"

    ring_html = hero_ring(score if score is not None else 0.0, color)

    avqi_val = values.get("avqi")
    abi_val = values.get("abi")
    avqi_norm = norms["avqi"]
    abi_norm = norms["abi"]
    avqi_in_range = avqi_norm.in_range(avqi_val)
    abi_in_range = abi_norm.in_range(abi_val)
    avqi_color = COLORS["optimal"] if avqi_in_range is True else (COLORS["bad"] if avqi_in_range is False else COLORS["muted"])
    abi_color = COLORS["optimal"] if abi_in_range is True else (COLORS["bad"] if abi_in_range is False else COLORS["muted"])
    excluded = incompatible_record_count(records, current)

    with st.container(key="card_hero"):
        left, right = st.columns([1, 1.3])
        with left:
            md(f"""
                <div style="position:relative;width:176px;margin:0 auto;">
                  {ring_html}
                    <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                              align-items:center;justify-content:center;pointer-events:none;">
                    <div class="vx-big-number">{score_display}</div>
                    <div class="vx-status-word" style="color:{color};">{status_text}</div>
                  </div>
                </div>
                <div class="vx-hero-caption" style="text-align:center;margin-top:0.5rem;">{t("hero_title")}</div>
                <div class="vx-hero-caption" style="text-align:center;margin-top:0.25rem;">{t("hero_subtitle")}</div>
                """)
        with right:
            md(f"""
                <div class="vx-gbar-label-row"><span class="vx-gbar-name">{METRIC_META['avqi']['label']}</span>
                    <span class="vx-gbar-value">{_metric_value_text(avqi_val)} <span style="color:{COLORS['muted']};font-weight:400;">({t('trend_norm_line')} {avqi_norm.max:g})</span></span></div>
                {gradient_bar(avqi_val if avqi_val is not None else 0.0, 10.0, avqi_norm.max or 1.0, avqi_color)}
                <div style="height:0.7rem;"></div>
                <div class="vx-gbar-label-row"><span class="vx-gbar-name">{METRIC_META['abi']['label']}</span>
                    <span class="vx-gbar-value">{_metric_value_text(abi_val)} <span style="color:{COLORS['muted']};font-weight:400;">({t('trend_norm_line')} {abi_norm.max:g})</span></span></div>
                {gradient_bar(abi_val if abi_val is not None else 0.0, 10.0, abi_norm.max or 1.0, abi_color)}
                <div class="vx-hero-caption" style="margin-top:0.65rem;">{t('hero_recipe')}</div>
                <div class="vx-hero-caption" style="margin-top:0.25rem;">{t('recording_quality_label')}: {t(_quality_text_key(current))}</div>
                """)
            if week_avg is not None or month_avg is not None:
                md(f"""
                    <div class="vx-hero-compare">
                      <span>{t("prev_week_label")}: <b>{round(week_avg) if week_avg is not None else '--'}</b></span>
                      <span>{t("prev_month_label")}: <b>{round(month_avg) if month_avg is not None else '--'}</b> {trend_arrow}</span>
                    </div>
                    """)
            if excluded:
                md(f'<div class="vx-hero-caption">{t("trend_protocol_note")} ({excluded} legacy or non-comparable session(s) excluded.)</div>')


def _trend_series(buckets, granularity: str, window: int, label_fmt=lambda p: p):
    """(values, labels, x_positions) for trend_chart. A single bucket left
    after windowing renders as a flat line spanning the full requested
    window (e.g. all 30 days) rather than a lone, context-less dot --
    the first (synthetic window-start) label is left blank so only the
    real date shows."""
    if len(buckets) == 1:
        start, end = trend_window_bounds(granularity, window)
        v = buckets[0].average
        return [v, v], ["", label_fmt(buckets[0].period)], [start, end]
    values = [b.average for b in buckets]
    labels = [label_fmt(b.period) for b in buckets]
    x_positions = [period_to_ordinal(b.period, granularity) for b in buckets]
    return values, labels, x_positions


def render_trend_card(records: list[dict]):
    comparable = filter_comparable_records(records, records[-1])
    buckets = aggregate(comparable, "composite", "day")
    buckets = filter_to_window(buckets, "day", TREND_WINDOW["day"])
    if not buckets:
        st.info(t("no_history"))
        return
    values, labels, x_positions = _trend_series(buckets, "day", TREND_WINDOW["day"], label_fmt=lambda p: p[5:])

    with st.container(key="card_trend"):
        md(f'<div class="vx-section-label">{t("trend_card_title")} &middot; {t("trend_card_subtitle")}</div>')
        md(trend_chart(
            values, labels, x_positions=x_positions,
            domain=(0.0, 100.0), accepted_band=(STATUS_THRESHOLDS["optimal"], 100.0),
            norm_value=STATUS_THRESHOLDS["optimal"], color_hex=COLORS["optimal"],
        ))
        md(f'<div class="vx-hero-caption">{t("trend_monthly_label")}</div>')
        md(f'<div class="vx-hero-caption">{t("trend_protocol_note")}</div>')


_INSIGHT_PILL_ICON = {"optimal": "&#10003;", "attention": "&ndash;", "concerning": "&#10005;"}


def render_insights_card(records: list[dict]):
    """Three GROUP-level insights (Hoarseness / Breathiness / Pitch
    Stability), each based on one declared indicator rather than a hidden
    second composite of correlated raw parameters."""
    current = records[-1]
    values = {**current["parameters"], **current["indices"]}
    norms = record_norms(current)
    comparable = filter_comparable_records(records, current)

    insight_defs = [
        ("profile_cluster_hoarseness", "hoarseness"),
        ("profile_cluster_breathiness", "breathiness"),
        ("friendly_pitch_group", "general"),
    ]

    with st.container(key="card_insights"):
        md(f'<div class="vx-section-label">{t("insights_title")}</div>')

        for label_key, group in insight_defs:
            score = group_score(values, norms, group)
            if score is None:
                continue
            tier = status_word_key(score).split("_", 1)[1]  # "optimal" | "attention" | "concerning"
            pill_class = f"vx-pill-{tier}"
            pill_icon = _INSIGHT_PILL_ICON[tier]
            in_range_for_bar = True if tier == "optimal" else (False if tier == "concerning" else None)

            _, week_avg, month_avg = latest_and_prior_averages(comparable, f"group_{group}")
            week_txt = f"{week_avg:.0f}" if week_avg is not None else "--"
            month_txt = f"{month_avg:.0f}" if month_avg is not None else "--"

            md(f"""
                <div class="vx-insight-row">
                  <div class="vx-insight-top">
                    <span class="vx-insight-name">{t(label_key)}</span>
                    <div class="vx-insight-value-row">
                      <span class="vx-insight-value">{score:.0f}</span>
                      <span class="vx-pill {pill_class}">{pill_icon}</span>
                    </div>
                  </div>
                  {range_bar(score, in_range_for_bar)}
                  <div class="vx-insight-sub">{t("insights_current")}: {score:.0f} | {t("insights_week_avg")}: {week_txt} | {t("insights_month_avg")}: {month_txt}</div>
                </div>
                """)


def _radar_abnormalities(values: dict, norms: dict) -> dict:
    return {key: abnormality(values.get(key), norms[key]) for key in RADAR_AXES}


def render_voice_profile_card(records: list[dict]):
    current = records[-1]
    current_values = {**current["parameters"], **current["indices"]}
    norms = record_norms(current)
    comparable = filter_comparable_records(records, current)
    current_abn = _radar_abnormalities(current_values, norms)

    week_buckets = {
        key: filter_to_window(aggregate(comparable, key, "week"), "week", 1)
        for key in RADAR_AXES
    }
    month_buckets = {
        key: filter_to_window(aggregate(comparable, key, "month"), "month", 1)
        for key in RADAR_AXES
    }
    week_values = {key: (b[-1].average if b else None) for key, b in week_buckets.items()}
    month_values = {key: (b[-1].average if b else None) for key, b in month_buckets.items()}
    week_abn = _radar_abnormalities(week_values, norms)
    month_abn = _radar_abnormalities(month_values, norms)

    score = composite_stimm_score(current_values, norms)
    status_key = status_word_key(score)
    verdict = t(f"verdict_{status_key.split('_')[1]}") if score is not None else t("score_not_available")

    with st.container(key="card_profile"):
        md(f'<div class="vx-section-label">{t("profile_title")}</div>')
        md(f"""
            <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:{COLORS['muted']};margin-bottom:0.2rem;">
              <span>{t("profile_cluster_hoarseness")}</span>
              <span>{t("profile_cluster_breathiness")}</span>
            </div>
            <div style="display:flex;justify-content:center;">
              {radar_chart(current_abn, week_abn, month_abn)}
            </div>
            <div class="vx-legend" style="justify-content:center;">
              <span class="vx-legend-item"><span class="vx-legend-swatch" style="background:{COLORS['bad']};"></span>{t("legend_current")}</span>
              <span class="vx-legend-item"><span class="vx-legend-swatch" style="background:{COLORS['gold']};"></span>{t("legend_week_avg")}</span>
              <span class="vx-legend-item"><span class="vx-legend-swatch" style="background:{COLORS['muted']};"></span>{t("legend_month_avg")}</span>
            </div>
            <div class="vx-verdict">{verdict}</div>
            """)


def render_voice_analysis_tab(records: list[dict]):
    render_hero(records)
    render_trend_card(records)
    render_insights_card(records)
    render_voice_profile_card(records)


# ===========================================================================
# DETAILS tab
# ===========================================================================

def render_details_tab(records: list[dict]):
    current = records[-1]
    values = {**current["parameters"], **current["indices"]}
    norms = record_norms(current)

    groups = [
        ("details_group_general", "general"),
        ("details_group_breathiness", "breathiness"),
        ("details_group_hoarseness", "hoarseness"),
    ]

    with st.container(key="card_details"):
        for title_key, group in groups:
            keys = [k for k, meta in METRIC_META.items() if meta["group"] == group]
            md(f'<div class="vx-group-title">{t(title_key)}</div>')
            for key in keys:
                value = values.get(key)
                if value is None:
                    continue
                norm = norms.get(key)
                in_range = norm.in_range(value) if norm else None
                g = goodness(value, norm) if norm else None
                unit = METRIC_META[key]["unit"]
                if in_range is True:
                    pill_class, pill_icon = "vx-pill-optimal", "&#10003;"
                elif in_range is False:
                    pill_class, pill_icon = "vx-pill-concerning", "&#10005;"
                else:
                    pill_class, pill_icon = "vx-pill-attention", "&ndash;"
                norm_txt = ""
                if norm and norm.max is not None and norm.min is None:
                    norm_txt = f"Norm &lt; {norm.max:g}"
                elif norm and norm.min is not None and norm.max is None:
                    norm_txt = f"Norm &gt; {norm.min:g}"
                elif norm and norm.min is not None and norm.max is not None:
                    norm_txt = f"Norm {norm.min:g}&ndash;{norm.max:g}"
                md(f"""
                    <div class="vx-insight-row">
                      <div class="vx-insight-top">
                        <span class="vx-insight-name">{METRIC_META[key]["label"]}</span>
                        <div class="vx-insight-value-row">
                          <span class="vx-insight-value">{value:.2f}{(' ' + unit) if unit else ''}</span>
                          <span class="vx-pill {pill_class}">{pill_icon}</span>
                        </div>
                      </div>
                      {range_bar(g, in_range)}
                      <div class="vx-insight-sub">{norm_txt}</div>
                    </div>
                    """)

    render_trends_section(records)

    with st.expander(t("qa_expander")):
        st.json({
            **current,
            "analysis_meta": analysis_metadata(current),
        })


def render_trends_section(records: list[dict]):
    with st.container(key="card_trends"):
        md(f'<div class="vx-section-label">{t("tab_details")}</div>')

        granularities = [("day", t("trend_toggle_day")), ("week", t("trend_toggle_week")), ("month", t("trend_toggle_month"))]
        cols = st.columns(len(granularities))
        for col, (key, label) in zip(cols, granularities):
            with col:
                if st.button(label, key=f"gran_{key}", use_container_width=True,
                             type="primary" if st.session_state.trend_granularity == key else "secondary"):
                    st.session_state.trend_granularity = key
                    st.rerun()

        metric_options = ["composite"] + list(METRIC_META.keys())
        st.session_state.trend_metric = st.selectbox(
            t("trend_select_metric"),
            options=metric_options,
            format_func=lambda k: t("hero_title") if k == "composite" else METRIC_META[k]["label"],
            index=metric_options.index(st.session_state.trend_metric) if st.session_state.trend_metric in metric_options else 0,
        )

        metric_key = st.session_state.trend_metric
        granularity = st.session_state.trend_granularity
        window = TREND_WINDOW[granularity]
        comparable = filter_comparable_records(records, records[-1])
        buckets = aggregate(comparable, metric_key, granularity)
        buckets = filter_to_window(buckets, granularity, window)
        if not buckets:
            st.info(t("no_history"))
        else:
            values, labels, x_positions = _trend_series(buckets, granularity, window)

            if metric_key == "composite":
                domain = (0.0, 100.0)
                norm_value = float(STATUS_THRESHOLDS["optimal"])
                accepted_band = (norm_value, 100.0)
            else:
                norm = record_norms(records[-1]).get(metric_key)
                domain = None
                norm_value = norm.max if (norm and norm.max is not None) else (norm.min if norm else None)
                accepted_band = None
                if norm and (norm.min is not None or norm.max is not None):
                    lo = norm.min if norm.min is not None else float("-inf")
                    hi = norm.max if norm.max is not None else float("inf")
                    accepted_band = (lo, hi)

            md(trend_chart(
                values, labels, x_positions=x_positions,
                norm_value=norm_value, domain=domain, accepted_band=accepted_band,
            ))
            if norm_value is not None:
                md(f'<div class="vx-hero-caption">- - - {t("trend_norm_line")}: {norm_value:g}</div>')
            md(f'<div class="vx-hero-caption">{t("trend_protocol_note")}</div>')


# ===========================================================================
# Capture flow
# ===========================================================================

CAPTURE_TOTAL_STAGES = 3
CAPTURE_ILLUSTRATIONS = {
    "sv": "images/char_microphone_chatting.png",
    "cs": "images/char_chatting.png",
}


def _render_capture_topbar(stage: int) -> None:
    fill_pct = (stage / CAPTURE_TOTAL_STAGES) * 100
    c1, c2 = st.columns([1, 7])
    with c1:
        if st.button("✕", key="rec_close_btn", help=t("capture_cancel")):
            reset_capture_state("sv", "cs")
            st.session_state.pop("sv_bytes", None)
            st.session_state.view = "dashboard"
            st.session_state.capture_step = 1
            st.rerun()
    with c2:
        md(f'<div class="rec-progress-track"><div class="rec-progress-fill" style="width:{fill_pct:.1f}%;"></div></div>')


def _render_capture_step(
    stage: int, title_key: str, text_card_content: str,
    prefix: str, record_label_key: str, upload_label_key: str,
) -> bytes | None:
    _render_capture_topbar(stage)
    md(f'<div class="rec-title">{t(title_key)}</div>')
    with st.container(key=f"rec_illustration_{prefix}"):
        st.image(CAPTURE_ILLUSTRATIONS[prefix], use_container_width=True)
    with st.container(key=f"card_capture{stage}"):
        md(f'<div class="rec-text-card-label">{t("capture_text_to_record_label")}</div>')
        md(f'<div class="vx-reading-passage">{text_card_content}</div>')
        accepted = render_sample_capture(prefix, record_label_key, upload_label_key)
    return accepted


def render_capture_flow():
    step = st.session_state.capture_step

    if "last_error" in st.session_state:
        st.error(t("error"))
        with st.expander(t("qa_expander")):
            st.code(st.session_state["last_error"])

    if step == 1:
        sv_accepted = _render_capture_step(
            1, "capture_sv_title", t("capture_vowel_prompt"),
            "sv", "sv_record_label", "sv_upload_label",
        )
        if sv_accepted is not None:
            st.session_state["sv_bytes"] = sv_accepted
            st.session_state.capture_step = 2
            st.rerun()

    elif step == 2:
        cs_accepted = _render_capture_step(
            2, "capture_cs_title", reading_passage(),
            "cs", "cs_record_label", "cs_upload_label",
        )
        if cs_accepted is not None:
            with st.spinner(t("capture_analyzing_message")):
                run_analysis(st.session_state["sv_bytes"], cs_accepted)

    elif step == 3:
        render_congrats_screen()


def render_congrats_screen():
    md('<div class="rec-progress-track"><div class="rec-progress-fill" style="width:100%;"></div></div>')
    with st.container(key="rec_illustration_congrats"):
        st.image("images/celebration.png", use_container_width=True)
    md(f'<div class="rec-congrats-title">{t("capture_congrats_title")}</div>')
    md(f'<div class="rec-congrats-subtitle">{t("capture_congrats_subtitle")}</div>')
    if st.button(t("capture_view_results_button"), type="primary", use_container_width=True):
        st.session_state.view = "dashboard"
        st.session_state.active_tab = "voice_analysis"
        st.session_state.capture_step = 1
        st.rerun()


def run_analysis(sv_bytes: bytes, cs_bytes: bytes):
    try:
        raw_sv_sound = load_wav_bytes(sv_bytes)
        raw_cs_sound = load_wav_bytes(cs_bytes)
        standardized = standardize_pair(raw_sv_sound, raw_cs_sound)
        if not standardized.is_analysable:
            st.session_state["last_error"] = protocol_error_message(standardized)
            if standardized.sv.sound is None:
                clear_accepted("sv")
                clear_accepted("cs")
                st.session_state.pop("sv_bytes", None)
                st.session_state.capture_step = 1
            else:
                clear_accepted("cs")
            st.rerun()
            return

        sv_sound = standardized.sv.sound
        cs_sound = standardized.cs.sound
        assert sv_sound is not None and cs_sound is not None
        combined_sound = concatenate(sv_sound, cs_sound)

        single_params = analyze_single_parameters(sv_sound, cs_sound, combined_sound)
        avqi_result = compute_avqi(combined_sound)
        abi_result = compute_abi(combined_sound)

        parameters = single_params.as_dict()
        indices = {"avqi": avqi_result.avqi, "abi": abi_result.abi}
        active_norms = get_norms()
        norms = flag_all({**parameters, **indices}, active_norms)
        voice_quality_score = composite_stimm_score({**parameters, **indices}, active_norms)
        analysis_meta = build_analysis_metadata(
            standardized=standardized,
            sv_capture=st.session_state.get("sv_capture_meta"),
            cs_capture=st.session_state.get("cs_capture_meta"),
            avqi_result=avqi_result,
            abi_result=abi_result,
            norms=active_norms,
            voice_quality_score=voice_quality_score,
        )

        sample_meta = {
            "sv_seconds": sv_sound.duration,
            "cs_seconds": cs_sound.duration,
            "sample_rate_hz": combined_sound.sampling_frequency,
            "analysis_meta": analysis_meta,
        }

        store, daily_store = _record_store()
        record = log_session(store, sample_meta, parameters, indices, norms, daily_store=daily_store)
        mark_item_complete(NEW_RECORDING)

        st.session_state.pop("last_error", None)
        st.session_state["last_record"] = record
        reset_capture_state("sv", "cs")
        st.session_state.pop("sv_bytes", None)
        st.session_state.capture_step = 3
        st.rerun()
    except SupabaseStorageError:
        # A configured server store must not leak backend responses or traces into the UI.
        st.session_state["last_error"] = (
            "The secure voice-history service could not save this analysis. "
            "Please try again after checking its configuration."
        )
        clear_accepted("cs")
        st.rerun()
    except Exception as exc:
        st.session_state["last_error"] = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        clear_accepted("cs")
        st.rerun()


# ===========================================================================
# Main
# ===========================================================================

def render(*, embedded: bool = False) -> None:
    """Render Voxplot standalone or inside the Health Voice Training route."""
    if not embedded:
        st.set_page_config(page_title=t("page_title"), layout="centered", initial_sidebar_state="collapsed")
    inject_css(st)
    _ensure_session_state()

    if st.session_state.view == "capture":
        render_capture_flow()
    elif st.session_state.view == "activity":
        render_activity_flow()
    else:
        render_header()
        render_tab_bar()

        records = get_records()

        if st.session_state.active_tab == "training":
            render_training_tab()
        elif st.session_state.active_tab == "voice_analysis":
            render_voice_analysis_tab(records)
        elif st.session_state.active_tab == "details":
            render_details_tab(records)


if __name__ == "__main__":
    render()
