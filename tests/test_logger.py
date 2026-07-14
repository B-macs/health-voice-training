"""G6: every recording appends a schema-valid JSONL row with norms/flags."""
import json

import pytest

from analysis.norms import flag_all
from storage.logger import JsonlRecordStore, REQUIRED_PARAMETER_KEYS, build_record, log_session
from storage.record_metadata import analysis_metadata


def _dummy_parameters():
    return {k: 1.0 for k in REQUIRED_PARAMETER_KEYS}


def test_build_record_rejects_missing_parameters():
    with pytest.raises(ValueError):
        build_record({}, {"f0_mean_hz": 1.0}, {}, {})


def test_build_record_schema():
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})
    record = build_record({"sv_seconds": 3.0, "cs_seconds": 6.0, "sample_rate_hz": 44100}, params, indices, norms)

    assert "timestamp" in record
    assert record["sample_meta"]["sample_rate_hz"] == 44100
    assert record["parameters"] == params
    assert record["indices"] == indices
    assert record["norms"]["jitter_local_pct"]["in_range"] is not None


def test_log_session_appends_valid_jsonl_line(tmp_path):
    path = tmp_path / "voice_log.jsonl"
    store = JsonlRecordStore(str(path))
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})

    log_session(store, {"sv_seconds": 3.0, "cs_seconds": 6.0, "sample_rate_hz": 44100}, params, indices, norms)
    log_session(store, {"sv_seconds": 3.1, "cs_seconds": 6.2, "sample_rate_hz": 44100}, params, indices, norms)

    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert set(parsed.keys()) == {"timestamp", "sample_meta", "parameters", "indices", "norms"}


def test_jsonl_read_orders_out_of_order_history(tmp_path):
    path = tmp_path / "voice_log.jsonl"
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})
    older = build_record({}, params, indices, norms)
    newer = build_record({}, params, indices, norms)
    older["timestamp"] = "2025-01-01T10:00:00+00:00"
    newer["timestamp"] = "2025-01-02T10:00:00+00:00"
    path.write_text("\n".join(json.dumps(row) for row in (newer, older)) + "\n", encoding="utf-8")

    assert [row["timestamp"] for row in JsonlRecordStore(str(path)).read_all()] == [
        older["timestamp"],
        newer["timestamp"],
    ]


def test_record_preserves_non_audio_analysis_provenance():
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})
    provenance = {
        "schema_version": 2,
        "protocol_version": "de_windowed_3s_v2",
        "scoring_version": "voice_quality_v1",
        "protocol": {"status": "usable", "analysis_allowed": True},
        "capture": {"raw_audio_stored": False},
    }
    record = build_record({"analysis_meta": provenance}, params, indices, norms)

    assert analysis_metadata(record)["protocol_version"] == "de_windowed_3s_v2"
    assert record["sample_meta"]["analysis_meta"]["capture"]["raw_audio_stored"] is False


def test_legacy_record_has_explicit_metadata_fallback():
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    legacy = build_record({}, params, indices, flag_all({**params, **indices}))

    metadata = analysis_metadata(legacy)
    assert metadata["protocol_version"] == "legacy_manual_unversioned"
    assert metadata["protocol"]["status"] == "legacy_unknown"
