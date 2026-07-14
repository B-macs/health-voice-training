"""Activity content model + Screens A (explanation), B (timed practice),
and C (results) of the per-activity flow reached from a Training-tab
"Start" button.

This is the one place to define a new activity's content: build an
Activity with a title/duration/timer_seconds and 1-4 ActivityStep
instructions (each gets its own explanation screen, illustrated with
images/Sign1.png..Sign4.png -- the "#1".."#4" step-badge artwork). Screens
A, B, and C below render generically off that data; adding a new activity
never needs new render code, just a new Activity value. The real exercise
pool lives in ui/exercise_library.py (see its module docstring for why
each one was chosen).

Every activity's time lives in two required fields, `duration` (the
display string shown on the training-tab card) and `timer_seconds` (what
Screen B actually counts down) -- there is no rep/round count anywhere in
the model. Step instructions must guide the user by time ("until the
timer runs out") and never by a rep count ("N times" / "N rounds"),
because Screen B only ever runs a plain countdown and never tracks reps
for the user. ui/exercise_library.py's `_steps()` helper enforces this
with a regex check, so a new activity authored through it can't
reintroduce "N times"/"N rounds" phrasing by accident.

Screen B is a self-driving countdown: it re-shows all of the activity's
instructions as a reminder, counts down `activity.timer_seconds`, and
advances to the results screen on its own once the clock hits zero -- no
user interaction required. The countdown number is rendered by its own
`@st.fragment(run_every=1)` (_render_timer_clock) rather than a whole-
script sleep+st.rerun() loop -- the naive whole-script version was tried
first and, confirmed via manual browser testing, left stray widgets from
the *previous* screen visibly stuck on top of the timer after the
explain->timer transition, because a full-script rerun re-diffs the
entire element tree on every tick instead of just the fragment's small
subtree. "Results" for now are still placeholder metric rows
demonstrating the repeatable component, not measured data -- feed real
measured ActivityMetric values into render_activity_results() instead of
_placeholder_metrics() once that's wired up.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from html import escape

import streamlit as st

from config import t
from ui.styles import COLORS
from ui.svg_components import gradient_bar
from ui.html_utils import flatten

SIGN_ILLUSTRATIONS = [f"images/Sign{i}.png" for i in range(1, 5)]


def _md(html: str) -> None:
    st.markdown(flatten(html), unsafe_allow_html=True)


# DETERMINISTIC: renders only supplied static practice text; a missing paragraph leaves non-speech activities unchanged.
def _render_practice_paragraph(paragraph: str | None) -> None:
    if not paragraph:
        return
    _md(f"""
        <div class="act-practice-paragraph">
          <div class="act-practice-paragraph-title">{escape(t("activity_practice_paragraph_title"))}</div>
          <div class="act-practice-paragraph-copy">{escape(paragraph)}</div>
          <div class="act-practice-paragraph-hint">{escape(t("activity_practice_paragraph_hint"))}</div>
        </div>
        """)


@dataclass
class ActivityStep:
    """One explanation-screen step. `instruction` may contain a literal
    "{n}" placeholder (filled with the 1-based step number) -- real
    instruction text won't use it, and .format() is a no-op when it's
    absent, so the same rendering code handles both. `speech_paragraph` is
    optional text supplied only on a connected-speech step."""
    instruction: str
    illustration: str
    speech_paragraph: str | None = None


@dataclass
class ActivityMetric:
    """One row of the repeatable results-screen metric block."""
    label: str
    value: float
    display: str
    domain_max: float = 100.0
    cutoff: float | None = None


@dataclass
class Activity:
    id: str
    title: str
    duration: str
    category: str = "Training"
    timer_seconds: int = 240
    """How long Screen B's countdown runs before auto-advancing to results."""
    steps: list[ActivityStep] = field(default_factory=list)


def _placeholder_metrics() -> list[ActivityMetric]:
    return [
        ActivityMetric(label=f"{t('activity_metric_placeholder_label')} {i}", value=0.0, display="--")
        for i in (1, 2)
    ]


