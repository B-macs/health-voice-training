"""Persisted progress through the 20-day training plan (see
ui/training_plan.py) -- which day the user is on, which of that day's
items are done so far, `current_day_date` (the calendar date the active
day_index started on), and `history` (a calendar-date -> "complete"/
"missed" map used by ui.training_plan.sync_plan_to_today to catch the
plan up with real time and by ui/training.py's weekly streak row to
render truthfully). A single JSON object, not a log: there's only one
"current position" plus a compact history map to track, unlike the
append-only recording logs in storage/logger.py and
storage/daily_averages.py.
"""
from __future__ import annotations

import copy
import json
import os

DEFAULT_STATE = {
    "day_index": 0,
    "completed_today": [],
    "current_day_date": None,
    "history": {},
}


class TrainingProgressStore:
    def __init__(self, path: str = "training_progress.json"):
        self.path = path

    def load(self) -> dict:
        state = copy.deepcopy(DEFAULT_STATE)
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                state.update(json.load(f))
        return state

    def save(self, state: dict) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
