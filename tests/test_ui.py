"""Unit tests for ui/scoring.py and ui/aggregation.py -- the dashboard's
direction-aware normalization and day/week/month rollup logic. Not a UI
rendering test (that needs a browser -- see PLAN.md/README for how this was
verified manually with Playwright); this covers the pure-Python logic
underneath the dashboard.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from analysis.norms import NormRange
from ui.scoring import goodness, abnormality, composite_stimm_score, status_word_key
from ui.aggregation import period_key, aggregate, metric_value, period_to_ordinal


def test_goodness_lower_is_better_at_cutoff_is_50():
    norm = NormRange(max=2.70)
    assert abs(goodness(2.70, norm) - 50.0) < 1e-9


def test_goodness_lower_is_better_below_cutoff_is_better_than_50():
    norm = NormRange(max=2.70)
    assert goodness(1.0, norm) > 50.0
    assert goodness(5.0, norm) < 50.0


def test_goodness_higher_is_better_at_cutoff_is_50():
    norm = NormRange(min=20.0)
    assert abs(goodness(20.0, norm) - 50.0) < 1e-9
    assert goodness(30.0, norm) > 50.0
    assert goodness(10.0, norm) < 50.0


def test_goodness_none_for_missing_value_or_no_cutoff():
    assert goodness(None, NormRange(max=1.0)) is None
    assert goodness(float("nan"), NormRange(max=1.0)) is None
    assert goodness(5.0, NormRange()) is None


def test_abnormality_is_inverse_of_goodness():
    norm = NormRange(max=2.70)
    assert abs(abnormality(2.24, norm) - (100 - goodness(2.24, norm))) < 1e-9


def test_composite_score_reflects_avqi_and_abi_direction():
    norms = {"avqi": NormRange(max=2.70), "abi": NormRange(max=2.0)}
    healthy = composite_stimm_score({"avqi": 0.5, "abi": 0.2}, norms)
    unhealthy = composite_stimm_score({"avqi": 6.0, "abi": 8.0}, norms)
    assert healthy > unhealthy
    assert healthy > 50
    assert unhealthy < 50


def test_status_word_key_thresholds():
    assert status_word_key(90) == "status_optimal"
    assert status_word_key(60) == "status_attention"
    assert status_word_key(20) == "status_concerning"
    assert status_word_key(None) == "status_attention"


def test_period_key_day_week_month():
    dt = datetime(2026, 7, 8, 15, 30)
    assert period_key(dt, "day") == "2026-07-08"
    assert period_key(dt, "month") == "2026-07"
    iso_year, iso_week, _ = dt.isocalendar()
    assert period_key(dt, "week") == f"{iso_year}-W{iso_week:02d}"


def _fake_record(days_ago: int, avqi: float, abi: float) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "timestamp": ts.isoformat(),
        "parameters": {},
        "indices": {"avqi": avqi, "abi": abi},
        "norms": {
            "avqi": {"norm": {"min": None, "max": 2.70, "note": ""}, "in_range": True},
            "abi": {"norm": {"min": None, "max": 2.0, "note": ""}, "in_range": True},
        },
    }


def test_metric_value_reads_indices_and_composite():
    record = _fake_record(0, avqi=1.0, abi=0.5)
    assert metric_value(record, "avqi") == 1.0
    composite = metric_value(record, "composite")
    assert composite is not None and composite > 50  # healthy values -> good composite


def test_aggregate_buckets_by_day_with_average_min_max():
    records = [_fake_record(2, 1.0, 0.5), _fake_record(2, 3.0, 0.5), _fake_record(0, 2.0, 0.5)]
    buckets = aggregate(records, "avqi", "day")
    assert len(buckets) == 2
    two_days_ago_bucket = buckets[0]
    assert two_days_ago_bucket.n == 2
    assert two_days_ago_bucket.average == 2.0
    assert two_days_ago_bucket.min == 1.0
    assert two_days_ago_bucket.max == 3.0


def test_aggregate_averages_not_medians_multiple_same_day_inputs():
    """A skewed set of same-day inputs must average, not take the middle
    value -- median would let a single outlier session dominate the day's
    displayed trend point instead of reflecting all of them."""
    records = [_fake_record(0, 1.0, 0.5), _fake_record(0, 1.0, 0.5), _fake_record(0, 10.0, 0.5)]
    buckets = aggregate(records, "avqi", "day")
    assert len(buckets) == 1
    assert abs(buckets[0].average - 4.0) < 1e-9  # mean(1,1,10), NOT median(1,1,10)=1


def test_period_to_ordinal_orders_and_spaces_by_real_elapsed_time():
    day_gap_close = period_to_ordinal("2025-10-27", "day") - period_to_ordinal("2025-10-14", "day")
    day_gap_far = period_to_ordinal("2025-11-06", "day") - period_to_ordinal("2025-09-25", "day")
    assert day_gap_close == 13
    assert day_gap_far == 42
    assert day_gap_far > day_gap_close


def test_period_to_ordinal_week_and_month_granularity():
    # ISO week 1 of 2025 starts Monday 2024-12-30
    assert period_to_ordinal("2025-W01", "week") == datetime(2024, 12, 30).toordinal()
    assert period_to_ordinal("2025-06", "month") == datetime(2025, 6, 1).toordinal()
    # a later month must be a strictly larger ordinal than an earlier one
    assert period_to_ordinal("2025-07", "month") > period_to_ordinal("2025-06", "month")
