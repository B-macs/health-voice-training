"""The 20-day plan: every day starts with a recording, no day
exceeds the 15-minute cap, every exercise in the pool gets used, and
completing a day's items advances to the next day with progress
persisted (survives closing and reopening the app). Also covers
sync_plan_to_today's calendar rollover: a day that passes without being
fully completed is recorded "missed" and the plan steps forward on its
own to keep pace with real time.
"""
from __future__ import annotations

from datetime import date, timedelta

from ui.exercise_library import EXERCISE_LIBRARY
from ui.training_plan import (
    NEW_RECORDING, TRAINING_PLAN, mark_item_complete, plan_day_minutes,
    sync_plan_to_today,
)
from storage.training_progress import TrainingProgressStore


# DETERMINISTIC: validates static activity-card data and fails if the plan schema changes.
def test_plan_has_twenty_days_and_valid_activity_templates():
    assert len(TRAINING_PLAN) == 20
    assert [d.day_number for d in TRAINING_PLAN] == list(range(1, 21))
    assert len(EXERCISE_LIBRARY) == 22

    activity_ids = [activity.id for activity in EXERCISE_LIBRARY]
    assert len(activity_ids) == len(set(activity_ids))
    for activity in EXERCISE_LIBRARY:
        assert activity.timer_seconds > 0
        assert len(activity.steps) == 4


def test_every_day_starts_with_a_new_recording():
    for day in TRAINING_PLAN:
        assert day.activity_ids[0] == NEW_RECORDING


def test_every_day_stays_under_the_fifteen_minute_cap():
    for day in TRAINING_PLAN:
        minutes = plan_day_minutes(day)
        assert minutes <= 15, f"Day {day.day_number} is {minutes} min, over the 15-min cap"


def test_every_pool_exercise_is_scheduled_at_least_once():
    scheduled = {aid for day in TRAINING_PLAN for aid in day.activity_ids}
    scheduled_activity_ids = scheduled - {NEW_RECORDING}
    pool_ids = {a.id for a in EXERCISE_LIBRARY}
    missing = pool_ids - scheduled_activity_ids
    assert not missing, f"exercises never scheduled: {missing}"
    unknown = scheduled_activity_ids - pool_ids
    assert not unknown, f"scheduled ids missing from exercise library: {unknown}"


def test_completing_a_day_advances_to_the_next_and_resets(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day1 = TRAINING_PLAN[0]

    for item_id in day1.activity_ids[:-1]:
        state = mark_item_complete(item_id, store=store)
        assert state["day_index"] == 0  # still day 1, not all items done yet

    state = mark_item_complete(day1.activity_ids[-1], store=store)
    assert state["day_index"] == 1  # advanced to day 2
    assert state["completed_today"] == []  # reset for the new day


def test_progress_persists_across_store_instances(tmp_path):
    """Progress must survive closing and reopening the app -- a fresh
    TrainingProgressStore pointed at the same file sees the same state."""
    path = str(tmp_path / "training_progress.json")
    mark_item_complete(NEW_RECORDING, store=TrainingProgressStore(path))

    reloaded = TrainingProgressStore(path).load()
    assert reloaded["completed_today"] == [NEW_RECORDING]
    assert reloaded["day_index"] == 0


def test_plan_already_complete_is_a_noop(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    store.save({"day_index": len(TRAINING_PLAN), "completed_today": []})
    state = mark_item_complete("anything", store=store)
    assert state["day_index"] == len(TRAINING_PLAN)
    assert state["completed_today"] == []


def test_first_sync_starts_today_with_no_history(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    state = sync_plan_to_today(store, today=day_one)
    assert state["day_index"] == 0
    assert state["current_day_date"] == "2026-01-01"
    assert state["history"] == {}


def test_missed_days_advance_and_are_recorded(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    sync_plan_to_today(store, today=day_one)

    # user opens the app two calendar days later without having trained
    state = sync_plan_to_today(store, today=day_one + timedelta(days=2))

    assert state["day_index"] == 2
    assert state["history"] == {"2026-01-01": "missed", "2026-01-02": "missed"}
    assert state["current_day_date"] == "2026-01-03"


def test_missed_day_rollover_stops_at_the_end_of_the_plan(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    sync_plan_to_today(store, today=day_one)

    state = sync_plan_to_today(store, today=day_one + timedelta(days=30))
    assert state["day_index"] == len(TRAINING_PLAN)
    assert len(state["history"]) == len(TRAINING_PLAN)


def test_completed_day_is_recorded_and_advances(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    day1 = TRAINING_PLAN[0]

    state = None
    for item_id in day1.activity_ids:
        state = mark_item_complete(item_id, store=store, today=day_one)

    assert state["day_index"] == 1
    assert state["history"] == {"2026-01-01": "complete"}
    # current_day_date is pushed to *tomorrow*, not today, so the next day
    # doesn't unlock same-day -- this is exactly what
    # ui.training.render_training_tab checks to show the "come back
    # tomorrow" card instead of a startable next day.
    assert state["current_day_date"] == "2026-01-02"


def test_next_day_stays_locked_until_the_calendar_turns_over(tmp_path):
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    day1 = TRAINING_PLAN[0]
    for item_id in day1.activity_ids:
        mark_item_complete(item_id, store=store, today=day_one)

    # re-opening the app later the same day must not unlock day 2 early
    state = sync_plan_to_today(store, today=day_one)
    assert state["day_index"] == 1
    assert state["current_day_date"] == "2026-01-02"

    # the next calendar day, day 2 becomes the active day on its own
    state = sync_plan_to_today(store, today=day_one + timedelta(days=1))
    assert state["day_index"] == 1
    assert state["current_day_date"] == "2026-01-02"


def test_completing_after_a_missed_day_lands_on_the_rolled_forward_day(tmp_path):
    """A click that arrives after a day (or several) went by untouched
    should complete *today's* rolled-forward day, not the stale one."""
    store = TrainingProgressStore(str(tmp_path / "training_progress.json"))
    day_one = date(2026, 1, 1)
    sync_plan_to_today(store, today=day_one)

    day_three = day_one + timedelta(days=2)
    day3_plan = TRAINING_PLAN[2]
    state = None
    for item_id in day3_plan.activity_ids:
        state = mark_item_complete(item_id, store=store, today=day_three)

    assert state["day_index"] == 3
    assert state["history"]["2026-01-01"] == "missed"
    assert state["history"]["2026-01-02"] == "missed"
    assert state["history"]["2026-01-03"] == "complete"
