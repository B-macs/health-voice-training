"""Unit tests for the server-only Supabase voice-history store."""
from __future__ import annotations

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from storage.supabase import (
    SupabaseConfig,
    SupabaseRecordStore,
    SupabaseStorageError,
    record_hash,
)


class _Response:
    def __init__(self, body: bytes = b""):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.body


def _record() -> dict:
    return {
        "timestamp": "2026-07-14T08:46:15+00:00",
        "sample_meta": {"sv_seconds": 3.0},
        "parameters": {"jitter_local_pct": 0.3},
        "indices": {"avqi": 2.1, "abi": 1.8},
        "norms": {"avqi": {"in_range": True}},
    }


def _config() -> SupabaseConfig:
    config = SupabaseConfig.from_mapping({
        "url": "https://example.supabase.co",
        "secret_key": "sb_secret_for_tests_only",
    })
    assert config is not None
    return config


def test_unconfigured_mapping_uses_local_store_fallback():
    assert SupabaseConfig.from_mapping({}) is None


def test_config_requires_both_values_and_a_secret_key():
    with pytest.raises(SupabaseStorageError, match="Both"):
        SupabaseConfig.from_mapping({"url": "https://example.supabase.co"})
    with pytest.raises(SupabaseStorageError, match="Secret key"):
        SupabaseConfig.from_mapping({
            "url": "https://example.supabase.co",
            "secret_key": "sb_publishable_not_for_servers",
        })
    with pytest.raises(SupabaseStorageError, match="Secret key"):
        SupabaseConfig.from_mapping({
            "url": "https://example.supabase.co",
            "secret_key": "legacy-anon-key",
        })


def test_record_hash_is_stable_and_ignores_mapping_key_order():
    record = _record()
    reordered = {
        "norms": record["norms"],
        "indices": record["indices"],
        "parameters": record["parameters"],
        "sample_meta": record["sample_meta"],
        "timestamp": record["timestamp"],
    }
    assert record_hash(record) == record_hash(reordered)


def test_append_posts_an_idempotent_record_without_returning_secrets():
    store = SupabaseRecordStore(_config())
    with patch("storage.supabase.urlopen", return_value=_Response()) as urlopen_mock:
        store.append(_record())

    request = urlopen_mock.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url.endswith("/rest/v1/voice_sessions?on_conflict=record_hash")
    assert request.get_header("Apikey") == "sb_secret_for_tests_only"
    assert request.get_header("Prefer") == "resolution=ignore-duplicates,return=minimal"
    assert payload["recorded_at"] == _record()["timestamp"]
    assert payload["record_hash"] == record_hash(_record())


def test_read_all_reconstructs_existing_record_shape():
    row = {
        "id": "a6e5d493-3d37-4583-940b-c2e3152bb8be",
        "recorded_at": _record()["timestamp"],
        "sample_meta": _record()["sample_meta"],
        "parameters": _record()["parameters"],
        "indices": _record()["indices"],
        "norms": _record()["norms"],
    }
    store = SupabaseRecordStore(_config())
    with patch("storage.supabase.urlopen", return_value=_Response(json.dumps([row]).encode("utf-8"))) as urlopen_mock:
        assert store.read_all() == [_record()]

    request = urlopen_mock.call_args.args[0]
    query = parse_qs(urlparse(request.full_url).query)
    assert query["order"] == ["recorded_at.asc,id.asc"]
