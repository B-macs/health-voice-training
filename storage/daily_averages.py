"""Canonical per-day average of every recording logged that day.

Raw recordings (storage/logger.py's JsonlRecordStore) are append-only and
never modified. This is a separate, derived store: whenever a new
recording is logged, storage/logger.py's log_session() recomputes the
average for THAT day from every raw recording logged that day and
upserts it here, replacing whatever was there before. So:
  - a day with one recording: that recording IS the day's value.
  - a day with 2+ recordings (the user redid it because a reading felt
    off): the day's value is their average, recalculated from scratch
    each time a new same-day reading is added.

daily_average_records() (the pure function underneath the persisted
store) is also used directly by ui/aggregation.py to build every
day/week/month chart and average, so a chart can never drift from what
gets persisted -- both read the exact same computation, whether or not
daily_averages.jsonl happens to be present/up to date.
"""
from __future__ import annotations

import json
import os
import statistics


def group_by_date(records: list[dict]) -> dict[str, list[dict]]:
    by_date: dict[str, list[dict]] = {}
    for r in records:
        date_str = r["timestamp"][:10]
        by_date.setdefault(date_str, []).append(r)
    return by_date


def _mean_by_key(dicts: list[dict]) -> dict:
    keys: set[str] = set()
    for d in dicts:
        keys.update(d.keys())
    out = {}
    for k in keys:
        values = [d[k] for d in dicts if d.get(k) is not None]
        out[k] = statistics.mean(values) if values else None
    return out


def compute_daily_average_record(date_str: str, day_records: list[dict]) -> dict:
    """One recording that day: that reading is the value (mean of 1 is
    itself). Two or more: their average. Norms/flags are recomputed on
    the averaged values, not copied from any single recording."""
    from analysis.norms import flag_all

    parameters = _mean_by_key([r["parameters"] for r in day_records])
    indices = _mean_by_key([r["indices"] for r in day_records])
    norms = flag_all({**parameters, **indices})
    return {
        "date": date_str,
        "timestamp": f"{date_str}T00:00:00+00:00",
        "n": len(day_records),
        "parameters": parameters,
        "indices": indices,
        "norms": norms,
    }


def daily_average_records(records: list[dict]) -> list[dict]:
    """Every raw record -> one averaged record per calendar day it was
    logged on, sorted by date."""
    by_date = group_by_date(records)
    return [compute_daily_average_record(d, by_date[d]) for d in sorted(by_date.keys())]


class DailyAverageStore:
    def __init__(self, path: str = "daily_averages.jsonl"):
        self.path = path

    def upsert_from_raw(self, all_raw_records: list[dict], date_str: str) -> dict:
        """Recompute and persist the canonical average for `date_str` from
        every raw recording logged that day, replacing any previous value
        for that date. Called automatically after each new recording is
        logged -- see storage/logger.py's log_session()."""
        day_records = [r for r in all_raw_records if r["timestamp"][:10] == date_str]
        record = compute_daily_average_record(date_str, day_records)
        self._upsert(record)
        return record

    def rebuild_from_raw(self, all_raw_records: list[dict]) -> None:
        """Full backfill/rebuild -- recomputes every day's average from
        scratch and replaces the whole file. Useful the first time this
        store is introduced, or after raw records are edited/removed."""
        for record in daily_average_records(all_raw_records):
            self._upsert(record)

    def _upsert(self, record: dict) -> None:
        existing = self.load_all()
        existing[record["date"]] = record
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            for date in sorted(existing.keys()):
                f.write(json.dumps(existing[date], ensure_ascii=False) + "\n")

    def load_all(self) -> dict[str, dict]:
        if not os.path.exists(self.path):
            return {}
        by_date = {}
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    by_date[rec["date"]] = rec
        return by_date
