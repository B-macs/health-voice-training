"""Day/Week/Month rollups over voice_log.jsonl.

Each logged record is immutable and keyed by an ISO-8601 timestamp (see
storage/logger.py). Nothing about the schema needs to change to support
Day/Week/Month: the ISO year-week and calendar year-month are derived here,
on read, from that same timestamp. The norm used to judge each record is
read from the record itself (`record["norms"]`), not recomputed from the
current config, so a threshold line stays correct even if norms are
re-tuned later.

Day/week/month aggregation is hierarchical: aggregate() and
latest_and_prior_averages() both reduce records to one value per calendar
day first (storage.daily_averages.daily_average_records -- the same
canonical per-day average that gets persisted to daily_averages.jsonl
whenever a new recording is logged), THEN bucket by week/month. A day the
user recorded 3 times (because a reading felt off) is one data point, the
same as a day recorded once -- it never outweighs other days just for
having more redo attempts. Computing this on the fly from the raw log
here (rather than reading daily_averages.jsonl directly) means the UI
can't drift from the persisted store even if raw records are ever
edited/removed after the fact.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime

from ui.scoring import composite_stimm_score, group_score, _as_norm_range
from storage.daily_averages import daily_average_records


def load_records(path: str = "voice_log.jsonl") -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records.sort(key=lambda r: r["timestamp"])
    return records


def metric_value(record: dict, metric_key: str) -> float | None:
    """Look up one metric's value from a logged record, including the
    synthetic "composite" (Stimm-Score) metric and the "group_<name>"
    metrics (group_hoarseness/group_breathiness/group_general -- see
    ui.scoring.group_score), all computed from that record's own
    indices+norms."""
    if metric_key == "composite":
        values = {**record["parameters"], **record["indices"]}
        norms = {k: _as_norm_range(v.get("norm")) for k, v in record["norms"].items()}
        return composite_stimm_score(values, norms)
    if metric_key.startswith("group_"):
        values = {**record["parameters"], **record["indices"]}
        norms = {k: _as_norm_range(v.get("norm")) for k, v in record["norms"].items()}
        return group_score(values, norms, metric_key[len("group_"):])
    if metric_key in record["indices"]:
        return record["indices"][metric_key]
    return record["parameters"].get(metric_key)


def period_key(dt: datetime, granularity: str) -> str:
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        iso_year, iso_week, _ = dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if granularity == "month":
        return dt.strftime("%Y-%m")
    raise ValueError(f"unknown granularity: {granularity}")


@dataclass
class PeriodBucket:
    period: str
    average: float
    min: float
    max: float
    n: int


def aggregate(records: list[dict], metric_key: str, granularity: str) -> list[PeriodBucket]:
    """Buckets by day/week/month. "day" buckets raw records directly, same
    as ever -- one bucket per calendar day, average/min/max/n all describe
    that day's raw recordings. "week"/"month" bucket the PER-DAY averages
    instead (see module docstring): a day recorded 3 times becomes one
    value first, so it can't outweigh a day recorded once just for having
    more redo attempts -- n there is the number of distinct days
    contributing, not the number of raw recordings."""
    import statistics

    source = records if granularity == "day" else daily_average_records(records)

    buckets: dict[str, list[float]] = {}
    for record in source:
        value = metric_value(record, metric_key)
        if value is None:
            continue
        dt = datetime.fromisoformat(record["timestamp"])
        key = period_key(dt, granularity)
        buckets.setdefault(key, []).append(value)

    result = []
    for period in sorted(buckets.keys()):
        values = buckets[period]
        result.append(PeriodBucket(
            period=period,
            average=statistics.mean(values),
            min=min(values),
            max=max(values),
            n=len(values),
        ))
    return result


def period_to_ordinal(period: str, granularity: str) -> float:
    """A sortable, evenly-comparable number of days for a period label, so a
    trend chart can space points proportionally to real elapsed time instead
    of evenly by index -- a 4-month gap between sessions should look like a
    gap, not the same width as two sessions a day apart."""
    if granularity == "day":
        return datetime.strptime(period, "%Y-%m-%d").toordinal()
    if granularity == "week":
        iso_year, iso_week = period.split("-W")
        return datetime.strptime(f"{iso_year}-W{iso_week}-1", "%G-W%V-%u").toordinal()
    if granularity == "month":
        year, month = period.split("-")
        return datetime(int(year), int(month), 1).toordinal()
    raise ValueError(f"unknown granularity: {granularity}")


def trend_window_bounds(granularity: str, window: int, now: datetime | None = None) -> tuple[float, float]:
    """(start_ordinal, end_ordinal) spanning the last `window` periods of
    `granularity`, ending today -- e.g. granularity="day", window=30 gives
    the last 30 calendar days, regardless of how many of them actually have
    logged sessions. A chart's x-axis should span this real calendar
    window, not just "the last N buckets that happen to have data" -- with
    sparse logging that silently drags in sessions from a year ago."""
    now = now or datetime.now()
    if granularity == "day":
        end = now.date().toordinal()
        start = end - (window - 1)
    elif granularity == "week":
        end = now.date().toordinal()
        start = end - (window * 7 - 1)
    elif granularity == "month":
        total_months = now.year * 12 + (now.month - 1) - (window - 1)
        start_year, start_month0 = divmod(total_months, 12)
        start = datetime(start_year, start_month0 + 1, 1).toordinal()
        end = now.date().toordinal()
    else:
        raise ValueError(f"unknown granularity: {granularity}")
    return float(start), float(end)


def filter_to_window(
    buckets: list[PeriodBucket], granularity: str, window: int, now: datetime | None = None,
) -> list[PeriodBucket]:
    """Keep only buckets falling inside the real calendar window (see
    trend_window_bounds) -- not just the last `window` non-empty buckets."""
    start, end = trend_window_bounds(granularity, window, now)
    return [b for b in buckets if start <= period_to_ordinal(b.period, granularity) <= end]


def latest_and_prior_averages(records: list[dict], metric_key: str) -> tuple[float | None, float | None, float | None]:
    """Returns (latest_value, prev_week_avg, prev_month_avg) for the hero's
    comparison line. `latest_value` is always the most recent RAW
    recording, unaveraged -- Voice Analysis always shows the latest single
    reading, even on a day with several redo recordings. "Prev week/month"
    excludes the most recent record's own day and is built from per-day
    averages (see module docstring), so a day with several redo recordings
    doesn't outweigh a day with one, matching how Oura shows "vs. your
    recent average"."""
    if not records:
        return None, None, None
    import statistics

    latest = metric_value(records[-1], metric_key)
    today = records[-1]["timestamp"][:10]

    daily = daily_average_records(records)
    prior_days = [d for d in daily if d["date"] < today]

    week_values = [v for d in prior_days[-7:] if (v := metric_value(d, metric_key)) is not None]
    month_values = [v for d in prior_days[-30:] if (v := metric_value(d, metric_key)) is not None]

    week_avg = statistics.mean(week_values) if week_values else None
    month_avg = statistics.mean(month_values) if month_values else None
    return latest, week_avg, month_avg
