"""Structured result logging.

Phase 1: append-only local JSON Lines file (no cloud auth needed). The
`RecordStore` interface is intentionally minimal (`append(record)`) so a
SQLite/Postgres backend can be swapped in later (Phase 2) without touching
analysis code -- construct a different store and pass it to `log_session`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Protocol

from storage.daily_averages import DailyAverageStore


class RecordStore(Protocol):
    def append(self, record: dict) -> None: ...


class JsonlRecordStore:
    def __init__(self, path: str = "voice_log.jsonl"):
        self.path = path

    def append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False)
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records


REQUIRED_PARAMETER_KEYS = (
    "f0_mean_hz", "f0_sd_hz", "f0_sd_st",
    "jitter_local_pct", "jitter_ppq5_pct",
    "shimmer_local_pct", "shimmer_local_db", "shimmer_apq11_pct",
    "hnr_db", "cpps_sv_db", "cpps_cs_db",
    "ltas_slope_db", "ltas_tilt_db", "gne", "h1_h2_db",
)


def build_record(
    sample_meta: dict,
    parameters: dict,
    indices: dict,
    norms: dict,
) -> dict:
    missing = [k for k in REQUIRED_PARAMETER_KEYS if k not in parameters]
    if missing:
        raise ValueError(f"parameters dict missing required keys: {missing}")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_meta": sample_meta,
        "parameters": parameters,
        "indices": indices,
        "norms": norms,
    }


def log_session(
    store: RecordStore,
    sample_meta: dict, parameters: dict, indices: dict, norms: dict,
    daily_store: DailyAverageStore | None = None,
) -> dict:
    record = build_record(sample_meta, parameters, indices, norms)
    store.append(record)
    if daily_store is not None:
        all_records = store.read_all()
        daily_store.upsert_from_raw(all_records, record["timestamp"][:10])
    return record
