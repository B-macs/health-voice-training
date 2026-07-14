"""Supabase-backed persistence for immutable Voxplot analysis records.

The Streamlit process is the only component that sees the secret API key.
Browser code never receives it; the key is sent only to Supabase's Data API
from this server-side module.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_TABLE = "voice_sessions"
_PAGE_SIZE = 1000
_RECORD_FIELDS = ("timestamp", "sample_meta", "parameters", "indices", "norms")


class SupabaseStorageError(RuntimeError):
    """Raised when a configured Supabase store cannot complete an operation."""


@dataclass(frozen=True)
class SupabaseConfig:
    """Validated server-only connection settings for the Voxplot store."""

    url: str
    secret_key: str

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "SupabaseConfig | None":
        """DETERMINISTIC: validate storage settings; fallback to ``None`` when unconfigured."""
        values = values or {}
        url = str(values.get("url", "")).strip().rstrip("/")
        secret_key = str(values.get("secret_key", "")).strip()

        if not url and not secret_key:
            return None
        if not url or not secret_key:
            raise SupabaseStorageError(
                "Both voxplot_supabase.url and voxplot_supabase.secret_key must be configured."
            )
        if not url.startswith("https://") or not url.endswith(".supabase.co"):
            raise SupabaseStorageError(
                "voxplot_supabase.url must be the HTTPS Project URL from Supabase."
            )
        if not secret_key.startswith("sb_secret_"):
            raise SupabaseStorageError(
                "Use a Supabase Secret key (sb_secret_...) for voxplot_supabase.secret_key."
            )
        return cls(url=url, secret_key=secret_key)


def _json_safe(value: Any) -> Any:
    """DETERMINISTIC: make records JSONB-safe; fallback converts non-finite floats to ``None``."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _normalised_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """DETERMINISTIC: validate one immutable record; fallback raises a clear storage error."""
    missing = [field for field in _RECORD_FIELDS if field not in record]
    if missing:
        raise SupabaseStorageError(
            "Voice record is missing required field(s): " + ", ".join(missing)
        )
    return {field: _json_safe(record[field]) for field in _RECORD_FIELDS}


def record_hash(record: Mapping[str, Any]) -> str:
    """DETERMINISTIC: produce an idempotency key; fallback raises for invalid record content."""
    canonical = json.dumps(
        _normalised_record(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SupabaseRecordStore:
    """Append-only RecordStore implementation using Supabase's server-side Data API."""

    def __init__(self, config: SupabaseConfig, timeout_seconds: float = 15.0):
        self.config = config
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, payload: Any | None = None, *, prefer: str | None = None) -> bytes:
        """DETERMINISTIC: execute one API request; fallback raises a non-secret error message."""
        headers = {
            "apikey": self.config.secret_key,
            "Accept": "application/json",
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if prefer:
            headers["Prefer"] = prefer

        request = Request(
            f"{self.config.url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            raise SupabaseStorageError(
                f"Supabase {method} request failed ({exc.code}). Check the table migration and server secret."
            ) from exc
        except URLError as exc:
            raise SupabaseStorageError(
                f"Supabase {method} request could not reach the database."
            ) from exc

    def append(self, record: dict) -> None:
        """DETERMINISTIC: insert one record once; fallback raises without silently using local disk."""
        normalised = _normalised_record(record)
        row = {
            "record_hash": record_hash(normalised),
            "recorded_at": normalised["timestamp"],
            "sample_meta": normalised["sample_meta"],
            "parameters": normalised["parameters"],
            "indices": normalised["indices"],
            "norms": normalised["norms"],
        }
        query = urlencode({"on_conflict": "record_hash"})
        self._request(
            "POST",
            f"/rest/v1/{_TABLE}?{query}",
            row,
            prefer="resolution=ignore-duplicates,return=minimal",
        )

    def read_all(self) -> list[dict]:
        """DETERMINISTIC: read every stored record; fallback raises rather than returning partial history."""
        records: list[dict] = []
        offset = 0
        while True:
            query = urlencode({
                "select": "id,recorded_at,sample_meta,parameters,indices,norms",
                "order": "recorded_at.asc,id.asc",
                "limit": str(_PAGE_SIZE),
                "offset": str(offset),
            })
            payload = self._request("GET", f"/rest/v1/{_TABLE}?{query}")
            try:
                rows = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise SupabaseStorageError("Supabase returned invalid JSON for voice history.") from exc
            if not isinstance(rows, list):
                raise SupabaseStorageError("Supabase returned an unexpected voice-history response.")

            for row in rows:
                try:
                    records.append({
                        "timestamp": row["recorded_at"],
                        "sample_meta": row["sample_meta"],
                        "parameters": row["parameters"],
                        "indices": row["indices"],
                        "norms": row["norms"],
                    })
                except (KeyError, TypeError) as exc:
                    raise SupabaseStorageError(
                        "Supabase returned a voice-history row with missing data."
                    ) from exc

            if len(rows) < _PAGE_SIZE:
                return records
            offset += len(rows)
