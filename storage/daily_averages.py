"""Canonical per-day median of every recording logged that day.

Raw recordings (storage/logger.py's JsonlRecordStore) are append-only and
never modified. This is a separate, derived store: whenever a new
recording is logged, storage/logger.py's log_session() recomputes the
median for THAT day from every raw recording logged that day and
upserts it here, replacing whatever was there before. So:
  - a day with one recording: that recording IS the day's value.
  - a day with 2+ recordings (the user redid it because a reading felt
    off): the day's value is their median, recalculated from scratch
    each time a new same-day reading is added. Median aggregation prevents
    one poor retry from dominating a personal trend while preserving the
    within-day spread/count for review.

daily_average_records() (the pure function underneath the persisted
store) is also used directly by ui/aggregation.py to build every
day/week/month chart and average, so a chart can never drift from what
gets persisted -- both read the exact same computation, whether or not
daily_averages.jsonl happens to be present/up to date.
"""
from __future__ import annotations

import json
import math
import os
import statistics

from storage.dates import local_date, sort_records
from storage.record_metadata import analysis_metadata


def group_by_date(records: list[dict]) -> dict[str, list[dict]]:
    by_date: dict[str, list[dict]] = {}
    for r in records:
        date_str = local_date(r).isoformat()
        by_date.setdefault(date_str, []).append(r)
    return by_date


# DETERMINISTIC: summarize repeated numeric readings with a robust median; fallback ignores missing/non-finite values.
def _median_by_key(dicts: list[dict]) -> dict:
    keys: set[str] = set()
    for d in dicts:
        keys.update(d.keys())
    out = {}
    for k in keys:
        values = [
            d[k] for d in dicts
            if d.get(k) is not None and isinstance(d[k], (int, float)) and math.isfinite(d[k])
        ]
        out[k] = statistics.median(values) if values else None
    return out


# DETERMINISTIC: retain within-day range/count for auditability; fallback omits unavailable values.
def _spread_by_key(dicts: list[dict]) -> dict:
    keys: set[str] = set()
    for d in dicts:
        keys.update(d.keys())
    out = {}
    for k in keys:
        values = [
            d[k] for d in dicts
            if d.get(k) is not None and isinstance(d[k], (int, float)) and math.isfinite(d[k])
        ]
        if values:
            out[k] = {"min": min(values), "max": max(values), "n": len(values)}
    return out


def compute_daily_average_record(date_str: str, day_records: list[dict]) -> dict:
    """One recording that day: that reading is the value. Two or more:
    their numeric median. The most recent raw record's stored norm snapshot
    stays attached; current defaults must never silently reinterpret history."""
    if not day_records:
        raise ValueError("day_records must contain at least one record")
    ordered = sort_records(day_records)
    parameters = _median_by_key([r["parameters"] for r in ordered])
    indices = _median_by_key([r["indices"] for r in ordered])
    latest = ordered[-1]
    protocol_versions = sorted({analysis_metadata(r)["protocol_version"] for r in ordered})
    return {
        "date": date_str,
        "timestamp": f"{date_str}T00:00:00+00:00",
        "n": len(ordered),
        "parameters": parameters,
        "indices": indices,
        "norms": latest["norms"],
        "spread": {
            "parameters": _spread_by_key([r["parameters"] for r in ordered]),
            "indices": _spread_by_key([r["indices"] for r in ordered]),
        },
        "aggregation_meta": {
            "method": "median_per_calendar_day_v2",
            "norms_policy": "latest_raw_record_snapshot",
            "source_protocol_versions": protocol_versions,
        },
    }


def daily_average_records(records: list[dict]) -> list[dict]:
    """Every raw record -> one median record per local calendar day, sorted
    by date."""
    by_date = group_by_date(records)
    return [compute_daily_average_record(d, by_date[d]) for d in sorted(by_date.keys())]


class DailyAverageStore:
    def __init__(self, path: str = "daily_averages.jsonl"):
        self.path = path

    def upsert_from_raw(self, all_raw_records: list[dict], date_str: str) -> dict:
        """Recompute and persist the canonical median for `date_str` from
        every raw recording logged that day, replacing any previous value
        for that date. Called automatically after each new recording is
        logged -- see storage/logger.py's log_session()."""
        day_records = [r for r in all_raw_records if local_date(r).isoformat() == date_str]
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
