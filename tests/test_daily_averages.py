"""Per-day averaging: a user can redo a recording within the same day (if
a reading felt off) without it distorting week/month trends, and the
canonical daily average is persisted and recalculated automatically each
time a new same-day recording is logged.
"""
from __future__ import annotations

from analysis.norms import flag_all
from storage.daily_averages import DailyAverageStore, daily_average_records
from storage.logger import JsonlRecordStore, REQUIRED_PARAMETER_KEYS, log_session
from ui.aggregation import aggregate, latest_and_prior_averages


def _record(timestamp: str, avqi: float, abi: float = 1.0) -> dict:
    params = {"jitter_local_pct": 0.3}
    indices = {"avqi": avqi, "abi": abi}
    return {
        "timestamp": timestamp,
        "sample_meta": {},
        "parameters": params,
        "indices": indices,
        "norms": flag_all({**params, **indices}),
    }


def test_single_recording_day_is_that_reading():
    records = [_record("2025-01-06T09:00:00+00:00", avqi=2.5)]
    daily = daily_average_records(records)
    assert len(daily) == 1
    assert daily[0]["indices"]["avqi"] == 2.5
    assert daily[0]["n"] == 1


def test_multiple_same_day_recordings_average():
    records = [
        _record("2025-01-06T09:00:00+00:00", avqi=1.0),
        _record("2025-01-06T14:00:00+00:00", avqi=3.0),
        _record("2025-01-06T20:00:00+00:00", avqi=5.0),
    ]
    daily = daily_average_records(records)
    assert len(daily) == 1
    assert daily[0]["indices"]["avqi"] == 3.0  # mean(1,3,5)
    assert daily[0]["n"] == 3


def test_week_view_does_not_let_a_redone_day_outweigh_a_single_reading_day():
    """The bug this feature fixes: pooling raw recordings directly into a
    week bucket lets a day with several redo attempts dominate the week's
    average. Monday (one reading, avqi=1.0) and Wednesday (three redo
    readings, all avqi=10.0) are in the same ISO week -- the week average
    must weight each DAY equally (mean(1.0, 10.0) = 5.5), not each raw
    recording (mean(1,10,10,10) = 7.75)."""
    records = [
        _record("2025-01-06T09:00:00+00:00", avqi=1.0),   # Monday
        _record("2025-01-08T09:00:00+00:00", avqi=10.0),  # Wednesday, redo 1
        _record("2025-01-08T14:00:00+00:00", avqi=10.0),  # Wednesday, redo 2
        _record("2025-01-08T20:00:00+00:00", avqi=10.0),  # Wednesday, redo 3
    ]
    buckets = aggregate(records, "avqi", "week")
    assert len(buckets) == 1
    assert abs(buckets[0].average - 5.5) < 1e-9
    assert buckets[0].n == 2  # 2 distinct days, not 4 raw recordings


def test_month_view_also_weights_by_day_not_raw_recording():
    records = [
        _record("2025-01-06T09:00:00+00:00", avqi=1.0),
        _record("2025-01-20T09:00:00+00:00", avqi=10.0),
        _record("2025-01-20T14:00:00+00:00", avqi=10.0),
    ]
    buckets = aggregate(records, "avqi", "month")
    assert len(buckets) == 1
    assert abs(buckets[0].average - 5.5) < 1e-9
    assert buckets[0].n == 2


def test_day_view_still_reports_raw_min_max_and_count():
    """Day granularity is unchanged: it buckets raw recordings directly,
    so a chart showing a single day's spread still sees the true
    min/max/n of that day's recordings, not a collapsed single value."""
    records = [
        _record("2025-01-06T09:00:00+00:00", avqi=1.0),
        _record("2025-01-06T14:00:00+00:00", avqi=3.0),
    ]
    buckets = aggregate(records, "avqi", "day")
    assert len(buckets) == 1
    assert buckets[0].average == 2.0
    assert buckets[0].min == 1.0
    assert buckets[0].max == 3.0
    assert buckets[0].n == 2


def test_latest_and_prior_averages_uses_latest_raw_but_day_averaged_priors():
    """Voice Analysis always shows the latest single raw reading -- even if
    today already has other recordings. Prev week/month must not let a
    heavily-redone day outweigh others."""
    records = [
        _record("2025-01-06T09:00:00+00:00", avqi=1.0),
        _record("2025-01-08T09:00:00+00:00", avqi=10.0),
        _record("2025-01-08T14:00:00+00:00", avqi=10.0),
        _record("2025-01-09T09:00:00+00:00", avqi=4.0),  # today, the "latest"
    ]
    latest, week_avg, month_avg = latest_and_prior_averages(records, "avqi")
    assert latest == 4.0  # the single most recent raw reading, unaveraged
    assert abs(week_avg - 5.5) < 1e-9  # mean(1.0, 10.0) across the 2 PRIOR days, excluding today


def test_log_session_persists_and_recalculates_daily_average(tmp_path):
    raw_path = tmp_path / "voice_log.jsonl"
    daily_path = tmp_path / "daily_averages.jsonl"
    store = JsonlRecordStore(str(raw_path))
    daily_store = DailyAverageStore(str(daily_path))

    params = {k: 1.0 for k in REQUIRED_PARAMETER_KEYS}

    def log(avqi):
        indices = {"avqi": avqi, "abi": 1.0}
        norms = flag_all({**params, **indices})
        return log_session(store, {}, params, indices, norms, daily_store=daily_store)

    r1 = log(2.0)
    persisted = daily_store.load_all()
    today = r1["timestamp"][:10]
    assert persisted[today]["indices"]["avqi"] == 2.0
    assert persisted[today]["n"] == 1

    # a second reading the same day (the user redoing it) recalculates
    # the day's average automatically
    log(6.0)
    persisted = daily_store.load_all()
    assert persisted[today]["indices"]["avqi"] == 4.0  # mean(2.0, 6.0)
    assert persisted[today]["n"] == 2


def test_daily_average_store_upsert_replaces_not_duplicates(tmp_path):
    path = tmp_path / "daily_averages.jsonl"
    store = DailyAverageStore(str(path))
    day1 = [_record("2025-01-06T09:00:00+00:00", avqi=1.0)]
    store.upsert_from_raw(day1, "2025-01-06")
    day1_again = day1 + [_record("2025-01-06T14:00:00+00:00", avqi=3.0)]
    store.upsert_from_raw(day1_again, "2025-01-06")

    all_days = store.load_all()
    assert len(all_days) == 1
    assert all_days["2025-01-06"]["indices"]["avqi"] == 2.0
    assert all_days["2025-01-06"]["n"] == 2
