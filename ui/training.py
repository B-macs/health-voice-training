"""Gamified daily "Training" plan screen -- streak/XP/daily-plan UI in the
Duolingo mold: a status bar (streak + freeze counters, an XP pill), a
weekly streak row, a "New Recording" button into the existing capture flow
(unchanged -- see ui/capture.py), and a sequential "Daily plan" of cards
(Next -> Complete, one at a time).

The daily plan is driven by ui/training_plan.py's fixed 10-day baseline,
persisted via storage/training_progress.py -- "today's plan" is whichever day
the user has reached, always starting with a recording card (the existing
capture flow, gated first in the sequence the same way any other card is)
followed by that day's two or three practice activities and a cool-down.
Completing a day's last item advances to the next day automatically (see
ui.training_plan.mark_item_complete), but that next day doesn't unlock
same-day -- render_training_tab() shows a "come back tomorrow" card
instead of a daily list until the calendar date actually changes. After
day 10 it shows the whole-plan completion card instead. A separate optional
Activity Library exposes all 22 catalogue cards. Library practice uses the
same activity flow but never changes daily-plan progress, XP, or the streak.

XP is derived from *today's* completed items (len(completed_today) *
XP_PER_ACTIVITY), so it resets when the plan advances to a new day --
consistent with "daily energy goal" in the copy. Streak/freeze counters
are still static ephemeral session values, not wired to the persisted
plan progress yet.

Not implemented: a literal continuous dotted line connecting every card's
timeline node. Each card is its own independent st.container (required so
it can hold a real, clickable st.button), and Streamlit lays those out as
separate DOM blocks -- there's no clean way to bleed one continuous line
across independent containers without much more invasive restructuring.
Each card instead gets its own step node (ring/check/hollow circle) beside
its status label, which conveys the same "where am I in the sequence"
information.
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from config import t
from ui.styles import COLORS
from ui.html_utils import flatten
from ui.activities import Activity
from ui.exercise_library import EXERCISE_LIBRARY
from ui.training_plan import TRAINING_PLAN, NEW_RECORDING, sync_plan_to_today

XP_PER_ACTIVITY = 10
DAILY_XP_GOAL = 20
WEEKDAY_LABELS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_ILLUSTRATION_BGS = [COLORS["blue"], COLORS["gold"], COLORS["optimal"]]
_EXERCISE_BY_ID = {a.id: a for a in EXERCISE_LIBRARY}


def _md(html: str) -> None:
    st.markdown(flatten(html), unsafe_allow_html=True)


def _ensure_state() -> None:
    if "training_streak_days" not in st.session_state:
        st.session_state.training_streak_days = 1
    if "training_freeze_days" not in st.session_state:
        st.session_state.training_freeze_days = 0
    if "training_help_open" not in st.session_state:
        st.session_state.training_help_open = False


def _xp(progress: dict) -> int:
    return len(progress["completed_today"]) * XP_PER_ACTIVITY


def _render_status_bar(progress: dict) -> None:
    xp = _xp(progress)
    _md(f"""
        <div class="tr-status-bar">
          <div class="tr-streak-group">
            <span class="tr-pill">&#128293; {st.session_state.training_streak_days}</span>
            <span class="tr-pill">&#10052;&#65039; {st.session_state.training_freeze_days}</span>
          </div>
          <div class="tr-pill tr-xp-pill"><span class="tr-xp-dot"></span>&#9889; {xp}/{DAILY_XP_GOAL}</div>
        </div>
        """)


def _render_weekly_row(progress: dict) -> None:
    """Renders Mon-Sun of the current calendar week against
    progress["history"] (see storage/training_progress.py and
    ui.training_plan.sync_plan_to_today) -- a day shows a checkmark
    whenever that exact date is recorded "complete" (including today,
    once today's plan is finished and mark_item_complete has already
    locked out further training for the day), an X only if a past day is
    recorded "missed", the fire icon for today while it's still pending,
    and otherwise the neutral "future" styling (e.g. a date before the
    plan was ever started has no history entry, so it isn't falsely
    marked missed)."""
    today = date.today()
    today_idx = today.weekday()  # 0=Monday
    week_start = today - timedelta(days=today_idx)
    goal_met = _xp(progress) >= DAILY_XP_GOAL
    history = progress["history"]

    cells = []
    for i, label in enumerate(WEEKDAY_LABELS):
        status = history.get((week_start + timedelta(days=i)).isoformat())
        if status == "complete":
            marker = '<div class="tr-day-circle tr-day-complete">&#10003;</div>'
        elif i == today_idx:
            cls = "tr-day-active-lit" if goal_met else "tr-day-active-unlit"
            marker = f'<div class="tr-day-circle {cls}">&#128293;</div>'
        elif i < today_idx and status == "missed":
            marker = '<div class="tr-day-circle tr-day-missed">&#10005;</div>'
        else:
            marker = '<div class="tr-day-circle tr-day-future"></div>'
        cells.append(f'<div class="tr-day-col">{marker}<span class="tr-day-label">{label}</span></div>')

    _md(f'<div class="tr-week-row">{"".join(cells)}</div>')


def _render_new_recording_button() -> None:
    if st.button(f"\U0001F3A4 {t('new_recording_button')}", key="training_new_recording", use_container_width=True):
        st.session_state.view = "capture"
        st.session_state.capture_step = 1
        st.rerun()


def _render_plan_header(day_number: int) -> None:
    day_label = t("training_day_of_label").format(day=day_number, total=len(TRAINING_PLAN))
    _md(f"""
        <div class="tr-plan-header">
          <span class="tr-plan-title">{t("training_daily_plan_title")}</span>
          <span class="tr-pill">{day_label}</span>
        </div>
        """)
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("?", key="training_help_toggle", help=t("training_help_aria")):
            st.session_state.training_help_open = not st.session_state.training_help_open
    if st.session_state.training_help_open:
        st.caption(t("training_help_text"))


def _card_chrome(status: str) -> tuple[str, str]:
    if status == "next":
        node_html = '<div class="tr-card-node tr-card-node-next">&#9679;</div>'
        status_html = f'<span class="tr-card-status tr-card-status-next">{t("capture_next")}</span>'
    elif status == "complete":
        node_html = '<div class="tr-card-node tr-card-node-complete">&#10003;</div>'
        status_html = f'<span class="tr-card-status tr-card-status-complete">{t("training_status_complete")}</span>'
    else:
        node_html = '<div class="tr-card-node tr-card-node-upcoming"></div>'
        status_html = ""
    return node_html, status_html


def _render_recording_card(status: str) -> None:
    """First card of every plan day -- launches the existing capture flow
    (unchanged). Completion is detected in app.py's run_analysis() via
    ui.training_plan.mark_item_complete(NEW_RECORDING), not here."""
    with st.container(key=f"card_training_rec_{status}"):
        node_html, status_html = _card_chrome(status)
        _md(f"""
            <div class="tr-card-top">{node_html}{status_html}</div>
            <div class="tr-card-body">
              <div>
                <div class="tr-card-title">{t('new_recording_button')}</div>
                <div class="tr-card-meta">
                  <span>&#128337; ~2m</span>
                  <span>&#127908; {t('training_recording_category')}</span>
                </div>
              </div>
              <div class="tr-card-illustration" style="background:{COLORS['optimal']}22;">&#127908;</div>
            </div>
            """)

        if status == "next":
            if st.button(t("training_start_button"), key="training_start_recording",
                         type="primary", use_container_width=True):
                st.session_state.view = "capture"
                st.session_state.capture_step = 1
                st.rerun()
        elif status == "upcoming":
            st.button(t("training_start_button"), key="training_start_recording",
                      use_container_width=True, disabled=True)


# DETERMINISTIC: records an explicit launch source; unknown sources are treated as optional by the results screen and cannot change plan progress.
def _launch_activity(activity_id: str, source: str) -> None:
    st.session_state.view = "activity"
    st.session_state.active_activity_id = activity_id
    st.session_state.activity_screen = "explain"
    st.session_state.activity_explain_step = 0
    st.session_state.activity_launch_source = source
    st.session_state.pop("activity_timer_start", None)
    st.rerun()


def _render_activity_card(activity: Activity, status: str, index: int) -> None:
    """Renders one activity card. Tapping "Start" (status == "next")
    launches the Screen A/C flow in ui/activities.py, which marks the
    activity complete itself once the user finishes it -- this function
    no longer completes anything directly."""
    container_key = f"card_training_act_{status}_{activity.id}"

    with st.container(key=container_key):
        node_html, status_html = _card_chrome(status)
        illustration_bg = _ILLUSTRATION_BGS[index % len(_ILLUSTRATION_BGS)]
        _md(f"""
            <div class="tr-card-top">{node_html}{status_html}</div>
            <div class="tr-card-body">
              <div>
                <div class="tr-card-title">{activity.title}</div>
                <div class="tr-card-meta">
                  <span>&#128337; {activity.duration}</span>
                  <span>&#127919; {activity.category}</span>
                </div>
              </div>
              <div class="tr-card-illustration" style="background:{illustration_bg}22;">&#128444;&#65039;</div>
            </div>
            """)

        if status == "next":
            if st.button(t("training_start_button"), key=f"training_start_{activity.id}",
                         type="primary", use_container_width=True):
                _launch_activity(activity.id, "plan")
        elif status == "upcoming":
            st.button(t("training_start_button"), key=f"training_start_{activity.id}",
                      use_container_width=True, disabled=True)


# DETERMINISTIC: renders optional catalogue cards without plan status; an empty filter produces a clear empty-state message.
def _render_library_activity_card(activity: Activity, index: int) -> None:
    with st.container(key=f"card_training_library_{activity.id}"):
        illustration_bg = _ILLUSTRATION_BGS[index % len(_ILLUSTRATION_BGS)]
        _md(f"""
            <div class="tr-card-body">
              <div>
                <div class="tr-card-title">{activity.title}</div>
                <div class="tr-card-meta">
                  <span>&#128337; {activity.duration}</span>
                  <span>&#127919; {activity.category}</span>
                </div>
              </div>
              <div class="tr-card-illustration" style="background:{illustration_bg}22;">&#128444;&#65039;</div>
            </div>
            """)
        if st.button(t("training_library_start_button"), key=f"training_library_start_{activity.id}",
                     type="primary", use_container_width=True):
            _launch_activity(activity.id, "library")


# DETERMINISTIC: lists every catalogue activity; when a category has no match, it shows an empty state instead of changing plan data.
def _render_activity_library() -> None:
    _md('<hr class="tr-divider" />')
    library_title = f"\U0001F4DA {t('training_library_title')} · {len(EXERCISE_LIBRARY)}"
    with st.expander(library_title, expanded=False):
        st.caption(t("training_library_subtext"))
        categories = [t("training_library_all_categories"), *dict.fromkeys(a.category for a in EXERCISE_LIBRARY)]
        selected_category = st.selectbox(
            t("training_library_filter_label"), categories, key="training_library_category",
        )
        activities = EXERCISE_LIBRARY if selected_category == categories[0] else [
            activity for activity in EXERCISE_LIBRARY if activity.category == selected_category
        ]
        if not activities:
            st.info(t("training_library_empty"))
            return

        previous_category = None
        for index, activity in enumerate(activities):
            if activity.category != previous_category:
                st.caption(activity.category)
                previous_category = activity.category
            _render_library_activity_card(activity, index)


def _render_plan_complete() -> None:
    with st.container(key="card_training_plan_complete"):
        _md(f"""
            <div class="tr-plan-complete-title">{t('training_plan_complete_title')}</div>
            <div class="tr-plan-complete-body">{t('training_plan_complete_body')}</div>
            """)


def _render_day_complete() -> None:
    """Shown once today's plan day is fully done. mark_item_complete
    pushes current_day_date to tomorrow the moment a day finishes, so this
    stays in place -- no further training offered or required -- until
    the calendar actually turns over and sync_plan_to_today unlocks the
    next day."""
    with st.container(key="card_training_day_complete"):
        _md(f"""
            <div class="tr-plan-complete-title">{t('training_day_complete_title')}</div>
            <div class="tr-plan-complete-body">{t('training_day_complete_body')}</div>
            """)


def render_training_tab() -> None:
    _ensure_state()
    progress = sync_plan_to_today()
    day_index = progress["day_index"]

    _render_status_bar(progress)
    _render_weekly_row(progress)
    _render_new_recording_button()
    _md('<hr class="tr-divider" />')

    if day_index >= len(TRAINING_PLAN):
        _render_plan_complete()
    elif progress["current_day_date"] > date.today().isoformat():
        _render_day_complete()
    else:
        _render_plan_header(day_index + 1)

        today = TRAINING_PLAN[day_index]
        completed_today = set(progress["completed_today"])
        next_assigned = False

        for i, item_id in enumerate(today.activity_ids):
            if item_id in completed_today:
                status = "complete"
            elif not next_assigned:
                status = "next"
                next_assigned = True
            else:
                status = "upcoming"

            if item_id == NEW_RECORDING:
                _render_recording_card(status)
            else:
                _render_activity_card(_EXERCISE_BY_ID[item_id], status, i)

    _render_activity_library()
