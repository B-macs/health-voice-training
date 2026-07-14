"""Timezone-safe record ordering and local calendar-day helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from storage.record_metadata import analysis_metadata


DEFAULT_TIMEZONE = "Europe/Berlin"


# DETERMINISTIC: parse an ISO timestamp into an aware UTC datetime; fallback makes naive timestamps UTC.
def parse_timestamp(timestamp: str) -> datetime:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


# DETERMINISTIC: resolve the configured record timezone; fallback uses Europe/Berlin for legacy sessions.
def record_timezone(record: dict) -> ZoneInfo:
    name = str(analysis_metadata(record).get("recording_timezone", DEFAULT_TIMEZONE))
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


# DETERMINISTIC: derive the user's local calendar date; fallback uses Europe/Berlin for legacy data.
def local_date(record: dict):
    return parse_timestamp(record["timestamp"]).astimezone(record_timezone(record)).date()


# DETERMINISTIC: make a stable chronological key; fallback keeps malformed timestamps after valid records.
def record_sort_key(record: dict) -> tuple[int, datetime | str]:
    try:
        return 0, parse_timestamp(str(record["timestamp"]))
    except (KeyError, TypeError, ValueError):
        return 1, str(record.get("timestamp", ""))


# DETERMINISTIC: return chronological records without changing their stored representation.
def sort_records(records: list[dict]) -> list[dict]:
    return sorted(records, key=record_sort_key)