def _exit_to_plan() -> None:
    st.session_state.view = "dashboard"
    st.session_state.active_tab = "training"
    st.session_state.pop("active_activity_id", None)
    st.session_state.pop("activity_screen", None)
    st.session_state.pop("activity_explain_step", None)
    st.session_state.pop("activity_timer_start", None)
    st.session_state.pop("activity_launch_source", None)
    st.rerun()


# DETERMINISTIC: only an explicit daily-plan launch may change persisted plan progress; missing or unknown sources safely do not.
def is_plan_activity_launch(source: str | None) -> bool:
    return source == "plan"


def _tube_fill_pct(phase_index: int, total_steps: int) -> float:
    """Progress-tube fill for one phase of the explain -> timer -> results
    flow. There are total_steps explanation phases plus the timer phase
    plus the results phase (total_steps + 2 phases total); the tube only
    reaches 100% on the last of those (results) -- every earlier phase,
    including the timer screen, is a progressive fraction toward it, never
    full."""
    return (phase_index + 1) / (total_steps + 2) * 100.0


def _render_topbar(step_idx: int, total: int) -> None:
    fill_pct = _tube_fill_pct(step_idx, total)
    c1, c2, c3 = st.columns([1, 7, 1])
    with c1:
        if st.button("✕", key="act_close_btn", help=t("capture_cancel")):
            _exit_to_plan()
    with c2:
        _md(f'<div class="act-progress-track"><div class="act-progress-fill" style="width:{fill_pct:.1f}%;"></div></div>')
    with c3:
        if st.button("›", key="act_skip_btn", help=t("activity_continue_button")):
            st.session_state.activity_explain_step = total - 1
            st.session_state.activity_screen = "results"
            st.rerun()


def render_activity_explanation(activity: Activity) -> None:
    step_idx = st.session_state.get("activity_explain_step", 0)
    total = len(activity.steps)
    step = activity.steps[step_idx]

    _render_topbar(step_idx, total)
    _md(f'<div class="act-title">{activity.title}</div>')

    with st.container(key=f"act_illustration_{activity.id}"):
        st.image(step.illustration, use_container_width=True)

    dots = "".join(
        f'<div class="act-dot{" act-dot-active" if i == step_idx else ""}"></div>'
        for i in range(total)
    )
    _md(f'<div class="act-step-dots">{dots}</div>')
    _md(f'<div class="act-instruction">{step.instruction.format(n=step_idx + 1)}</div>')
    _render_practice_paragraph(step.speech_paragraph)

    st.write("")
    with st.container(key="act_continue_btn"):
        if st.button(t("activity_continue_button"), key="act_continue", type="primary", use_container_width=True):
            if step_idx >= total - 1:
                st.session_state.activity_screen = "timer"
            else:
                st.session_state.activity_explain_step = step_idx + 1
            st.rerun()


def _format_mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60}:{total % 60:02d}"


@st.fragment(run_every=1)
def _render_timer_clock(activity: Activity) -> None:
    """The only part of Screen B that needs to re-run every second. Scoped
    as its own fragment (rather than a whole-script sleep+st.rerun() loop)
    so Streamlit only re-renders this small subtree on each tick -- doing
    it as a full-script rerun instead was tried first and caused stray
    widgets from the *previous* screen to visibly bleed into this one on
    the explain->timer transition (confirmed via manual browser testing),
    since a full rerun re-diffs the entire element tree every single tick
    instead of just this fragment's."""
    remaining = activity.timer_seconds - (time.time() - st.session_state.activity_timer_start)
    if remaining <= 0:
        st.session_state.activity_screen = "results"
        st.session_state.pop("activity_timer_start", None)
        st.rerun(scope="app")
        return

    _md(f'<div class="act-timer-label">{t("activity_timer_label")}</div>')
    _md(f'<div class="act-timer-clock">{_format_mmss(remaining)}</div>')


