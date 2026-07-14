"""The 10-day baseline training plan.

Fixed, one-time schedule across ui/exercise_library.py's 12-exercise pool,
built under two hard constraints: every day starts with a fresh voice
recording (NEW_RECORDING, the existing standalone capture flow -- not
one of the 12 Activity entries), and no day's total time -- recording
included -- exceeds 15 minutes. Budget uses each exercise's own upper
duration estimate plus RECORDING_MINUTES_ESTIMATE, so the real total is
never more than what's checked here (see test_training_plan.py, which
asserts every day in TRAINING_PLAN stays under the cap).

This is a fixed 10-day baseline, not a rotating/repeating curriculum --
each of the 4 Pulmo-Train exercises (the tool with a documented track
record for this condition, see Investigation/01_Voice_Quality_Overview.html)
appears 2-3 times across the 10 days, the other 8 exercises appear at
least once, and every day ends with the same short cool-down. After day
10, re-assess against the daily-recorded trend before designing a longer
program -- see PlanProgress.is_complete.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from storage.training_progress import TrainingProgressStore

NEW_RECORDING = "new_recording"
RECORDING_MINUTES_ESTIMATE = 2.0


@dataclass
class PlanDay:
    day_number: int  # 1-10, matches its position in TRAINING_PLAN
    activity_ids: list[str]  # NEW_RECORDING first, then EXERCISE_LIBRARY ids


TRAINING_PLAN: list[PlanDay] = [
    PlanDay(1, [NEW_RECORDING, "pulmo_warmup_hum", "vfe_sustained_i", "cooldown_carryover"]),
    PlanDay(2, [NEW_RECORDING, "pulmo_pitch_glides", "vfe_ascending_glide", "cooldown_carryover"]),
    PlanDay(3, [NEW_RECORDING, "pulmo_water_resistance", "vfe_descending_glide", "cooldown_carryover"]),
    PlanDay(4, [NEW_RECORDING, "pulmo_reading_carryover", "resonant_humming", "cooldown_carryover"]),
    PlanDay(5, [NEW_RECORDING, "pulmo_warmup_hum", "breath_sz_ratio", "cooldown_carryover"]),
    PlanDay(6, [NEW_RECORDING, "pulmo_pitch_glides", "twang_brightness", "cooldown_carryover"]),
    PlanDay(7, [NEW_RECORDING, "pulmo_water_resistance", "loudness_range_glide", "cooldown_carryover"]),
    PlanDay(8, [NEW_RECORDING, "pulmo_reading_carryover", "vfe_sustained_i", "cooldown_carryover"]),
    PlanDay(9, [NEW_RECORDING, "pulmo_warmup_hum", "vfe_ascending_glide", "cooldown_carryover"]),
    PlanDay(10, [NEW_RECORDING, "pulmo_pitch_glides", "vfe_descending_glide", "cooldown_carryover"]),
]


def _duration_upper_bound_minutes(duration: str) -> float:
    """"3m" -> 3.0, "3-4m" -> 4.0 (the upper bound, for a conservative
    worst-case time budget)."""
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", duration)]
    return max(numbers)


def plan_day_minutes(day: PlanDay) -> float:
    """Conservative (upper-bound) total minutes for one day, including the
    recording -- the number test_training_plan.py checks against the
    15-minute cap."""
    from ui.exercise_library import EXERCISE_LIBRARY

    by_id = {a.id: a for a in EXERCISE_LIBRARY}
    total = RECORDING_MINUTES_ESTIMATE
    for activity_id in day.activity_ids:
        if activity_id == NEW_RECORDING:
            continue
        total += _duration_upper_bound_minutes(by_id[activity_id].duration)
    return total


def sync_plan_to_today(store: TrainingProgressStore | None = None, today: date | None = None) -> dict:
    """Keeps day_index in step with the calendar. Every calendar date the
    plan sits on the same day_index without that day having been fully
    completed becomes a "missed" day in `history`, and the plan steps
    forward one day at a time until it reaches `today` (or runs out of
    plan) -- so re-opening the app after skipping a day, or several,
    lands on today's day instead of a stale backlog, and the weekly
    streak row (ui/training.py) has a real complete/missed record for
    each date instead of guessing from the weekday alone."""
    store = store or TrainingProgressStore()
    today = today or date.today()
    today_str = today.isoformat()
    state = store.load()

    if state["current_day_date"] is None:
        state["current_day_date"] = today_str
        store.save(state)
        return state

    changed = False
    while state["current_day_date"] < today_str and state["day_index"] < len(TRAINING_PLAN):
        state["history"][state["current_day_date"]] = "missed"
        state["day_index"] += 1
        state["completed_today"] = []
        state["current_day_date"] = (date.fromisoformat(state["current_day_date"]) + timedelta(days=1)).isoformat()
        changed = True

    if changed:
        store.save(state)
    return state


def mark_item_complete(
    item_id: str, store: TrainingProgressStore | None = None, today: date | None = None,
) -> dict:
    """Marks `item_id` (NEW_RECORDING or an Activity id) done for the
    current plan day. Once every item in that day's plan is done, records
    that date as "complete" in history, advances to the next day, and
    resets today's completion list -- persisted, so progress survives
    closing and reopening the app. No-op (returns state unchanged) once
    the whole plan is already complete. Runs sync_plan_to_today first so a
    click after a skipped day still lands on the right (rolled-forward)
    day rather than completing a stale one.

    The newly-advanced day's `current_day_date` is set to *tomorrow*, not
    today -- once a day is done, no further training is required or even
    selectable until the calendar actually turns over (ui.training's
    render_training_tab shows a "come back tomorrow" card whenever
    current_day_date is still in the future). This also keeps history
    collision-free: today's date already holds this day's "complete"
    entry, so the next day must start accruing against a different date."""
    store = store or TrainingProgressStore()
    today = today or date.today()
    state = sync_plan_to_today(store, today)
    day_index = state["day_index"]
    if day_index >= len(TRAINING_PLAN):
        return state

    completed = set(state["completed_today"])
    completed.add(item_id)
    today_ids = set(TRAINING_PLAN[day_index].activity_ids)

    if today_ids <= completed:
        state["history"][state["current_day_date"]] = "complete"
        state["day_index"] = day_index + 1
        state["completed_today"] = []
        state["current_day_date"] = (today + timedelta(days=1)).isoformat()
    else:
        state["completed_today"] = sorted(completed)

    store.save(state)
    return state