def render_activity_timer(activity: Activity) -> None:
    """Screen B: re-shows all step instructions as a reminder and counts
    down `activity.timer_seconds` on its own, advancing to the results
    screen the instant it reaches zero -- no user interaction required."""
    if "activity_timer_start" not in st.session_state:
        st.session_state.activity_timer_start = time.time()

    total_steps = len(activity.steps)
    fill_pct = _tube_fill_pct(total_steps, total_steps)  # phase right after the last explanation step

    c1, c2 = st.columns([1, 7])
    with c1:
        if st.button("✕", key="act_timer_close_btn", help=t("capture_cancel")):
            _exit_to_plan()
    with c2:
        _md(f'<div class="act-progress-track"><div class="act-progress-fill" style="width:{fill_pct:.1f}%;"></div></div>')

    _md(f'<div class="act-title">{activity.title}</div>')

    reminder_html = "".join(
        f'<div class="act-timer-instruction">{i}. {step.instruction.format(n=i)}</div>'
        for i, step in enumerate(activity.steps, start=1)
    )
    _md(f"""
        <div class="act-timer-reminder-heading">{t('activity_timer_reminder_heading')}</div>
        <div class="act-timer-instructions">{reminder_html}</div>
        """)

    speech_paragraph = next((step.speech_paragraph for step in activity.steps if step.speech_paragraph), None)
    _render_practice_paragraph(speech_paragraph)

    _render_timer_clock(activity)


def _render_metric_row(metric: ActivityMetric) -> None:
    _md(f"""
        <div class="act-metric-row">
          <div class="act-metric-top">
            <span class="act-metric-label">{metric.label}</span>
            <span class="act-metric-value">{metric.display}</span>
          </div>
          {gradient_bar(metric.value, metric.domain_max, metric.cutoff, COLORS['streak_amber'])}
        </div>
        """)


def render_activity_results(activity: Activity, metrics: list[ActivityMetric] | None = None) -> None:
    # The only screen in the explain -> timer -> results flow where the
    # tube is full: every earlier screen renders it via _tube_fill_pct,
    # which by construction stays below 100% until this phase.
    completion_subtext = "activity_complete_subtext" if is_plan_activity_launch(
        st.session_state.get("activity_launch_source")
    ) else "activity_library_complete_subtext"
    _md('<div class="act-progress-track"><div class="act-progress-fill" style="width:100.0%;"></div></div>')
    _md(f"""
        <div class="act-tabs">
          <span class="act-tab act-tab-active">{t('activity_results_tab')}</span>
          <span class="act-tab">{t('activity_audios_tab')}</span>
        </div>
        """)

    with st.container(key="act_results_illustration"):
        st.image("images/celebration.png", use_container_width=True)

    _md(f'<div class="act-results-heading">{t("activity_complete_heading")}</div>')
    _md(f'<div class="act-results-subtext">{t(completion_subtext)}</div>')

    for metric in (metrics if metrics is not None else _placeholder_metrics()):
        _render_metric_row(metric)

    st.write("")
    with st.container(key="act_done_btn"):
        if st.button(t("activity_done_button"), key="act_done", type="primary", use_container_width=True):
            if not is_plan_activity_launch(st.session_state.get("activity_launch_source")):
                _exit_to_plan()
                return

            from ui.training_plan import mark_item_complete, TRAINING_PLAN
            from storage.training_progress import TrainingProgressStore

            prior_day_index = TrainingProgressStore().load()["day_index"]
            state = mark_item_complete(activity.id)

            next_id = None
            if state["day_index"] == prior_day_index:
                completed = set(state["completed_today"])
                next_id = next(
                    (i for i in TRAINING_PLAN[state["day_index"]].activity_ids if i not in completed),
                    None,
                )

            if next_id is not None:
                # Same day, more activities left -- go straight into the next
                # one instead of dropping back to the plan list (NEW_RECORDING
                # can never land here: it's always day-first and already
                # completed by the time an Activity screen is reachable at all).
                st.session_state.active_activity_id = next_id
                st.session_state.activity_screen = "explain"
                st.session_state.activity_explain_step = 0
                st.session_state.pop("activity_timer_start", None)
                st.rerun()
            else:
                _exit_to_plan()


def render_activity_flow() -> None:
    from ui.exercise_library import EXERCISE_LIBRARY  # deferred: exercise_library imports this module

    active_id = st.session_state.get("active_activity_id")
    activity = next((a for a in EXERCISE_LIBRARY if a.id == active_id), None)
    if activity is None:
        _exit_to_plan()
        return

    screen = st.session_state.get("activity_screen", "explain")
    if screen == "explain":
        render_activity_explanation(activity)
    elif screen == "timer":
        render_activity_timer(activity)
    else:
        render_activity_results(activity)
